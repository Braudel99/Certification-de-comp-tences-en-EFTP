"""
auth.py
Authentification et gestion des rôles (apprenant / formateur / verificateur).
Squelette simple : à renforcer (salage, sessions expirables) avant toute mise en production réelle.
"""

import hashlib
import re
import sqlite3
import streamlit as st
import config
from database import get_connection, now_iso

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LONGUEUR_MIN_MDP = 8


def hash_mot_de_passe(mot_de_passe: str) -> str:
    return hashlib.sha256(mot_de_passe.encode("utf-8")).hexdigest()


def valider_donnees_inscription(nom: str, email: str, mot_de_passe: str, confirmation: str,
                                 role: str = "apprenant", matricule: str = "") -> list:
    """Retourne la liste des erreurs de validation (vide si tout est correct)."""
    erreurs = []
    if not nom or len(nom.strip()) < 2:
        erreurs.append("Le nom doit contenir au moins 2 caractères.")
    if not REGEX_EMAIL.match(email or ""):
        erreurs.append("L'adresse email n'est pas valide.")
    if len(mot_de_passe or "") < LONGUEUR_MIN_MDP:
        erreurs.append(f"Le mot de passe doit contenir au moins {LONGUEUR_MIN_MDP} caractères.")
    if mot_de_passe != confirmation:
        erreurs.append("Les deux mots de passe ne correspondent pas.")

    if role == "formateur":
        matricule_nettoye = (matricule or "").strip()
        if not matricule_nettoye:
            erreurs.append("Le matricule est obligatoire pour un compte formateur.")
        elif not re.fullmatch(
            rf"\d{{{config.MATRICULE_LONGUEUR_MIN},{config.MATRICULE_LONGUEUR_MAX}}}",
            matricule_nettoye,
        ):
            erreurs.append(
                f"Le matricule doit être une suite de {config.MATRICULE_LONGUEUR_MIN} "
                f"à {config.MATRICULE_LONGUEUR_MAX} chiffres."
            )

    return erreurs


def creer_compte(nom: str, email: str, mot_de_passe: str, role: str = "apprenant",
                  matricule: str = "") -> dict:
    """Crée le compte et retourne l'utilisateur créé. Lève ValueError si l'email existe déjà."""
    matricule_normalise = matricule.strip().upper() if matricule else None
    with get_connection() as conn:
        try:
            conn.execute(
                """INSERT INTO apprenants (nom, email, mot_de_passe_hash, role, date_creation, matricule)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (nom.strip(), email.strip().lower(), hash_mot_de_passe(mot_de_passe), role,
                 now_iso(), matricule_normalise),
            )
        except sqlite3.IntegrityError:
            raise ValueError("Un compte existe déjà avec cet email.")

        row = conn.execute(
            "SELECT * FROM apprenants WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    return dict(row)


def authentifier(email: str, mot_de_passe: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM apprenants WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    if row and row["mot_de_passe_hash"] == hash_mot_de_passe(mot_de_passe):
        return dict(row)
    return None


def utilisateur_connecte():
    return st.session_state.get("utilisateur")


def deconnecter():
    st.session_state.pop("utilisateur", None)