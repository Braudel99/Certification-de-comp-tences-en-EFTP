"""
certification.py
Génération du certificat numérique (off-chain) et calcul de son empreinte cryptographique.
La génération PDF proprement dite (mise en page) est un TODO à brancher sur reportlab
ou weasyprint une fois le squelette validé -- ici on fige le CONTENU du certificat,
qui est ce qui doit être haché, avant toute mise en forme visuelle.
"""

import hashlib
import json
import uuid
from io import BytesIO

import qrcode
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import config
from database import get_connection, now_iso
import blockchain
import ipfs


def construire_contenu_certificat(apprenant: dict, competence: dict, note: float) -> dict:
    """
    Contenu canonique du certificat : c'est CE dict, sérialisé de façon stable,
    qui est haché. Toute modification ultérieure d'un seul caractère change le hash.
    """
    return {
        "identifiant_public": str(uuid.uuid4()),
        "apprenant_nom": apprenant["nom"],
        "apprenant_email": apprenant["email"],
        "competence_id": competence["id"],
        "competence_nom": competence["nom"],
        "note": note,
        "date_delivrance": now_iso(),
    }


def calculer_hash(contenu: dict) -> str:
    """Sérialisation stable (clés triées, séparateurs fixes) avant hachage SHA-256."""
    contenu_serialise = json.dumps(contenu, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(contenu_serialise.encode("utf-8")).hexdigest()


def emettre_certificat(apprenant: dict, competence: dict, note: float) -> dict:
    """
    Pipeline complet : construit le contenu, calcule le hash, publie une copie du
    contenu sur IPFS (disponibilité, indépendante de notre serveur), ancre le hash
    sur la blockchain (réelle si configurée, sinon simulée), puis enregistre le
    certificat off-chain en base. Retourne le certificat créé.
    """
    contenu = construire_contenu_certificat(apprenant, competence, note)
    hash_certificat = calculer_hash(contenu)

    cid_ipfs = ipfs.publier_sur_ipfs(contenu)
    ancrage = blockchain.ancrer_hash(hash_certificat)

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO certificats
               (identifiant_public, apprenant_id, competence_id, note_finale,
                date_delivrance, contenu_json, hash_certificat, hash_ancre_blockchain,
                ipfs_cid, blockchain_tx_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contenu["identifiant_public"], apprenant["id"], competence["id"], note,
                contenu["date_delivrance"], json.dumps(contenu, ensure_ascii=False),
                hash_certificat, ancrage["reference"], cid_ipfs,
                ancrage["reference"] if ancrage["mode"] == "reel" else None,
            ),
        )
    return contenu


def url_verification(identifiant_public: str) -> str:
    """URL complète encodée dans le QR code : ouvre directement la page de
    vérification avec l'identifiant pré-rempli, plutôt qu'un simple texte brut."""
    return f"{config.URL_BASE_VERIFICATION}/Verification_Publique?id={identifiant_public}"


def generer_qr_verification(identifiant_public: str) -> bytes:
    """Génère le QR code (PNG, en mémoire) pointant vers la page de vérification."""
    img = qrcode.make(url_verification(identifiant_public), box_size=8, border=2)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def numero_certificat(contenu: dict) -> str:
    """Numéro court et lisible, dérivé de données déjà existantes (pas de nouvelle
    colonne en base) : CERT-<domaine>-<année>-<6 premiers caractères de l'identifiant>."""
    competence = next(
        (c for c in config.COMPETENCES_MVP if c["id"] == contenu["competence_id"]), None
    )
    code_domaine = competence["domaine_id"] if competence else "XX"
    annee = contenu["date_delivrance"][:4]
    suffixe = contenu["identifiant_public"].replace("-", "")[:6].upper()
    return f"CERT-{code_domaine}-{annee}-{suffixe}"


