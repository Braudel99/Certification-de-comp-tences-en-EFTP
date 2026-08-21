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
import certification
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
        col_texte, col_qr = st.columns([3, 1])
        with col_texte:
            st.subheader(contenu["competence_nom"])
            st.write(f"Note : **{contenu['note']}/20**")
            st.write(f"Délivré le : {contenu['date_delivrance']}")
            st.code(cert["identifiant_public"], language=None)
            st.caption("Identifiant à transmettre pour vérification tierce (page publique).")
            st.caption(f"Empreinte SHA-256 : `{cert['hash_certificat']}`")
            if cert["blockchain_tx_hash"]:
                st.caption(f"⛓️ Ancré sur blockchain (Polygon Amoy) : `{cert['blockchain_tx_hash'][:20]}...`")
            else:
                st.caption("⛓️ Ancrage blockchain : simulation locale (portefeuille non configuré)")
            if cert["ipfs_cid"]:
                st.caption(f"🌐 Copie décentralisée (IPFS) : `{cert['ipfs_cid']}`")
        with col_qr:
            qr_png = certification.generer_qr_verification(cert["identifiant_public"])
            st.image(qr_png, caption="Scanner pour vérifier", width=150)

        pdf_bytes = certification.generer_certificat_pdf(
            contenu, cert["hash_certificat"],
            ipfs_cid=cert["ipfs_cid"], blockchain_tx_hash=cert["blockchain_tx_hash"],
        )
        st.download_button(
            "📄 Télécharger le certificat (PDF)",
            data=pdf_bytes,
            file_name=f"certificat_{contenu['competence_id']}_{cert['identifiant_public'][:8]}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )