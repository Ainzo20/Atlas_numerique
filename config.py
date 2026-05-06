"""
config.py
---------
Chargement et validation des variables d'environnement.
Toute la configuration de l'application passe par ce module.
Ne jamais mettre de valeurs sensibles en dur dans le code.
"""

import os
from dotenv import load_dotenv

# Chargement du fichier .env
load_dotenv()


def get_env_variable(name: str, required: bool = True) -> str:
    """
    Recupere une variable d'environnement par son nom.

    Args:
        name (str): Nom de la variable d'environnement.
        required (bool): Si True, leve une erreur si la variable est absente.

    Returns:
        str: Valeur de la variable d'environnement.

    Raises:
        EnvironmentError: Si la variable est requise et absente.
    """
    value = os.getenv(name)

    if required and not value:
        raise EnvironmentError(
            f"Variable d'environnement manquante : '{name}'. "
            f"Verifiez votre fichier .env."
        )

    return value


# ── Variables exposees ──────────────────────────────────────────
MONGODB_URI: str = get_env_variable("MONGODB_URI")
MONGODB_DB: str  = get_env_variable("MONGODB_DB")