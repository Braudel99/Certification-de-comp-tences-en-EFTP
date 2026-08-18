"""
utils.py
Protections anti-triche côté navigateur (JS/CSS injecté via components.html).

IMPORTANT (voir échanges précédents) : ces protections DÉCOURAGENT la copie et
journalisent les pertes de focus, mais ne peuvent techniquement PAS empêcher une
capture d'écran système ni un second appareil -- limite du web à assumer et à
documenter dans le mémoire, pas une faille de cette implémentation en particulier.
"""

import streamlit as st
import streamlit.components.v1 as components


def injecter_protections_anticopie():
    """Désactive clic droit, sélection de texte et Ctrl+C/Ctrl+U sur la page."""
    components.html(
        """
        <script>
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('copy', e => e.preventDefault());
        document.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && ['c','u','s','p'].includes(e.key.toLowerCase())) {
                e.preventDefault();
            }
        });
        document.body.style.userSelect = 'none';
        </script>
        """,
        height=0,
    )


def injecter_detecteur_focus(cle_session: str = "nb_changements_focus"):
    """
    Journalise (côté navigateur) chaque perte de focus de l'onglet.
    Le compteur JS n'est pas directement lisible par Streamlit sans aller-retour ;
    pour le squelette, on incrémente un compteur affiché à l'écran et on
    demandera à l'apprenant de valider un résumé honnête à la fin -- une
    version plus poussée utilisera st.query_params ou un composant custom
    bidirectionnel pour remonter la valeur automatiquement au serveur.
    """
    components.html(
        """
        <script>
        let compteur = 0;
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                compteur += 1;
                console.log('Perte de focus détectée, total:', compteur);
                window.parent.postMessage({type: 'focus_lost', count: compteur}, '*');
            }
        });
        </script>
        """,
        height=0,
    )


def afficher_avertissement_evaluation(duree_minutes: int) -> bool:
    """Écran d'avertissement avant le début de l'évaluation. Retourne True si l'apprenant confirme."""
    st.warning(
        f"""
        **Avant de commencer**

        - Cette évaluation dure **{duree_minutes} minutes**, chronométrées.
        - Le changement d'onglet ou de fenêtre est **journalisé**.
        - Le copier-coller et le clic droit sont désactivés sur cette page.
        - Une fois lancée, l'évaluation ne peut pas être mise en pause.
        - **Munissez-vous d'une calculatrice** pour les questions nécessitant un calcul.

        Assurez-vous d'être dans de bonnes conditions avant de continuer.
        """
    )
    return st.button("J'ai compris, commencer l'évaluation", type="primary")


def formater_delai(date_iso: str) -> str:
    """Affiche un délai lisible avant la prochaine tentative autorisée."""
    from datetime import datetime
    date_prochaine = datetime.fromisoformat(date_iso)
    delta = date_prochaine - datetime.now()
    heures = delta.total_seconds() / 3600
    if heures < 24:
        return f"dans environ {int(heures)} heure(s)"
    jours = heures / 24
    if jours < 30:
        return f"dans environ {int(jours)} jour(s)"
    return f"dans environ {int(jours / 30)} mois"