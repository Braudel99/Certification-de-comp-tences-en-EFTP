"""
pages/4_Verification_Publique.py
Page accessible sans connexion : un tiers saisit l'identifiant (issu d'un QR code)
et obtient l'un des trois statuts : AUTHENTIQUE / FALSIFIE / INCONNU.
"""

import streamlit as st
import verification
import theme
import navigation

theme.selecteur_theme()
theme.appliquer_theme()
navigation.marquer_arrivee_page("verification")
navigation.bouton_retour_domaines()

st.header("Vérification publique d'un certificat")
st.caption("Saisissez l'identifiant présent sur le certificat ou scanné via le QR code.")

identifiant = st.text_input("Identifiant du certificat")

if st.button("Vérifier", type="primary") and identifiant:
    resultat = verification.verifier_certificat(identifiant.strip())

    if resultat["statut"] == "AUTHENTIQUE":
        st.success(resultat["message"])
        cert = resultat["certificat"]
        st.write(f"**Titulaire :** {cert['apprenant_nom']}")
        st.write(f"**Compétence :** {cert['competence_nom']}")
        st.write(f"**Note :** {cert['note']}/20")
        st.write(f"**Date de délivrance :** {cert['date_delivrance']}")

    elif resultat["statut"] == "FALSIFIE":
        st.error(resultat["message"])
        st.caption(
            "Le contenu ci-dessous est celui actuellement enregistré côté serveur ; "
            "il ne correspond plus à l'empreinte ancrée lors de l'émission d'origine."
        )

    else:  # INCONNU
        st.warning(resultat["message"])