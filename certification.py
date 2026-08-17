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