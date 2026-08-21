"""
ipfs.py
Publication du contenu canonique du certificat sur IPFS (stockage décentralisé),
via le service de pinning Pinata.

Pourquoi un service de pinning : IPFS seul ne garantit pas qu'un contenu reste
disponible -- un nœud doit "épingler" (pin) durablement le contenu pour qu'il
reste accessible dans le temps. Pinata fait ce travail gratuitement pour un usage
modéré, sans avoir à héberger notre propre nœud IPFS.

Nécessite (dans st.secrets) :
    PINATA_JWT = "<jeton généré depuis le tableau de bord Pinata>"

Sans ce secret, publier_sur_ipfs() retourne None -- le certificat reste valide,
simplement sans copie décentralisée (mode dégradé, pratique en développement).
"""

import streamlit as st
import requests

PINATA_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"


def _jeton_pinata():
    try:
        return st.secrets.get("PINATA_JWT")
    except Exception:
        return None


def publier_sur_ipfs(contenu: dict):
    """
    Publie le contenu canonique du certificat sur IPFS et retourne son CID
    (identifiant de contenu, qui permet de le retrouver via n'importe quelle
    passerelle IPFS publique). Retourne None si Pinata n'est pas configuré ou
    en cas d'erreur réseau -- ne doit jamais empêcher l'émission du certificat.
    """
    jeton = _jeton_pinata()
    if not jeton:
        return None
    try:
        reponse = requests.post(
            PINATA_URL,
            headers={"Authorization": f"Bearer {jeton}"},
            json={
                "pinataContent": contenu,
                "pinataMetadata": {"name": f"certificat-{contenu.get('identifiant_public', 'inconnu')}"},
            },
            timeout=15,
        )
        reponse.raise_for_status()
        return reponse.json()["IpfsHash"]
    except Exception:
        return None


def url_ipfs(cid: str) -> str:
    """URL publique via une passerelle IPFS -- lisible sans compte ni logiciel spécial."""
    return f"https://gateway.pinata.cloud/ipfs/{cid}"