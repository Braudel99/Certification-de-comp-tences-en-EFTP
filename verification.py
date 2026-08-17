"""
verification.py
Vérification tierce d'un certificat par identifiant public (issu d'un QR code).
Distingue explicitement TROIS cas, pas un simple booléen valide/invalide :

  1. AUTHENTIQUE   : le hash recalculé correspond à l'empreinte ancrée on-chain.
  2. FALSIFIE      : l'identifiant existe, mais le contenu a été modifié après
                      émission -- le hash recalculé NE correspond PLUS à l'empreinte.
  3. INCONNU       : aucun certificat ne correspond à cet identifiant.
"""

import json
import certification
import blockchain
from database import get_connection


def verifier_certificat(identifiant_public: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM certificats WHERE identifiant_public = ?",
            (identifiant_public,),
        ).fetchone()

    if row is None:
        return {"statut": "INCONNU", "message": "Aucun certificat trouvé pour cet identifiant."}

    contenu_stocke = json.loads(row["contenu_json"])
    hash_recalcule = certification.calculer_hash(contenu_stocke)
    hash_ancre = blockchain.recuperer_hash_ancre(row["hash_certificat"])

    if hash_ancre is not None and hash_recalcule == hash_ancre == row["hash_certificat"]:
        return {
            "statut": "AUTHENTIQUE",
            "message": "Certificat valide et conforme à l'enregistrement d'origine.",
            "certificat": contenu_stocke,
        }

    return {
        "statut": "FALSIFIE",
        "message": (
            "Ce certificat ne correspond pas à l'empreinte enregistrée à l'origine. "
            "Le contenu présenté a probablement été modifié après délivrance."
        ),
        "certificat": contenu_stocke,
    }
