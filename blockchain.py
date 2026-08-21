"""
blockchain.py
Ancrage de l'empreinte cryptographique sur une blockchain publique (Polygon Amoy,
réseau de test) -- contrairement à la simulation initiale (une simple table dans
notre propre base), cette empreinte devient vérifiable indépendamment de notre
plateforme, par n'importe qui, via un explorateur de blockchain public
(ex. amoy.polygonscan.com), même si notre plateforme n'est plus accessible.

Fonctionnement : le hash est inscrit dans le champ "data" d'une transaction envoyée
depuis un portefeuille dédié -- pas besoin de smart contract, la transaction
elle-même sert de preuve d'ancrage horodatée et immuable.

Nécessite (dans st.secrets) :
    WALLET_PRIVATE_KEY = "0x..."  -- clé privée d'un portefeuille DÉDIÉ à cet usage,
                                      alimenté en jetons de TEST uniquement (MATIC de
                                      testnet, obtenus gratuitement via un faucet) --
                                      NE JAMAIS utiliser un portefeuille contenant de
                                      vrais fonds pour cette clé.
    RPC_URL (optionnel)          -- point d'accès RPC du réseau ; une valeur publique
                                      par défaut est utilisée si absente.

Si WALLET_PRIVATE_KEY est absent, ou si la transaction échoue pour une raison
quelconque (réseau, jetons de test épuisés...), on retombe automatiquement sur un
ancrage simulé en base locale -- l'émission d'un certificat ne doit jamais être
bloquée par un souci d'infrastructure blockchain.
"""

import streamlit as st
from database import get_connection, now_iso

RPC_URL_DEFAUT = "https://rpc-amoy.polygon.technology"


def _config_wallet():
    try:
        cle_privee = st.secrets.get("WALLET_PRIVATE_KEY")
        rpc_url = st.secrets.get("RPC_URL") or RPC_URL_DEFAUT
    except Exception:
        cle_privee, rpc_url = None, RPC_URL_DEFAUT
    return cle_privee, rpc_url


def _journaliser_erreur(hash_certificat: str, erreur: str):
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO blockchain_erreurs (hash_certificat, erreur, date_erreur) VALUES (?, ?, ?)",
                (hash_certificat, str(erreur)[:500], now_iso()),
            )
    except Exception:
        pass  # la journalisation de l'erreur ne doit jamais elle-même faire planter l'émission


def ancrer_hash(hash_certificat: str) -> dict:
    """
    Ancre le hash sur la blockchain réelle si un portefeuille est configuré, sinon
    simule l'ancrage en base locale (mode développement).

    Retourne un dict {"mode": "reel"|"simule", "reference": ...} :
    - mode "reel"   : reference = hash de la TRANSACTION blockchain (0x...), à
                       vérifier sur un explorateur public (ex. amoy.polygonscan.com)
    - mode "simule" : reference = le hash du certificat lui-même (comportement
                       précédent, vérifiable uniquement via notre propre base)
    """
    cle_privee, rpc_url = _config_wallet()

    if not cle_privee:
        return {"mode": "simule", "reference": _ancrer_hash_simule(hash_certificat)}

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        compte = w3.eth.account.from_key(cle_privee)

        transaction = {
            "from": compte.address,
            "to": compte.address,  # transaction à soi-même : seul le champ "data" compte
            "value": 0,
            "gas": 30000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(compte.address),
            "data": "0x" + hash_certificat.encode("utf-8").hex(),
            "chainId": w3.eth.chain_id,
        }
        transaction_signee = w3.eth.account.sign_transaction(transaction, cle_privee)
        tx_hash = w3.eth.send_raw_transaction(transaction_signee.raw_transaction)
        return {"mode": "reel", "reference": tx_hash.hex()}
    except Exception as e:
        # Ne jamais bloquer l'émission d'un certificat à cause d'un souci réseau/portefeuille --
        # on journalise l'erreur pour investigation et on retombe sur la simulation.
        _journaliser_erreur(hash_certificat, e)
        return {"mode": "simule", "reference": _ancrer_hash_simule(hash_certificat)}


def _ancrer_hash_simule(hash_certificat: str) -> str:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO blockchain_simulee (hash_ancre, date_ancrage) VALUES (?, ?)",
            (hash_certificat, now_iso()),
        )
    return hash_certificat


def verifier_hash_sur_chaine(hash_certificat: str, tx_hash: str) -> bool:
    """
    Relit la transaction sur la blockchain réelle et vérifie que son champ "data"
    correspond bien au hash attendu -- c'est la vérification qui reste possible
    même si notre propre base de données est indisponible ou compromise.
    """
    cle_privee, rpc_url = _config_wallet()
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        tx = w3.eth.get_transaction(tx_hash)
        data_hex = tx["input"]
        if hasattr(data_hex, "hex"):
            data_hex = data_hex.hex()
        data_hex = data_hex[2:] if data_hex.startswith("0x") else data_hex
        hash_sur_chaine = bytes.fromhex(data_hex).decode("utf-8")
        return hash_sur_chaine == hash_certificat
    except Exception:
        return False


def recuperer_hash_ancre(hash_certificat: str):
    """Vérification en mode simulé (repli), utilisée quand aucun tx_hash réel n'existe."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT hash_ancre FROM blockchain_simulee WHERE hash_ancre = ?",
            (hash_certificat,),
        ).fetchone()
    return row["hash_ancre"] if row else None