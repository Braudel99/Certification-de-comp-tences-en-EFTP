"""
blockchain.py
Squelette d'ancrage de l'empreinte cryptographique.

Deux implémentations possibles, activables via config :
- simulation locale (table blockchain_simulee) : suffisante pour démontrer le concept
  dans le mémoire si le temps ne permet pas d'aller plus loin.
- ancrage réel sur testnet (ex. Polygon Amoy) via web3.py : à activer en évolution,
  la fonction ancrer_hash() est le seul point à remplacer, le reste du dispositif
  (certification.py, verification.py) n'a pas à changer.
"""

from database import get_connection, now_iso


def ancrer_hash(hash_certificat: str) -> str:
    """
    Ancre le hash et retourne l'empreinte réellement enregistrée on-chain.
    Version simulation : on enregistre simplement le hash dans une table dédiée,
    en jouant le rôle d'une chaîne immuable pour la démonstration.
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO blockchain_simulee (hash_ancre, date_ancrage) VALUES (?, ?)",
            (hash_certificat, now_iso()),
        )
    return hash_certificat


def recuperer_hash_ancre(hash_certificat: str):
    """Retourne le hash tel qu'ancré on-chain, ou None s'il n'a jamais été ancré."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT hash_ancre FROM blockchain_simulee WHERE hash_ancre = ?",
            (hash_certificat,),
        ).fetchone()
    return row["hash_ancre"] if row else None
