"""
pages/3_Mon_Certificat.py
Affiche les certificats obtenus. La mise en forme PDF est un TODO
(reportlab / weasyprint) -- ici on affiche le contenu canonique tel que haché.
"""

import json
import streamlit as st
import auth
import theme
import navigation
from database import get_connection

theme.selecteur_theme()
theme.appliquer_theme()
navigation.marquer_arrivee_page("mon_certificat")
navigation.bouton_retour_domaines()

utilisateur = auth.utilisateur_connecte()
if utilisateur is None:
    st.warning("Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

st.header("Mes certificats")

with get_connection() as conn:
    certificats = conn.execute(
        "SELECT * FROM certificats WHERE apprenant_id = ?", (utilisateur["id"],)
    ).fetchall()

if not certificats:
    st.caption("Aucun certificat émis pour l'instant.")

for cert in certificats:
    contenu = json.loads(cert["contenu_json"])
    with st.container(border=True):
        st.subheader(contenu["competence_nom"])
        st.write(f"Note : **{contenu['note']}/20**")
        st.write(f"Délivré le : {contenu['date_delivrance']}")
        st.code(cert["identifiant_public"], language=None)
        st.caption("Identifiant à transmettre pour vérification tierce (page publique).")
        st.caption(f"Empreinte SHA-256 : `{cert['hash_certificat']}`")
        # TODO : générer un QR code pointant vers la page de vérification avec cet identifiant
        # TODO : bouton d'export PDF une fois la mise en forme visuelle définie