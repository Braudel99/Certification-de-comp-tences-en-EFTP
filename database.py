"""
database.py
Couche d'accès aux données, migrée vers Turso (libSQL distant) pour la persistance
réelle -- le fichier SQLite local de Streamlit Cloud n'est PAS garanti de survivre
aux redémarrages/redéploiements du conteneur, ce qui a causé la disparition de
comptes signalée en test.

Turso étant compatible SQLite (même dialecte, mêmes types), tout le reste du code
(auth.py, evaluations.py, certification.py, blockchain.py, verification.py, les
pages) continue à utiliser exactement la même syntaxe qu'avant :
    with get_connection() as conn:
        conn.execute("SELECT ...", (param,)).fetchone() / .fetchall()
        curseur = conn.execute("INSERT ..."); curseur.lastrowid

La classe ConnexionCompat ci-dessous fait le pont avec l'API du client libsql_client
(qui diffère légèrement de sqlite3), afin qu'aucun autre fichier n'ait besoin
d'être modifié pour ce changement d'infrastructure.

Configuration requise (voir .streamlit/secrets.toml en local, ou l'onglet "Secrets"
du tableau de bord Streamlit Cloud pour la production) :
    TURSO_DATABASE_URL = "libsql://<votre-base>.turso.io"
    TURSO_AUTH_TOKEN   = "<jeton généré via `turso db tokens create`>"

Si ces secrets sont absents (typiquement en développement local sans configuration
Turso), la base retombe automatiquement sur un fichier local (config.DB_PATH) --
pratique pour tester rapidement, mais NON persistant sur Streamlit Cloud : à utiliser
uniquement pour du développement, jamais pour la version déployée aux apprenants.
"""

from contextlib import contextmanager
from datetime import datetime

import libsql_client
import streamlit as st
import config


def _url_et_jeton():
    """Lit les identifiants Turso depuis les secrets Streamlit, avec repli local."""
    try:
        url = st.secrets.get("TURSO_DATABASE_URL")
        jeton = st.secrets.get("TURSO_AUTH_TOKEN")
    except Exception:
        url, jeton = None, None

    if not url:
        # Repli développement local : fichier SQLite classique, NON persistant sur
        # Streamlit Cloud -- à ne jamais utiliser pour la version réellement déployée.
        return f"file:{config.DB_PATH}", None
    return url, jeton


class Row:
    """Émule sqlite3.Row : accès par nom de colonne (row['col']) ou par index."""

    def __init__(self, colonnes, valeurs):
        self._colonnes = colonnes
        self._valeurs = valeurs

    def __getitem__(self, cle):
        if isinstance(cle, str):
            return self._valeurs[self._colonnes.index(cle)]
        return self._valeurs[cle]

    def keys(self):
        return list(self._colonnes)

    def __repr__(self):
        return repr(dict(zip(self._colonnes, self._valeurs)))


class ResultatCompat:
    """Émule le curseur sqlite3 : .fetchone(), .fetchall(), .lastrowid."""

    def __init__(self, result_set, client, est_insert):
        self._result_set = result_set
        self._client = client
        self._est_insert = est_insert
        self._index = 0

    def fetchone(self):
        if self._index >= len(self._result_set.rows):
            return None
        ligne = Row(self._result_set.columns, self._result_set.rows[self._index])
        self._index += 1
        return ligne

    def fetchall(self):
        return [Row(self._result_set.columns, r) for r in self._result_set.rows]

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def lastrowid(self):
        if not self._est_insert:
            return None
        resultat = self._client.execute("SELECT last_insert_rowid()")
        return resultat.rows[0][0]


