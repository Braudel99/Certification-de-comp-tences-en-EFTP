"""
pages/2_Mes_Competences.py
Tableau de bord de progression de l'apprenant : statut par compétence.
"""

import streamlit as st
import auth
import theme
import navigation
from database import get_connection

theme.selecteur_theme()
theme.appliquer_theme()
navigation.marquer_arrivee_page("mes_competences")
navigation.bouton_retour_domaines()

utilisateur = auth.utilisateur_connecte()
if utilisateur is None:
    st.warning("Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

st.header("Mes compétences")

with get_connection() as conn:
    competences = conn.execute("SELECT * FROM competences").fetchall()
    tentatives = conn.execute(
        "SELECT * FROM tentatives_evaluation WHERE apprenant_id = ? ORDER BY numero_tentative",
        (utilisateur["id"],),
    ).fetchall()

tentatives_par_competence = {}
for t in tentatives:
    tentatives_par_competence.setdefault(t["competence_id"], []).append(t)

for comp in competences:
    st.subheader(comp["nom"])
    hist = tentatives_par_competence.get(comp["id"], [])
    if not hist:
        st.caption("Aucune tentative pour l'instant.")
        continue

    derniere = hist[-1]
    if any(t["valide"] for t in hist):
        note_validante = next(t["note"] for t in hist if t["valide"])
        st.success(f"Validée — note : {note_validante}/20 ({len(hist)} tentative(s))")
    else:
        st.warning(f"Non validée — {len(hist)} tentative(s), dernière note : {derniere['note']}/20")
    st.divider()