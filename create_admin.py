
"""
create_admin.py
---------------
Script CLI pour créer le premier compte administrateur en base de données.
À exécuter une seule fois, après avoir configuré le .env et la connexion MongoDB.
"""

import sys
import getpass
from datetime import datetime, timezone

from database import get_collection, Collections, check_connection
from auth import hacher_mot_de_passe


def main():
    print("🔑 Création du compte administrateur — Atlas Numérique du Cameroun")
    print("-" * 60)

    username = input("Nom d'utilisateur : ").strip()
    if not username:
        print("❌ Le nom d'utilisateur est obligatoire.")
        sys.exit(1)

    password = getpass.getpass("Mot de passe (min. 6 caractères) : ")
    if len(password) < 6:
        print("❌ Le mot de passe doit contenir au moins 6 caractères.")
        sys.exit(1)

    confirm = getpass.getpass("Confirmer le mot de passe : ")
    if password != confirm:
        print("❌ Les mots de passe ne correspondent pas.")
        sys.exit(1)

    if not check_connection():
        print("❌ Impossible de se connecter à MongoDB. Vérifie tes variables .env")
        sys.exit(1)

    users_col = get_collection(Collections.USERS)
    if users_col.find_one({"username": username}):
        print(f"⚠️  L'utilisateur '{username}' existe déjà en base.")
        sys.exit(0)

    doc = {
        "username": username,
        "hashed_password": hacher_mot_de_passe(password),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    users_col.insert_one(doc)
    print(f"\n✅ Admin '{username}' créé avec succès !")
    print("🚀 Tu peux maintenant te connecter via l'endpoint /api/login")


if __name__ == "__main__":
    main()