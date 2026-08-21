"""
pages/4_Verification_Publique.py
Page accessible sans connexion : un tiers saisit l'identifiant (issu d'un QR code)
et obtient l'un des trois statuts : AUTHENTIQUE / FALSIFIE / INCONNU.
"""

import streamlit as st
import verification
import ipfs
import theme
import navigation

theme.selecteur_theme()
theme.appliquer_theme()
navigation.marquer_arrivee_page("verification")
navigation.bouton_retour_domaines()

st.header("Vérification publique d'un certificat")
st.caption("Saisissez l'identifiant présent sur le certificat ou scanné via le QR code.")

# Pré-remplissage automatique si on arrive ici via un scan de QR code
# (l'URL encodée dans le QR contient ?id=<identifiant>).
identifiant_depuis_url = st.query_params.get("id", "")

identifiant = st.text_input("Identifiant du certificat", value=identifiant_depuis_url)

verification_auto = bool(identifiant_depuis_url) and f"verif_auto_{identifiant_depuis_url}" not in st.session_state
if verification_auto:
    st.session_state[f"verif_auto_{identifiant_depuis_url}"] = True

if (st.button("Vérifier", type="primary") or verification_auto) and identifiant:
    resultat = verification.verifier_certificat(identifiant.strip())

    if resultat["statut"] == "AUTHENTIQUE":
        st.success(resultat["message"])
        cert = resultat["certificat"]
        st.write(f"**Titulaire :** {cert['apprenant_nom']}")
        st.write(f"**Compétence :** {cert['competence_nom']}")
        st.write(f"**Note :** {cert['note']}/20")
        st.write(f"**Date de délivrance :** {cert['date_delivrance']}")

        if resultat.get("blockchain_tx_hash") or resultat.get("ipfs_cid"):
            with st.expander("🔍 Vérification indépendante (sans passer par notre plateforme)"):
                st.caption(
                    "Ces liens permettent de confirmer l'authenticité de ce certificat "
                    "même si notre plateforme n'est plus accessible."
                )
                if resultat.get("blockchain_tx_hash"):
                    url_explorateur = f"https://amoy.polygonscan.com/tx/{resultat['blockchain_tx_hash']}"
                    st.write(f"**Transaction blockchain :** [{resultat['blockchain_tx_hash'][:20]}...]({url_explorateur})")
                if resultat.get("ipfs_cid"):
                    st.write(f"**Copie décentralisée (IPFS) :** [{resultat['ipfs_cid']}]({ipfs.url_ipfs(resultat['ipfs_cid'])})")

    elif resultat["statut"] == "FALSIFIE":
        st.error(resultat["message"])
        st.caption(
            "Le contenu ci-dessous est celui actuellement enregistré côté serveur ; "
            "il ne correspond plus à l'empreinte ancrée lors de l'émission d'origine."
        )

    else:  # INCONNU
        st.warning(resultat["message"])