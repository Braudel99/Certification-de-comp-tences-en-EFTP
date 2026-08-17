"""
database.py
Couche d'accès aux données. SQLite pour le prototype de mémoire ;
prévoir une migration vers PostgreSQL si usage multi-utilisateurs simultané en production.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
import config


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


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