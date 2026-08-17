"""
navigation.py
Distingue une navigation "fraîche" (clic sur une page dans le menu latéral)
d'un simple rerun déclenché par une interaction sur la page déjà affichée
(bouton, formulaire...). Streamlit ne fournit pas nativement cette information
puisqu'il ré-exécute le script de la page dans les deux cas.

Principe : on mémorise le nom de la dernière page "marquée" en session. Si la
page qui s'exécute maintenant n'est pas celle mémorisée, c'est une navigation
fraîche -- sinon, c'est un rerun interne (ex. clic sur une card) et l'état
de progression en cours (compétence sélectionnée, etc.) doit être préservé.
"""

import streamlit as st


def marquer_arrivee_page(nom_page: str) -> bool:
    """Retourne True si c'est une navigation fraîche vers nom_page (à réinitialiser)."""
    page_precedente = st.session_state.get("page_active")
    st.session_state["page_active"] = nom_page
    return page_precedente != nom_page


def bouton_retour_domaines():
    """
    Bouton fiable de retour à la liste des domaines, affiché en haut de la barre
    latérale sur chaque page.

    Le lien automatique "Domaine" du menu Streamlit ne peut PAS être réinitialisé
    quand on clique dessus alors qu'on est déjà sur cette page (même en profondeur,
    ex. dans le détail d'une compétence) : Streamlit relance alors le script de la
    même façon qu'un simple rafraîchissement interne, sans moyen de distinguer les
    deux cas. Ce bouton contourne la limite : un clic sur un bouton est un événement
    qu'on contrôle explicitement, donc on peut vider l'état avant de rediriger.
    """
    if st.sidebar.button("🏠 Retour aux domaines", use_container_width=True):
        for cle in ["domaine_selectionne", "competence_selectionnee"]:
            st.session_state.pop(cle, None)
        for cle in list(st.session_state.keys()):
            if cle.startswith("confirme_") or cle.startswith("questions_") or cle.startswith("debut_"):
                del st.session_state[cle]
        st.switch_page("pages/1_Domaine.py")