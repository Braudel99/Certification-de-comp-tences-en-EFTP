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
    Pipeline complet : construit le contenu, calcule le hash, l'ancre sur la
    blockchain (simulée ou réelle selon blockchain.py), puis enregistre le
    certificat off-chain en base. Retourne le certificat créé.
    """
    contenu = construire_contenu_certificat(apprenant, competence, note)
    hash_certificat = calculer_hash(contenu)
    hash_ancre = blockchain.ancrer_hash(hash_certificat)

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO certificats
               (identifiant_public, apprenant_id, competence_id, note_finale,
                date_delivrance, contenu_json, hash_certificat, hash_ancre_blockchain)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contenu["identifiant_public"], apprenant["id"], competence["id"], note,
                contenu["date_delivrance"], json.dumps(contenu, ensure_ascii=False),
                hash_certificat, hash_ancre,
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


def generer_certificat_pdf(contenu: dict, hash_certificat: str) -> bytes:
    """
    Génère le certificat au format PDF (paysage, pleine page), avec le sceau,
    le QR code de vérification et l'empreinte. Le filigrane est explicitement
    contenu dans les limites de la page (clip) pour ne jamais déborder.
    """
    largeur, hauteur = landscape(A4)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    VERT = HexColor("#0F6E56")
    TEXTE = HexColor("#1A1A18")
    TEXTE_SEC = HexColor("#5F5E5A")
    BORDURE = HexColor("#B8AE8E")
    FILIGRANE = HexColor("#0F6E56")

    marge = 20
    c.setFillColor(HexColor("#FBFAF7"))
    c.rect(0, 0, largeur, hauteur, fill=1, stroke=0)

    # --- Filigrane : taille calculée pour tenir dans le cadre à 20°, pas de clip
    # (peu fiable selon les moteurs de rendu PDF -- mieux vaut dimensionner correctement
    # dès le départ que compter sur un recadrage a posteriori).
    c.saveState()
    c.setFillColor(FILIGRANE, alpha=0.06)
    c.setFont("Helvetica-Bold", 55)
    c.translate(largeur / 2, hauteur / 2)
    c.rotate(20)
    c.drawCentredString(0, 0, "GÉNIE ÉLECTRIQUE")
    c.restoreState()

    # --- Cadre décoratif ---
    c.setStrokeColor(VERT)
    c.setLineWidth(2.2)
    c.rect(marge, marge, largeur - 2 * marge, hauteur - 2 * marge)
    c.setStrokeColor(BORDURE)
    c.setLineWidth(0.8)
    c.rect(marge + 10, marge + 10, largeur - 2 * (marge + 10), hauteur - 2 * (marge + 10))

    centre_x = largeur / 2
    y = hauteur - 70

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 11)
    c.drawCentredString(centre_x, y, "DISPOSITIF DE CERTIFICATION DES COMPÉTENCES EN EFTP")
    y -= 16
    c.setFont("Helvetica", 9)
    c.drawCentredString(centre_x, y, "Génie électrique — République du Bénin")

    y -= 42
    c.setFillColor(TEXTE)
    c.setFont("Times-Bold", 32)
    c.drawCentredString(centre_x, y, "CERTIFICAT DE COMPÉTENCE")
    y -= 14
    c.setStrokeColor(VERT)
    c.setLineWidth(2)
    c.line(centre_x - 45, y, centre_x + 45, y)

    y -= 32
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 12)
    c.drawCentredString(centre_x, y, "Ce certificat atteste que")

    y -= 32
    c.setFillColor(VERT)
    c.setFont("Times-BoldItalic", 26)
    c.drawCentredString(centre_x, y, contenu["apprenant_nom"])

    y -= 26
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 12)
    c.drawCentredString(centre_x, y, "a démontré la maîtrise de la compétence")

    y -= 22
    c.setFillColor(TEXTE)
    c.setFont("Times-Bold", 16)
    c.drawCentredString(centre_x, y, f"« {contenu['competence_nom']} »")

    y -= 30
    badge_texte = f"NOTE OBTENUE : {contenu['note']} / {config.NOTE_MAX}   —   SEUIL DE VALIDATION : {config.SEUIL_VALIDATION}/{config.NOTE_MAX}"
    c.setFont("Helvetica-Bold", 10)
    largeur_badge = c.stringWidth(badge_texte, "Helvetica-Bold", 10) + 28
    c.setStrokeColor(VERT)
    c.setLineWidth(1)
    c.roundRect(centre_x - largeur_badge / 2, y - 8, largeur_badge, 20, 10, stroke=1, fill=0)
    c.setFillColor(VERT)
    c.drawCentredString(centre_x, y - 2, badge_texte)

    # --- Sceau (cercles concentriques) ---
    cy_sceau = y - 70
    for rayon in (40, 33, 26):
        c.setStrokeColor(VERT)
        c.setLineWidth(1)
        c.circle(centre_x, cy_sceau, rayon, stroke=1, fill=0)
    c.setFillColor(TEXTE)
    c.setFont("Times-Bold", 12)
    c.drawCentredString(centre_x, cy_sceau + 3, "CERTIFIÉ")
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 7)
    c.drawCentredString(centre_x, cy_sceau - 9, "Compétence validée")

    # --- Bas de page : identifiant, empreinte, QR, date ---
    y_bas = marge + 40
    x_gauche = marge + 45

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 7)
    c.drawString(x_gauche, y_bas + 42, "IDENTIFIANT PUBLIC")
    c.setFont("Courier", 8)
    c.setFillColor(TEXTE)
    c.drawString(x_gauche, y_bas + 32, contenu["identifiant_public"])

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 7)
    c.drawString(x_gauche, y_bas + 18, "EMPREINTE SHA-256")
    c.setFont("Courier", 7)
    c.setFillColor(TEXTE)
    c.drawString(x_gauche, y_bas + 8, hash_certificat)

    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 7)
    c.drawString(x_gauche, y_bas - 6, "VÉRIFICATION")
    c.setFont("Courier", 7)
    c.setFillColor(TEXTE)
    c.drawString(x_gauche, y_bas - 16, config.URL_BASE_VERIFICATION.replace("http://", "").replace("https://", ""))

    qr_bytes = generer_qr_verification(contenu["identifiant_public"])
    qr_image = ImageReader(BytesIO(qr_bytes))
    taille_qr = 62
    c.drawImage(qr_image, centre_x - taille_qr / 2, y_bas - 14, taille_qr, taille_qr)
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 7)
    c.drawCentredString(centre_x, y_bas - 24, "Scanner pour vérifier")

    x_droite = largeur - marge - 45
    c.setFillColor(TEXTE_SEC)
    c.setFont("Helvetica", 7)
    c.drawRightString(x_droite, y_bas + 18, "DATE DE DÉLIVRANCE")
    c.setFillColor(TEXTE)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x_droite, y_bas + 4, contenu["date_delivrance"][:10])

    c.showPage()
    c.save()
    return buffer.getvalue()