"""
auth.py
-------
Gestion de l'authentification et des autorisations de l'application.
"""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException, status

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from database import get_collection, Collections

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# MOTS DE PASSE
# ════════════════════════════════════════════════════════════════

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Hache un mot de passe en clair pour stockage en base de donnees.

    Args:
        mot_de_passe (str): Mot de passe fourni par l'utilisateur.

    Returns:
        str: Hash bcrypt du mot de passe (jamais le mot de passe en clair).
    """
    hash_bytes = bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    """
    Compare un mot de passe en clair a un hash stocke en base.

    Args:
        mot_de_passe (str): Mot de passe saisi lors du login.
        hash_stocke (str): Hash bcrypt recupere depuis la collection users.

    Returns:
        bool: True si le mot de passe correspond, False sinon.
    """
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))

# ════════════════════════════════════════════════════════════
# AUTHENTIFICATION + JWT
# ════════════════════════════════════════════════════════════

def authentifier_utilisateur(username: str, password: str) -> dict | None:
    """
    Vérifie les identifiants et retourne l'utilisateur si valide.

    Args:
        username: Nom d'utilisateur saisi.
        password: Mot de passe en clair.

    Returns:
        dict: Document utilisateur (sans le mot de passe haché) ou None.
    """
    collection = get_collection(Collections.USERS)
    utilisateur = collection.find_one({"username": username})

    if not utilisateur:
        return None

    if not verifier_mot_de_passe(password, utilisateur["hashed_password"]):
        return None

    # On retourne l'utilisateur sans le hash pour sécurité
    return {
        "username": utilisateur["username"],
        "role": utilisateur["role"],
        "created_at": utilisateur.get("created_at"),
    }


def creer_token_session(username: str, role: str) -> str:
    """
    Génère un JWT de session pour un utilisateur authentifié.

    Args:
        username: Nom d'utilisateur.
        role: Rôle de l'utilisateur (ex: "admin").

    Returns:
        str: Token JWT encodé.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        "sub": username,                    # subject = identifiant utilisateur
        "role": role,                       # rôle pour les vérifications d'accès
        "exp": expire,                      # date d'expiration
        "iat": datetime.now(timezone.utc),  # date d'émission
        "type": "session",                  # marqueur pour distinguer d'autres tokens
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decoder_token_session(token: str) -> dict | None:
    """
    Décode et valide un token JWT de session.

    Args:
        token: Token JWT reçu du cookie.

    Returns:
        dict: Payload du token si valide, None sinon.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Vérification supplémentaire : s'assurer que c'est bien un token de session
        if payload.get("type") != "session":
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token JWT expiré.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token JWT invalide : {e}")
        return None
    # ════════════════════════════════════════════════════════════
# DÉPENDANCES FASTAPI (AUTH & AUTORISATION)
# ════════════════════════════════════════════════════════════

def get_utilisateur_courant(
    session_token: str = Cookie(None, alias="atlas_session")
) -> dict:
    """
    Extrait et valide le token JWT depuis le cookie de session.
    Retourne les infos de l'utilisateur connecté ou lève une erreur 401.

    Args:
        session_token: Valeur du cookie atlas_session.

    Returns:
        dict: Informations de l'utilisateur connecté.

    Raises:
        HTTPException 401: Si le token est absent, expiré ou invalide.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session manquante. Veuillez vous connecter.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    payload = decoder_token_session(session_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expirée.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    # Pour l'instant, on fait confiance au payload signé par JWT_SECRET.
    # On pourrait ajouter une vérification en base si besoin plus tard.
    return {
        "username": payload["sub"],
        "role": payload["role"],
    }

def get_utilisateur_optionnel(
    session_token: str = Cookie(None, alias="atlas_session")
) -> dict | None:
    """
    Version "douce" de get_utilisateur_courant : ne leve JAMAIS d'erreur.

    Utile pour les routes publiques qui doivent simplement s'adapter selon
    qu'un visiteur est connecte ou non (ex: /api/me pour savoir si on
    affiche le bouton d'import), sans bloquer l'acces des visiteurs
    anonymes qui representent la majorite du trafic du site.

    Args:
        session_token: Valeur du cookie atlas_session (peut etre absent).

    Returns:
        dict | None: Informations de l'utilisateur (username, role) si la
            session est valide, None si absente, expiree ou invalide.
    """
    if not session_token:
        return None

    payload = decoder_token_session(session_token)
    if not payload:
        return None

    return {
        "username": payload["sub"],
        "role": payload["role"],
    }
    
def exiger_admin(utilisateur: dict = Depends(get_utilisateur_courant)) -> dict:
    """
    Dépendance qui vérifie que l'utilisateur connecté a le rôle 'admin'.
    À utiliser dans les routes sensibles (ex: /import).

    Args:
        utilisateur: Résultat injecté par get_utilisateur_courant.

    Returns:
        dict: L'utilisateur si admin.

    Raises:
        HTTPException 403: Si l'utilisateur n'est pas admin.
    """
    if utilisateur.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return utilisateur
