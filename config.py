"""
config.py
Paramètres centraux du dispositif de certification.
Modifier ici plutôt que dans le code métier.
"""

# --- Évaluation ---
SEUIL_VALIDATION = 16          # note minimale sur 20 pour valider une compétence
NOTE_MAX = 20
NB_QUESTIONS_PAR_TENTATIVE = 40  # questions réellement posées à chaque tentative
NB_QUESTIONS_MIN_BANQUE = 20     # taille minimale recommandée de la banque par compétence
TEMPS_PAR_QUESTION_MIN = 1.3     # minutes, utilisé pour calculer la durée totale du chrono

# Répartition par niveau de difficulté au sein des 40 questions tirées (tirage stratifié,
# pas un tirage uniforme, pour garder l'équilibre facile/moyen/application/difficile/pratique).
REPARTITION_NIVEAUX = {
    "Facile": 8,
    "Moyen": 8,
    "Application": 10,
    "Difficile": 8,
    "Pratique": 6,
}  # somme = 40 = NB_QUESTIONS_PAR_TENTATIVE

# Affichage de l'évaluation par lots successifs (pagination), plutôt que les 40
# questions d'un coup, pour ne pas décourager le candidat. Ordonné par difficulté
# croissante (Facile -> Moyen -> Application -> Difficile -> Pratique).
QUESTIONS_PAR_PAGE = 5

# --- Tentatives et délais d'attente (en heures) ---
DELAIS_TENTATIVES = {
    1: 3,        # après tentative 1 -> 3h avant tentative 2
    2: 24,       # après tentative 2 -> 24h avant tentative 3
    3: 24 * 7,   # après tentative 3 -> 1 semaine
    4: 24 * 7,   # après tentative 4 -> 1 semaine (2e fois)
}
DELAI_PALIER_MOIS_HEURES = 24 * 30  # à partir de la tentative 5, palier fixe d'1 mois

# --- Rôles ---
ROLES = ["apprenant", "formateur", "verificateur"]

# --- Base de données ---
DB_PATH = "certification.db"

# --- Domaines (extensible : d'autres domaines pourront être ajoutés plus tard) ---
DOMAINES = [
    {
        "id": "ET",
        "nom": "Électrotechnique",
        "image": "assets/images/electrotechnique.webp",
        "description": "Câblage normé et diagnostic des installations électriques.",
    },
    {
        "id": "EN",
        "nom": "Énergétique",
        "image": "assets/images/energetique.webp",
        "description": "Dimensionnement des systèmes énergétiques, dont le solaire autonome.",
    },
]

# --- Compétences du MVP, rattachées à un domaine ---
COMPETENCES_MVP = [
    {
        "id": "C1",
        "domaine_id": "EN",
        "nom": "Dimensionner un système photovoltaïque autonome",
        "type_pratique": "simulateur_pv",  # renvoie vers le moteur PV Sizing réutilisé
        "image": "assets/images/competence_pv.webp",
        "presentation": (
            "Cette compétence consiste à calculer et choisir les composants d'une installation "
            "solaire autonome — panneaux, batteries, régulateur, onduleur — à partir des besoins "
            "électriques réels d'un foyer ou d'un site. Elle est particulièrement recherchée au "
            "Bénin, où l'électrification décentralisée et les solutions de secours reposent de "
            "plus en plus sur le solaire autonome."
        ),
    },
    {
        "id": "C2",
        "domaine_id": "ET",
        "nom": "Installations électriques (domestique)",
        "type_pratique": "schema_svg",
        "image": "assets/images/competence_cablage.webp",
        "presentation": (
            "Cette compétence couvre les connaissances, calculs et démarches de diagnostic "
            "nécessaires pour réaliser, protéger et dépanner une installation électrique "
            "domestique — grandeurs électriques, protections normalisées, calculs de "
            "dimensionnement et résolution méthodique de pannes courantes. Elle correspond "
            "au socle attendu de tout professionnel intervenant sur des installations "
            "résidentielles au Bénin."
        ),
    },
    {
        "id": "C3",
        "domaine_id": "ET",
        "nom": "Installations industrielles",
        "type_pratique": "arbre_diagnostic",
        "image": "assets/images/competence_diagnostic.webp",  # provisoire : pas d'image dédiée fournie
        "presentation": (
            "Cette compétence porte sur les équipements et automatismes des installations "
            "industrielles — machines électriques (moteurs, transformateurs, alternateurs), "
            "automatismes et commande, actionneurs pneumatiques et hydrauliques — ainsi que "
            "sur le diagnostic méthodique des pannes rencontrées sur ce type d'installation. "
            "Elle vise les techniciens appelés à intervenir en environnement industriel ou "
            "sur des lignes de production automatisées."
        ),
    },
]

# --- Comptes formateur ---
# Format de matricule accepté : une suite de chiffres, entre 5 et 11 caractères.
MATRICULE_LONGUEUR_MIN = 5
MATRICULE_LONGUEUR_MAX = 11