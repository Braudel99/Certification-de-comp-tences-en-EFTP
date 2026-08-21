"""
verification.py
Vérification tierce d'un certificat par identifiant public (issu d'un QR code).
Distingue explicitement TROIS cas, pas un simple booléen valide/invalide :

  1. AUTHENTIQUE   : le hash recalculé correspond à l'empreinte ancrée.
  2. FALSIFIE      : l'identifiant existe, mais le contenu a été modifié après
                      émission -- le hash recalculé NE correspond PLUS à l'empreinte.
  3. INCONNU       : aucun certificat ne correspond à cet identifiant.

Si le certificat a été ancré sur une VRAIE blockchain (blockchain_tx_hash renseigné),
la vérification relit directement la transaction sur la chaîne -- c'est la partie de
ce processus qui reste possible même si notre propre base de données est indisponible
ou compromise. Sinon, on retombe sur la vérification via la table locale simulée.
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

    tx_hash = row["blockchain_tx_hash"]
    if tx_hash:
        ancrage_valide = blockchain.verifier_hash_sur_chaine(row["hash_certificat"], tx_hash)
        mode_verification = "blockchain réelle"
    else:
        hash_ancre = blockchain.recuperer_hash_ancre(row["hash_certificat"])
        ancrage_valide = hash_ancre is not None and hash_ancre == row["hash_certificat"]
        mode_verification = "base locale (simulation)"

    if ancrage_valide and hash_recalcule == row["hash_certificat"]:
        return {
            "statut": "AUTHENTIQUE",
            "message": f"Certificat valide et conforme à l'enregistrement d'origine (vérifié via {mode_verification}).",
            "certificat": contenu_stocke,
            "ipfs_cid": row["ipfs_cid"],
            "blockchain_tx_hash": tx_hash,
        }

    return {
        "statut": "FALSIFIE",
        "message": (
            "Ce certificat ne correspond pas à l'empreinte enregistrée à l'origine. "
            "Le contenu présenté a probablement été modifié après délivrance."
        ),
        "certificat": contenu_stocke,
        "ipfs_cid": row["ipfs_cid"],
        "blockchain_tx_hash": tx_hash,
    }