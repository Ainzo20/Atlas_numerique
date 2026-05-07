"""
database.py
-----------
Gestion de la connexion MongoDB et operations de base.

Ce module expose :
- Une connexion unique et reutilisable a MongoDB (pattern Singleton)
- Des fonctions utilitaires pour acceder aux collections
- Une fonction de verification de la connexion
"""

import logging
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from config import MONGODB_URI, MONGODB_DB

# ── Configuration du logger ─────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Instance unique du client MongoDB ──────────────────────────
_client: MongoClient | None = None


def get_client() -> MongoClient:
    """
    Retourne le client MongoDB. Le cree si inexistant (Singleton).

    Returns:
        MongoClient: Instance unique du client MongoDB.

    Raises:
        ConnectionFailure: Si la connexion a MongoDB echoue.
    """
    global _client

    if _client is None:
        logger.info("Initialisation de la connexion MongoDB...")
        _client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000  # timeout 5 secondes
        )
        logger.info("Client MongoDB initialise.")

    return _client


def get_database() -> Database:
    """
    Retourne la base de donnees principale de l'application.

    Returns:
        Database: Instance de la base de donnees MongoDB.
    """
    return get_client()[MONGODB_DB]


def get_collection(name: str) -> Collection:
    """
    Retourne une collection MongoDB par son nom.

    Args:
        name (str): Nom de la collection.

    Returns:
        Collection: Instance de la collection MongoDB.
    """
    return get_database()[name]


def check_connection() -> bool:
    """
    Verifie que la connexion a MongoDB est active.
    Utilise la commande ping de MongoDB.

    Returns:
        bool: True si la connexion est active, False sinon.
    """
    try:
        get_client().admin.command("ping")
        logger.info("Connexion MongoDB OK.")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Connexion MongoDB echouee : {e}")
        return False


# ── Noms des collections ────────────────────────────────────────
# Centralises ici pour eviter les fautes de frappe dans les autres modules

class Collections:
    """
    Constantes des noms de collections MongoDB.
    A utiliser dans tous les autres modules a la place des strings brutes.
    """
    REGIONS          = "regions"
    DEPARTEMENTS     = "departements"
    ARRONDISSEMENTS  = "arrondissements"
    COMMUNES         = "communes"
    VILLAGES         = "villages_quartiers"
    CHEFFERIES       = "chefferies"
    ETHNIES          = "ethnies"
    MARCHES          = "jours_marche"
    LIEUX            = "lieux"
    COOPERATIVES     = "cooperatives"
    EXERCICES        = "exercices"
    TYPES            = "types"
    SOUS_TYPES       = "sous_types"
    TYPES_COMMUNE    = "types_commune"