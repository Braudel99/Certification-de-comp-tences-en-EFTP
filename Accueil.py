"""
Accueil.py
Point d'entrée, renommé depuis app.py pour que Streamlit affiche "Accueil"
dans le menu latéral (le libellé de la page principale est dérivé du nom de
fichier). Lancer avec : streamlit run Accueil.py

Gère le login et l'inscription (avec choix apprenant/formateur, matricule
requis et vérifié pour un compte formateur), puis laisse la navigation
multipage (dossier pages/) prendre le relais.
"""

import streamlit as st
from database import init_db
import auth
import theme

st.set_page_config(page_title="Certification de compétences en EFTP", page_icon="🎓", layout="wide")

init_db()
theme.selecteur_theme()
theme.appliquer_theme()

st.title("🎓 Certification de compétences en EFTP")

if auth.utilisateur_connecte() is None:
    onglet_connexion, onglet_inscription = st.tabs(["Se connecter", "Créer un compte"])

    with onglet_connexion:
        with st.form("connexion"):
            email = st.text_input("Email")
            mot_de_passe = st.text_input("Mot de passe", type="password")
            soumis = st.form_submit_button("Se connecter", type="primary")

        if soumis:
            utilisateur = auth.authentifier(email, mot_de_passe)
            if utilisateur:
                st.session_state["utilisateur"] = utilisateur
                st.switch_page("pages/1_Domaine.py")
            else:
                st.error("Identifiants incorrects.")

    with onglet_inscription:
        st.caption("Les comptes vérificateur sont créés séparément par l'administration.")

        # En dehors du formulaire : un changement de rôle doit s'afficher immédiatement
        # (dans un st.form, les widgets ne déclenchent pas de nouvelle exécution avant
        # la soumission, donc le champ matricule n'apparaissait qu'après un premier clic).
        role_i = st.radio(
            "Je suis", options=["apprenant", "formateur"],
            format_func=lambda r: "Apprenant" if r == "apprenant" else "Formateur",
            horizontal=True, key="role_inscription",
        )
        matricule_i = ""
        if role_i == "formateur":
            matricule_i = st.text_input(
                "Matricule formateur",
                help="Requis pour confirmer votre statut de formateur.",
                key="matricule_inscription",
            )

        with st.form("inscription"):
            nom = st.text_input("Nom complet")
            email_i = st.text_input("Email", key="email_inscription")
            mdp_i = st.text_input("Mot de passe", type="password", key="mdp_inscription")
            mdp_confirm = st.text_input("Confirmer le mot de passe", type="password")
            soumis_i = st.form_submit_button("Créer mon compte", type="primary")

        if soumis_i:
            erreurs = auth.valider_donnees_inscription(
                nom, email_i, mdp_i, mdp_confirm, role=role_i, matricule=matricule_i
            )
            if erreurs:
                for e in erreurs:
                    st.error(e)
            else:
                try:
                    utilisateur = auth.creer_compte(
                        nom, email_i, mdp_i, role=role_i, matricule=matricule_i
                    )
                    st.session_state["utilisateur"] = utilisateur
                    st.success("Compte créé avec succès.")
                    st.switch_page("pages/1_Domaine.py")
                except ValueError as e:
                    st.error(str(e))
else:
    utilisateur = auth.utilisateur_connecte()
    st.sidebar.success(f"Connecté : {utilisateur['nom']} ({utilisateur['role']})")
    if st.sidebar.button("Se déconnecter"):
        auth.deconnecter()
        st.rerun()

    st.write("Utilisez le menu à gauche pour accéder à une évaluation, "
             "consulter vos compétences ou votre certificat.")