class ConnexionCompat:
    """Émule l'API sqlite3.Connection utilisée dans le reste du projet."""

    def __init__(self, client):
        self._client = client

    def execute(self, sql, params=None):
        rs = self._client.execute(sql, list(params) if params else [])
        est_insert = sql.strip().upper().startswith("INSERT")
        return ResultatCompat(rs, self._client, est_insert)

    def executescript(self, script):
        """libSQL exécute une instruction à la fois : on découpe sur ';'."""
        for instruction in script.split(";"):
            instruction = instruction.strip()
            if instruction:
                self._client.execute(instruction)

    def commit(self):
        pass  # chaque execute() est déjà validé côté serveur libSQL, no-op ici

    def close(self):
        pass  # fermeture gérée par get_connection()


@contextmanager
def get_connection():
    url, jeton = _url_et_jeton()
    client = libsql_client.create_client_sync(url, auth_token=jeton) if jeton \
        else libsql_client.create_client_sync(url)
    try:
        yield ConnexionCompat(client)
    finally:
        client.close()


def init_db():
    """Crée les tables si elles n'existent pas encore. À appeler au démarrage de l'app."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS apprenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mot_de_passe_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'apprenant',
                date_creation TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS competences (
                id TEXT PRIMARY KEY,
                nom TEXT NOT NULL,
                type_pratique TEXT
            );

            CREATE TABLE IF NOT EXISTS tentatives_evaluation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apprenant_id INTEGER NOT NULL,
                competence_id TEXT NOT NULL,
                numero_tentative INTEGER NOT NULL,
                note REAL,
                valide INTEGER NOT NULL DEFAULT 0,
                date_tentative TEXT NOT NULL,
                date_prochaine_tentative TEXT,
                sous_themes_faibles TEXT,
                nb_changements_focus INTEGER DEFAULT 0,
                FOREIGN KEY (apprenant_id) REFERENCES apprenants (id),
                FOREIGN KEY (competence_id) REFERENCES competences (id)
            );

            CREATE TABLE IF NOT EXISTS certificats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifiant_public TEXT UNIQUE NOT NULL,
                apprenant_id INTEGER NOT NULL,
                competence_id TEXT NOT NULL,
                note_finale REAL NOT NULL,
                date_delivrance TEXT NOT NULL,
                contenu_json TEXT NOT NULL,
                hash_certificat TEXT NOT NULL,
                hash_ancre_blockchain TEXT NOT NULL,
                FOREIGN KEY (apprenant_id) REFERENCES apprenants (id),
                FOREIGN KEY (competence_id) REFERENCES competences (id)
            );

            CREATE TABLE IF NOT EXISTS reponses_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tentative_id INTEGER NOT NULL,
                ordre INTEGER NOT NULL,
                question TEXT NOT NULL,
                choix_json TEXT NOT NULL,
                reponse_donnee INTEGER,
                reponse_correcte INTEGER NOT NULL,
                sous_theme TEXT,
                niveau TEXT,
                est_correcte INTEGER NOT NULL,
                FOREIGN KEY (tentative_id) REFERENCES tentatives_evaluation (id)
            );

            CREATE TABLE IF NOT EXISTS progression_evaluation (
                apprenant_id INTEGER NOT NULL,
                competence_id TEXT NOT NULL,
                ordre INTEGER NOT NULL,
                valeur_brute INTEGER,
                PRIMARY KEY (apprenant_id, competence_id, ordre)
            );

            CREATE TABLE IF NOT EXISTS blockchain_simulee (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_ancre TEXT UNIQUE NOT NULL,
                date_ancrage TEXT NOT NULL
            );
            """
        )
        for comp in config.COMPETENCES_MVP:
            conn.execute(
                "INSERT OR IGNORE INTO competences (id, nom, type_pratique) VALUES (?, ?, ?)",
                (comp["id"], comp["nom"], comp["type_pratique"]),
            )

        # Migration : ajout de la colonne matricule si absente (comptes créés avant cette évolution)
        colonnes = [row["name"] for row in conn.execute("PRAGMA table_info(apprenants)")]
        if "matricule" not in colonnes:
            conn.execute("ALTER TABLE apprenants ADD COLUMN matricule TEXT")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")