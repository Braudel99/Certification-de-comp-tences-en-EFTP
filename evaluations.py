"""
evaluations.py
Logique métier des évaluations théoriques : tirage aléatoire des questions,
mélange des choix, calcul des délais entre tentatives, scoring, feedback agrégé
par sous-thème (sans jamais révéler les questions/réponses avant validation).
"""

import random
import json
from datetime import datetime, timedelta

import config
from database import get_connection, now_iso
from data.questions_bank import BANQUE


def tirer_questions(competence_id: str, nb_questions: int = None):
    """
    Tire aléatoirement les questions par palier de difficulté (tirage stratifié selon
    config.REPARTITION_NIVEAUX), tous sous-thèmes confondus au sein de chaque palier,
    puis mélange l'ordre des choix de chacune. Les questions sont ensuite ordonnées par
    difficulté croissante (Facile -> Moyen -> Application -> Difficile -> Pratique) pour
    que l'évaluation progresse en douceur plutôt que de mélanger tous les niveaux.
    """
    pool_par_niveau = {}
    for sous_theme, questions in BANQUE.get(competence_id, {}).items():
        for q in questions:
            pool_par_niveau.setdefault(q["niveau"], []).append({**q, "sous_theme": sous_theme})

    ordre_niveaux = ["Facile", "Moyen", "Application", "Difficile", "Pratique"]
    tirage = []
    for niveau in ordre_niveaux:
        dispo = pool_par_niveau.get(niveau, [])
        nb_voulu = config.REPARTITION_NIVEAUX.get(niveau, 0)
        nb_reel = min(nb_voulu, len(dispo))
        tirage.extend(random.sample(dispo, nb_reel))

    questions_melangees = []
    for q in tirage:
        indices = list(range(len(q["choix"])))
        random.shuffle(indices)
        choix_melanges = [q["choix"][i] for i in indices]
        nouvel_index_correct = indices.index(q["correct"])
        questions_melangees.append(
            {
                "question": q["question"],
                "choix": choix_melanges,
                "correct": nouvel_index_correct,
                "sous_theme": q["sous_theme"],
                "niveau": q["niveau"],
            }
        )
    return questions_melangees


def calculer_note(questions: list, reponses: list) -> float:
    """reponses : liste d'indices choisis par l'apprenant, même ordre que questions."""
    nb_correctes = sum(
        1 for q, r in zip(questions, reponses) if r == q["correct"]
    )
    return round(nb_correctes / len(questions) * config.NOTE_MAX, 2)


def feedback_par_sous_theme(questions: list, reponses: list) -> dict:
    """
    Agrège les erreurs par sous-thème SANS révéler la question ni la bonne réponse.
    Utilisé uniquement tant que la compétence n'est pas validée.
    """
    erreurs = {}
    total = {}
    for q, r in zip(questions, reponses):
        st_ = q["sous_theme"]
        total[st_] = total.get(st_, 0) + 1
        if r != q["correct"]:
            erreurs[st_] = erreurs.get(st_, 0) + 1

    feedback = {}
    for sous_theme, nb_total in total.items():
        nb_err = erreurs.get(sous_theme, 0)
        if nb_err > 0:
            feedback[sous_theme] = f"{nb_err}/{nb_total} erreur(s) — à retravailler"
    return feedback


def calculer_prochaine_date_tentative(numero_tentative_echouee: int) -> str:
    """
    numero_tentative_echouee : numéro de la tentative qui vient d'échouer (1, 2, 3, 4, 5, ...)
    Retourne la date ISO à partir de laquelle la tentative suivante est autorisée.
    """
    if numero_tentative_echouee in config.DELAIS_TENTATIVES:
        delai_heures = config.DELAIS_TENTATIVES[numero_tentative_echouee]
    else:
        # à partir de la 5e tentative échouée : palier fixe d'1 mois
        delai_heures = config.DELAI_PALIER_MOIS_HEURES
    date_prochaine = datetime.now() + timedelta(hours=delai_heures)
    return date_prochaine.isoformat(timespec="seconds")


def peut_retenter(apprenant_id: int, competence_id: str):
    """Retourne (autorise: bool, date_prochaine: str|None, deja_valide: bool)."""
    with get_connection() as conn:
        deja_valide = conn.execute(
            "SELECT 1 FROM tentatives_evaluation WHERE apprenant_id=? AND competence_id=? AND valide=1",
            (apprenant_id, competence_id),
        ).fetchone()
        if deja_valide:
            return False, None, True

        derniere = conn.execute(
            """SELECT * FROM tentatives_evaluation
               WHERE apprenant_id=? AND competence_id=?
               ORDER BY numero_tentative DESC LIMIT 1""",
            (apprenant_id, competence_id),
        ).fetchone()

    if derniere is None:
        return True, None, False

    if derniere["date_prochaine_tentative"] is None:
        return True, None, False

    date_prochaine = datetime.fromisoformat(derniere["date_prochaine_tentative"])
    if datetime.now() >= date_prochaine:
        return True, None, False
    return False, derniere["date_prochaine_tentative"], False


def enregistrer_tentative(apprenant_id: int, competence_id: str, note: float,
                           feedback: dict, questions: list = None, reponses: list = None,
                           nb_changements_focus: int = 0):
    valide = 1 if note >= config.SEUIL_VALIDATION else 0
    with get_connection() as conn:
        numero = conn.execute(
            "SELECT COUNT(*) as n FROM tentatives_evaluation WHERE apprenant_id=? AND competence_id=?",
            (apprenant_id, competence_id),
        ).fetchone()["n"] + 1

        date_prochaine = None if valide else calculer_prochaine_date_tentative(numero)

        curseur = conn.execute(
            """INSERT INTO tentatives_evaluation
               (apprenant_id, competence_id, numero_tentative, note, valide,
                date_tentative, date_prochaine_tentative, sous_themes_faibles, nb_changements_focus)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                apprenant_id, competence_id, numero, note, valide,
                now_iso(), date_prochaine, json.dumps(feedback, ensure_ascii=False),
                nb_changements_focus,
            ),
        )
        tentative_id = curseur.lastrowid

        # Détail question par question, nécessaire pour la revue formateur.
        if questions and reponses:
            for i, (q, r) in enumerate(zip(questions, reponses)):
                conn.execute(
                    """INSERT INTO reponses_detail
                       (tentative_id, ordre, question, choix_json, reponse_donnee,
                        reponse_correcte, sous_theme, niveau, est_correcte)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tentative_id, i, q["question"], json.dumps(q["choix"], ensure_ascii=False),
                        r if r is not None and r >= 0 else None, q["correct"],
                        q.get("sous_theme"), q.get("niveau"), 1 if r == q["correct"] else 0,
                    ),
                )
    return valide, numero, date_prochaine