import  secrets
import hashlib
from datetime import datetime, timezone

from fastapi import Security, HTTPException, status, Cookie
from fastapi.security import APIKeyHeader
from database import get_collection, Collections

# 1. CONFIGURATION DU HEADER
# Cela indique à FastAPI de chercher la clé dans l'en-tête "X-API-Key"
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # Permet de ne pas lever une erreur automatiquement(ont la gere nous meme) si la clé est absente
    description="Clé API pour l'authentification"
    )
# 2. GÉNÉRATION ET STOCKAGE DE LA CLÉ API
def generer_api_key(client_name: str, scopes: list[str] = ["read"]) -> dict:
    """
    Génère une clé aléatoire, la hache, et la stocke dans MongoDB.
    Retourne la clé EN CLAIR une seule fois pour l'administrateur.
    """
    # Génère une chaîne aléatoire sécurisée (ex: atlas_live_aB3dE5fG...)
    raw_key = f"atlas_live_{secrets.token_urlsafe(32)}"
    
    # Hachage SHA-256 : on ne stocke JAMAIS la clé en clair dans la BDD
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    # Préfixe pour identification visuelle rapide dans la BDD (ex: atlas_live_aB3)
    key_prefix = raw_key[:15] 
    
    # Document à insérer dans MongoDB
    doc = {
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "client_name": client_name,
        "scopes": scopes,  # ex: ["read"] ou ["read", "write"]
        "created_at": datetime.now(timezone.utc),
        "last_used_at": None,
        "is_active": True,
    }
    
    # Insertion dans la collection api_keys
    get_collection(Collections.API_KEYS).insert_one(doc)
    
    return {
        "api_key": raw_key,
        "client_name": client_name,
        "scopes": scopes,
        "message": "Conservez cette clé précieusement, elle ne sera plus jamais affichée."
    }
    
    # 3. VÉRIFICATION DE LA CLÉ
def verifier_api_key(raw_key: str) -> dict | None:
    """
    Prend la clé reçue du client, la hache, et cherche une correspondance dans la BDD.
    """
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    # On cherche une clé active avec cette empreinte digitale
    doc = get_collection(Collections.API_KEYS).find_one({
        "key_hash": key_hash,
        "is_active": True
    })
    
    if doc:
        # Mise à jour de la date de dernière utilisation (utile pour l'audit)
        get_collection(Collections.API_KEYS).update_one(
            {"_id": doc["_id"]},
            {"$set": {"last_used_at": datetime.now(timezone.utc)}}
        )
    
    return doc

# 4. DÉPENDANCE FASTAPI (Le garde de sécurité)
async def valider_api_key(
    api_key_from_header: str = Security(api_key_header),
    atlas_session: str | None = Cookie(default=None)
) -> dict:
    """
    Valide l'authentification en acceptant soit le header X-API-Key (mobile/scripts),
    soit le cookie atlas_session (dashboard web).
    """
    # On prend le header en priorité, sinon on prend le cookie
    raw_key = api_key_from_header or atlas_session
    
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise. Clé API ou session manquante."
        )
    
    doc = verifier_api_key(raw_key)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide, expirée ou révoquée."
        )
    
    return doc # Retourne les infos du client (nom, scopes, etc.)

# 5. VÉRIFICATION DES PERMISSIONS (Scopes)
def require_scope(scope_requis: str):
    """
    Factory qui vérifie en plus que le client a la permission spécifique.
    Utilisation dans main.py : Depends(require_scope("write"))
    """
    async def _verifier(client: dict = Security(valider_api_key)):
        if scope_requis not in client.get("scopes", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Votre clé n'a pas la permission '{scope_requis}'."
            )
        return client
    return _verifier