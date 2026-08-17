"""
pages/1_Domaine.py
Flux : cards de domaines -> cards de compétences du domaine -> détail (paragraphe
unique, pas de "Description :"/"Utilité :") -> avertissement -> évaluation.

Remplace l'ancienne page 1_Evaluation.py. Le nom "Domaine" plutôt qu'"Évaluation"
permet d'ajouter d'autres domaines que le Génie électrique plus tard sans
restructurer la navigation.

Note technique : les blocs HTML des cards sont construits SANS retour à la ligne
indenté à l'intérieur de la chaîne -- un bloc HTML indenté de 4 espaces ou plus
est interprété par le moteur Markdown comme un bloc de code et s'affiche en
texte brut au lieu d'être rendu. D'où les chaînes construites sur une seule ligne.
"""

import time
import streamlit as st

import auth
import config
import evaluations
import certification
import utils
import theme
import navigation
from image_utils import image_en_base64

theme.selecteur_theme()
theme.appliquer_theme()
navigation.bouton_retour_domaines()

utilisateur = auth.utilisateur_connecte()
if utilisateur is None:
    st.warning("Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

# Navigation fraîche depuis le menu (et non un simple clic interne à cette page)
# -> on repart toujours de la liste des domaines, comme demandé.
if navigation.marquer_arrivee_page("domaine"):
    st.session_state.pop("domaine_selectionne", None)
    st.session_state.pop("competence_selectionnee", None)
    for cle in list(st.session_state.keys()):
        if cle.startswith("confirme_") or cle.startswith("questions_") or cle.startswith("debut_"):
            del st.session_state[cle]


def carte_html(titre: str, visuel_html: str, cle_bouton: str, largeur_colonne) -> bool:
    """Affiche une card (image/icône + titre) suivie de son bouton. Retourne True si cliqué."""
    with largeur_colonne:
        html = (
            f'<div class="carte">{visuel_html}'
            f'<div class="carte-corps"><p class="carte-titre">{titre}</p></div>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return st.button("Voir", key=cle_bouton, use_container_width=True)


# --- Étape 0 : choix du domaine ---
if "domaine_selectionne" not in st.session_state:
    st.header("Domaines")
    st.caption("Choisissez un domaine pour accéder à ses compétences.")

    colonnes = st.columns(3)
    for i, dom in enumerate(config.DOMAINES):
        image_b64 = image_en_base64(dom["image"])
        visuel = f'<img class="carte-image" src="{image_b64}" alt="{dom["nom"]}"/>'
        clique = carte_html(dom["nom"], visuel, f"choix_domaine_{dom['id']}", colonnes[i % 3])
        if clique:
            st.session_state["domaine_selectionne"] = dom["id"]
            st.rerun()
    st.stop()

domaine_id = st.session_state["domaine_selectionne"]
domaine = next(d for d in config.DOMAINES if d["id"] == domaine_id)

# --- Étape 1 : choix de la compétence dans le domaine ---
if "competence_selectionnee" not in st.session_state:
    if st.button("← Choisir un autre domaine"):
        del st.session_state["domaine_selectionne"]
        st.rerun()

    st.header(domaine["nom"])
    st.caption("Choisissez une compétence à évaluer.")

    competences_domaine = [c for c in config.COMPETENCES_MVP if c["domaine_id"] == domaine_id]
    colonnes = st.columns(3)
    for i, comp in enumerate(competences_domaine):
        image_b64 = image_en_base64(comp["image"])
        visuel = f'<img class="carte-image" src="{image_b64}" alt="{comp["nom"]}"/>'
        clique = carte_html(comp["nom"], visuel, f"choix_comp_{comp['id']}", colonnes[i % 3])
        if clique:
            st.session_state["competence_selectionnee"] = comp["id"]
            st.rerun()
    st.stop()

# --- Étape 2 : détail de la compétence sélectionnée ---
competence_id = st.session_state["competence_selectionnee"]
competence = next(c for c in config.COMPETENCES_MVP if c["id"] == competence_id)

if st.button("← Choisir une autre compétence"):
    for cle in list(st.session_state.keys()):
        if cle.startswith("confirme_") or cle.startswith("questions_") or cle.startswith("debut_"):
            del st.session_state[cle]
    del st.session_state["competence_selectionnee"]
    st.rerun()

st.subheader(competence["nom"])
st.image(competence["image"], use_container_width=True)
st.write(competence["presentation"])
st.divider()

autorise, date_prochaine, deja_valide = evaluations.peut_retenter(utilisateur["id"], competence_id)

if deja_valide:
    st.success("Cette compétence est déjà validée. Aucune nouvelle tentative n'est possible.")
    st.stop()

if not autorise:
    st.error(
        f"Compétence temporairement bloquée après un échec. "
        f"Prochaine tentative possible {utils.formater_delai(date_prochaine)}."
    )
    st.stop()

# --- Étape 3 : avertissement ---
cle_confirme = f"confirme_{competence_id}"
if cle_confirme not in st.session_state:
    st.session_state[cle_confirme] = False

if not st.session_state[cle_confirme]:
    duree = round(config.NB_QUESTIONS_PAR_TENTATIVE * config.TEMPS_PAR_QUESTION_MIN)
    if utils.afficher_avertissement_evaluation(duree):
        st.session_state[cle_confirme] = True
        st.session_state[f"questions_{competence_id}"] = evaluations.tirer_questions(competence_id)
        st.session_state[f"debut_{competence_id}"] = time.time()
        st.rerun()
    st.stop()

# --- Étape 4 : évaluation en cours, affichée par lots pour ne pas décourager le candidat ---
utils.injecter_protections_anticopie()
utils.injecter_detecteur_focus()

questions = st.session_state[f"questions_{competence_id}"]
duree_totale_s = config.NB_QUESTIONS_PAR_TENTATIVE * config.TEMPS_PAR_QUESTION_MIN * 60
temps_ecoule = time.time() - st.session_state[f"debut_{competence_id}"]
temps_restant = max(0, duree_totale_s - temps_ecoule)

col1, col2 = st.columns([3, 1])
with col2:
    minutes, secondes = divmod(int(temps_restant), 60)
    st.metric("Temps restant", f"{minutes:02d}:{secondes:02d}")

taille_page = config.QUESTIONS_PAR_PAGE
nb_pages = -(-len(questions) // taille_page)  # arrondi supérieur
cle_page = f"page_{competence_id}"
if cle_page not in st.session_state:
    st.session_state[cle_page] = 0
page_courante = st.session_state[cle_page]

temps_ecoule_total = temps_restant <= 0
if temps_ecoule_total:
    st.error("Temps écoulé. L'évaluation est soumise automatiquement avec les réponses actuelles.")
    page_courante = nb_pages - 1  # forcer l'affichage de la dernière page pour le bouton Terminer

st.caption(f"Lot {page_courante + 1} / {nb_pages} — niveau : {questions[page_courante * taille_page]['niveau']}")

debut_lot = page_courante * taille_page
fin_lot = min(debut_lot + taille_page, len(questions))

for i in range(debut_lot, fin_lot):
    q = questions[i]
    st.markdown(f"**Question {i + 1}.** {q['question']}")
    st.radio(
        "Réponse", options=list(range(len(q["choix"]))),
        format_func=lambda idx, q=q: q["choix"][idx],
        key=f"q_{competence_id}_{i}", index=None, label_visibility="collapsed",
    )
    st.divider()

reponses_lot = [st.session_state.get(f"q_{competence_id}_{i}") for i in range(debut_lot, fin_lot)]
lot_incomplet = None in reponses_lot and not temps_ecoule_total

est_dernier_lot = page_courante >= nb_pages - 1

if not est_dernier_lot:
    if st.button("Continuer →", type="primary", disabled=lot_incomplet, use_container_width=True):
        st.session_state[cle_page] = page_courante + 1
        st.rerun()
    if lot_incomplet:
        st.caption("Répondez à toutes les questions de ce lot pour continuer.")
else:
    soumis = st.button("Terminer l'évaluation", type="primary",
                        disabled=lot_incomplet, use_container_width=True)
    if lot_incomplet:
        st.caption("Répondez à toutes les questions de ce lot pour terminer.")

    if soumis or temps_ecoule_total:
        reponses = [st.session_state.get(f"q_{competence_id}_{i}") for i in range(len(questions))]
        reponses = [r if r is not None else -1 for r in reponses]

        note = evaluations.calculer_note(questions, reponses)
        feedback = evaluations.feedback_par_sous_theme(questions, reponses)
        valide, numero, date_prochaine = evaluations.enregistrer_tentative(
            utilisateur["id"], competence_id, note, feedback,
            questions=questions, reponses=reponses,
        )

        cles_a_nettoyer = [cle_confirme, f"questions_{competence_id}", f"debut_{competence_id}", cle_page]
        cles_a_nettoyer += [f"q_{competence_id}_{i}" for i in range(len(questions))]
        for cle in cles_a_nettoyer:
            st.session_state.pop(cle, None)

        if valide:
            st.success(f"Compétence validée avec {note}/20 !")
            certificat = certification.emettre_certificat(utilisateur, competence, note)
            st.info(f"Certificat émis — identifiant public : `{certificat['identifiant_public']}`")
            st.balloons()
        else:
            st.error(f"Note obtenue : {note}/20 — seuil requis : {config.SEUIL_VALIDATION}/20.")
            if feedback:
                st.markdown("**Sous-thèmes à retravailler** *(sans détail des questions)* :")
                for sous_theme, message in feedback.items():
                    st.write(f"- {sous_theme} : {message}")
            else:
                st.write("Aucun sous-thème particulier identifié — révisez l'ensemble du contenu.")
            st.warning(f"Prochaine tentative possible {utils.formater_delai(date_prochaine)}.")