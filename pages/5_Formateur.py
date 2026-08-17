"""
pages/5_Formateur.py
Réservé au rôle "formateur" : consultation détaillée des tentatives des
apprenants (question par question, réponse donnée vs réponse attendue) et
une vue d'analyse agrégée par thème sur l'ensemble de la cohorte.

Note d'architecture : comme les autres pages, ce fichier apparaît dans le
menu latéral pour tout le monde (limite du système de navigation automatique
par fichiers de Streamlit -- voir navigation.py). La restriction d'accès se
fait donc à l'intérieur de la page, pas au niveau du menu.
"""

import json
import streamlit as st

import auth
import config
import theme
import navigation
from database import get_connection

theme.selecteur_theme()
theme.appliquer_theme()
navigation.marquer_arrivee_page("formateur")
navigation.bouton_retour_domaines()

utilisateur = auth.utilisateur_connecte()
if utilisateur is None:
    st.warning("Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

if utilisateur["role"] != "formateur":
    st.error("Cette page est réservée aux comptes formateur.")
    st.stop()

st.header("Espace formateur")

NOMS_COMPETENCES = {c["id"]: c["nom"] for c in config.COMPETENCES_MVP}

onglet_apprenant, onglet_analyse = st.tabs(["Revue par apprenant", "Analyse par thème"])

# ============================================================
# Onglet 1 : revue détaillée d'un apprenant
# ============================================================
with onglet_apprenant:
    with get_connection() as conn:
        apprenants = conn.execute(
            "SELECT * FROM apprenants WHERE role = 'apprenant' ORDER BY nom"
        ).fetchall()

    if not apprenants:
        st.caption("Aucun apprenant enregistré pour l'instant.")
    else:
        options_apprenants = {f"{a['nom']} ({a['email']})": a["id"] for a in apprenants}
        choix_nom = st.selectbox("Apprenant", options=list(options_apprenants.keys()))
        apprenant_id = options_apprenants[choix_nom]

        with get_connection() as conn:
            tentatives = conn.execute(
                """SELECT * FROM tentatives_evaluation WHERE apprenant_id = ?
                   ORDER BY date_tentative DESC""",
                (apprenant_id,),
            ).fetchall()

        if not tentatives:
            st.caption("Cet apprenant n'a encore passé aucune évaluation.")
        else:
            options_tentatives = {
                f"{NOMS_COMPETENCES.get(t['competence_id'], t['competence_id'])} — "
                f"tentative {t['numero_tentative']} — {t['note']}/20 — "
                f"{'validée' if t['valide'] else 'non validée'} — {t['date_tentative'][:16]}": t["id"]
                for t in tentatives
            }
            choix_tentative = st.selectbox("Tentative", options=list(options_tentatives.keys()))
            tentative_id = options_tentatives[choix_tentative]
            tentative = next(t for t in tentatives if t["id"] == tentative_id)

            col1, col2, col3 = st.columns(3)
            col1.metric("Note", f"{tentative['note']}/20")
            col2.metric("Statut", "Validée" if tentative["valide"] else "Non validée")
            col3.metric("Tentative n°", tentative["numero_tentative"])

            with get_connection() as conn:
                details = conn.execute(
                    "SELECT * FROM reponses_detail WHERE tentative_id = ? ORDER BY ordre",
                    (tentative_id,),
                ).fetchall()

            if not details:
                st.info(
                    "Le détail question par question n'a pas été enregistré pour cette "
                    "tentative (antérieure à la mise en place du suivi détaillé)."
                )
            else:
                st.divider()
                filtre = st.radio(
                    "Afficher", ["Toutes les questions", "Uniquement les erreurs"],
                    horizontal=True,
                )

                for d in details:
                    if filtre == "Uniquement les erreurs" and d["est_correcte"]:
                        continue
                    choix = json.loads(d["choix_json"])
                    reponse_donnee = d["reponse_donnee"]
                    reponse_correcte = d["reponse_correcte"]

                    icone = "✅" if d["est_correcte"] else "❌"
                    with st.container(border=True):
                        st.markdown(f"{icone} **Q{d['ordre'] + 1}.** {d['question']}")
                        st.caption(f"Sous-thème : {d['sous_theme']}    |    Niveau : {d['niveau']}")
                        for i, texte_choix in enumerate(choix):
                            prefixe = ""
                            if i == reponse_correcte:
                                prefixe = "✔️ "
                            elif i == reponse_donnee:
                                prefixe = "➡️ "
                            style = ""
                            if i == reponse_correcte:
                                style = "**"
                            texte_ligne = f"{prefixe}{style}{texte_choix}{style}"
                            st.write(texte_ligne)
                        if reponse_donnee is None:
                            st.caption("Aucune réponse donnée (temps écoulé ou question passée).")
                        elif not d["est_correcte"]:
                            st.caption(
                                f"Réponse donnée : « {choix[reponse_donnee]} »  —  "
                                f"Réponse attendue : « {choix[reponse_correcte]} »"
                            )

# ============================================================
# Onglet 2 : analyse agrégée par thème, toute la cohorte
# ============================================================
with onglet_analyse:
    st.caption("Taux de réussite par thème, toutes tentatives et tous apprenants confondus.")

    competence_id_analyse = st.selectbox(
        "Compétence", options=list(NOMS_COMPETENCES.keys()),
        format_func=lambda x: NOMS_COMPETENCES[x], key="comp_analyse",
    )

    with get_connection() as conn:
        lignes = conn.execute(
            """SELECT rd.sous_theme, rd.est_correcte
               FROM reponses_detail rd
               JOIN tentatives_evaluation t ON rd.tentative_id = t.id
               WHERE t.competence_id = ?""",
            (competence_id_analyse,),
        ).fetchall()

    if not lignes:
        st.caption("Pas encore de données pour cette compétence.")
    else:
        stats = {}
        for l in lignes:
            st_ = l["sous_theme"] or "Non classé"
            stats.setdefault(st_, {"total": 0, "correct": 0})
            stats[st_]["total"] += 1
            stats[st_]["correct"] += l["est_correcte"]

        for theme_nom, s in sorted(stats.items(), key=lambda x: x[1]["correct"] / x[1]["total"]):
            taux = s["correct"] / s["total"] * 100
            st.write(f"**{theme_nom}** — {s['correct']}/{s['total']} bonnes réponses ({taux:.0f}%)")
            st.progress(taux / 100)

        st.caption(
            "Les thèmes en haut de liste sont ceux où la cohorte réussit le moins bien — "
            "utile pour orienter le contenu des séances de reformation."
        )