def generer_certificat_pdf(contenu: dict, hash_certificat: str, ipfs_cid: str = None, blockchain_tx_hash: str = None) -> bytes:
    """
    Génère le certificat au format PDF (paysage, pleine page) : tableau récapitulatif
    de l'épreuve, badge de niveau, sceau, QR code de vérification et empreinte.

    Note : la colonne "Épreuve pratique" est marquée "Non évaluée (QCM uniquement)"
    tant que l'évaluation pratique n'est pas intégrée à la plateforme -- à corriger
    dès qu'elle le sera, pour ne jamais afficher une compétence pratique comme
    validée alors qu'elle n'a pas été réellement observée.
    """
    largeur, hauteur = landscape(A4)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    BLEU_FONCE = HexColor("#1B3A5C")
    VERT = HexColor("#0F6E56")
    TEXTE = HexColor("#1A1A18")
    TEXTE_SEC = HexColor("#5F5E5A")
    BORDURE = HexColor("#B8AE8E")
    ENTETE_TABLE = HexColor("#1B3A5C")
    FOND_TABLE = HexColor("#F3F1EA")

    domaine = next(
        (d for d in config.DOMAINES
         if d["id"] == next((c["domaine_id"] for c in config.COMPETENCES_MVP
                              if c["id"] == contenu["competence_id"]), None)),
        None,
    )
    nom_domaine = domaine["nom"] if domaine else "Génie électrique"

    marge = 20
    c.setFillColor(HexColor("#FBFAF7"))
    c.rect(0, 0, largeur, hauteur, fill=1, stroke=0)

    # --- Filigrane, dimensionné pour tenir dans le cadre ---
    c.saveState()
    c.setFillColor(BLEU_FONCE, alpha=0.05)
    c.setFont("Helvetica-Bold", 50)
    c.translate(largeur / 2, hauteur / 2)
    c.rotate(20)
    c.drawCentredString(0, 0, nom_domaine.upper())
    c.restoreState()

    # --- Cadre décoratif ---
    c.setStrokeColor(BLEU_FONCE)
    c.setLineWidth(2.2)
    c.rect(marge, marge, largeur - 2 * marge, hauteur - 2 * marge)
    c.setStrokeColor(BORDURE)
    c.setLineWidth(0.8)
    c.rect(marge + 10, marge + 10, largeur - 2 * (marge + 10), hauteur - 2 * (marge + 10))

    centre_x = largeur / 2
    y = hauteur - 55

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 11)
    c.drawCentredString(centre_x, y, "DISPOSITIF DE CERTIFICATION DES COMPÉTENCES EN EFTP")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawCentredString(centre_x, y, f"Filière {nom_domaine} — République du Bénin")

    y -= 36
    c.setFillColor(TEXTE)
    c.setFont("Times-Bold", 28)
    c.drawCentredString(centre_x, y, "CERTIFICAT DE COMPÉTENCE")
    y -= 12
    c.setStrokeColor(BLEU_FONCE)
    c.setLineWidth(2)
    c.line(centre_x - 40, y, centre_x + 40, y)

    y -= 24
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 11)
    c.drawCentredString(centre_x, y, "Ce certificat atteste que")

    y -= 26
    c.setFillColor(BLEU_FONCE)
    c.setFont("Times-BoldItalic", 22)
    c.drawCentredString(centre_x, y, contenu["apprenant_nom"])

    y -= 22
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 9.5)
    annee_session = contenu["date_delivrance"][:4]
    texte_intro = (
        "a satisfait aux exigences d'évaluation par compétences du dispositif technopédagogique "
        "numérique de formation, sur la base d'une épreuve de connaissances (QCM), pour la "
        f"compétence détaillée ci-dessous, au titre de la session {annee_session}."
    )
    # découpage manuel sur 2 lignes pour rester centré et lisible
    from reportlab.pdfbase.pdfmetrics import stringWidth
    mots = texte_intro.split()
    lignes, ligne_courante = [], ""
    for mot in mots:
        essai = f"{ligne_courante} {mot}".strip()
        if stringWidth(essai, "Helvetica", 9.5) > largeur - 180:
            lignes.append(ligne_courante)
            ligne_courante = mot
        else:
            ligne_courante = essai
    lignes.append(ligne_courante)
    for ligne in lignes:
        c.drawCentredString(centre_x, y, ligne)
        y -= 13

    # --- Tableau récapitulatif ---
    y -= 14
    largeur_table = largeur - 2 * 70
    x_table = 70
    hauteur_ligne = 26
    colonnes = [0.40, 0.13, 0.20, 0.14, 0.13]  # proportions
    largeurs_col = [largeur_table * p for p in colonnes]
    entetes = ["Compétence évaluée", "Épreuve QCM", "Épreuve pratique", "Niveau atteint", "Date de validation"]

    c.setFillColor(ENTETE_TABLE)
    c.rect(x_table, y - hauteur_ligne, largeur_table, hauteur_ligne, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 8.5)
    x_cursor = x_table
    for entete, larg in zip(entetes, largeurs_col):
        c.drawString(x_cursor + 6, y - hauteur_ligne + 9, entete)
        x_cursor += larg

    y -= hauteur_ligne
    c.setFillColor(FOND_TABLE)
    c.rect(x_table, y - hauteur_ligne, largeur_table, hauteur_ligne, fill=1, stroke=0)
    c.setStrokeColor(BORDURE)
    c.rect(x_table, y - hauteur_ligne, largeur_table, hauteur_ligne, fill=0, stroke=1)

    valeurs = [
        contenu["competence_nom"],
        f"{contenu['note']} / {config.NOTE_MAX}",
        "Non évaluée (QCM uniquement)",
        "MAÎTRISÉ" if contenu["note"] >= config.SEUIL_VALIDATION else "NON ATTEINT",
        contenu["date_delivrance"][:10],
    ]
    x_cursor = x_table
    for i, (valeur, larg) in enumerate(zip(valeurs, largeurs_col)):
        c.setFillColor(TEXTE)
        c.setFont("Helvetica-Bold" if i == 3 else "Helvetica", 8.5)
        if i == 3:
            c.setFillColor(VERT if contenu["note"] >= config.SEUIL_VALIDATION else HexColor("#B3261E"))
        texte_cell = valeur if len(valeur) < 46 else valeur[:43] + "…"
        c.drawString(x_cursor + 6, y - hauteur_ligne + 9, texte_cell)
        x_cursor += larg
    y -= hauteur_ligne

    y -= 22
    c.setFillColor(TEXTE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(centre_x, y, f"N° DE CERTIFICAT : {numero_certificat(contenu)}")

    # --- Sceau ---
    cy_sceau = y - 55
    for rayon in (32, 27, 22):
        c.setStrokeColor(BLEU_FONCE)
        c.setLineWidth(1)
        c.circle(centre_x, cy_sceau, rayon, stroke=1, fill=0)
    c.setFillColor(TEXTE)
    c.setFont("Times-Bold", 10)
    c.drawCentredString(centre_x, cy_sceau + 3, "CERTIFIÉ")
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 6)
    c.drawCentredString(centre_x, cy_sceau - 7, "Compétence validée")

    # --- Bas de page ---
    y_bas = marge + 38
    x_gauche = marge + 30

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 6.5)
    c.drawString(x_gauche, y_bas + 34, "IDENTIFIANT PUBLIC")
    c.setFont("Courier", 6.5)
    c.setFillColor(TEXTE)
    c.drawString(x_gauche, y_bas + 25, contenu["identifiant_public"])

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 6.5)
    c.drawString(x_gauche, y_bas + 13, "EMPREINTE SHA-256 (extrait)")
    c.setFont("Courier", 6.5)
    c.setFillColor(TEXTE)
    c.drawString(x_gauche, y_bas + 4, hash_certificat[:24] + "..." + hash_certificat[-8:])

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 6.5)
    c.drawString(x_gauche, y_bas - 8, "VÉRIFICATION")
    c.setFont("Courier", 6.5)
    c.setFillColor(TEXTE)
    c.drawString(x_gauche, y_bas - 17, config.URL_BASE_VERIFICATION.replace("http://", "").replace("https://", ""))

    if blockchain_tx_hash:
        c.setFillColor(TEXTE_SEC)
        c.setFont("Helvetica", 6)
        c.drawString(x_gauche, y_bas - 27, f"Tx blockchain : {blockchain_tx_hash[:24]}...")
    if ipfs_cid:
        c.setFillColor(TEXTE_SEC)
        c.setFont("Helvetica", 6)
        c.drawString(x_gauche, y_bas - 35, f"IPFS : {ipfs_cid}")

    x_droite = largeur - marge - 30
    taille_qr = 55
    qr_bytes = generer_qr_verification(contenu["identifiant_public"])
    qr_image = ImageReader(BytesIO(qr_bytes))
    c.drawImage(qr_image, x_droite - taille_qr, y_bas - 12, taille_qr, taille_qr)
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(x_droite - taille_qr / 2, y_bas - 22, "Scanner pour vérifier")

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 6.5)
    c.drawRightString(x_droite - taille_qr - 20, y_bas + 20, "DATE DE DÉLIVRANCE")
    c.setFillColor(TEXTE)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x_droite - taille_qr - 20, y_bas + 8, contenu["date_delivrance"][:10])

    c.showPage()
    c.save()
    return buffer.getvalue()