"""
main.py
-------
Point d'entree de l'application FastAPI.
"""

import io
import logging
from datetime import datetime, timezone
import pandas as pd
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, Depends, Cookie, Form, Response
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from auth import require_scope, valider_api_key, verifier_api_key

from config import MONGODB_DB
from database import Collections, check_connection, get_collection, inserer_toutes_communes
from parser import parser_csv


# Import des schemas de documentation
from schemas import (
    ErrorResponse, HealthResponse, StatsResponse, ImportReportResponse,
    RegionsListResponse, RegionDetailResponse, DepartementDetailResponse,
    ArrondissementDetailResponse, CommunesListResponse, CommuneDetailResponse,
    SousDocumentListResponse, LieuxTypesResponse,
    SyncStatusResponse, SyncChangesResponse, SyncFullResponse
)

# ── Configuration du logger global ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
)
logger = logging.getLogger(__name__)

# ── Initialisation de l'application FastAPI ─────────────────────
app = FastAPI(
    title="Atlas Numerique du Cameroun - API",
    description="""
## Bienvenue sur l'API de l'Atlas Numerique

Cette API centralise les donnees geographiques et administratives du Cameroun.

### Guide de Synchronisation Mobile
1. **Premiere installation** : Appelez `GET /sync/full`.
2. **Sync incrementale** : 
   - Appelez `GET /sync/status` pour comparer les timestamps.
   - Si des changements existent, appelez `GET /sync/changes?since=VOTRE_TIMESTAMP`.
""",
    version="1.0.0",
    openapi_tags=[
        {"name": "Sante & Stats", "description": "Monitoring et compteurs globaux."},
        {"name": "Import & Export", "description": "Manipulation des fichiers CSV/Excel."},
        {"name": "Hierarchie", "description": "Navigation : Regions > Departements > Arrondissements."},
        {"name": "Communes & Lieux", "description": "Details des communes et points d'interet."},
        {"name": "Sync Mobile", "description": "Endpoints optimises pour la synchronisation offline-first."},
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "list",
        "tryItOutEnabled": True,
    }
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ════════════════════════════════════════════════════════════════
# UTILITAIRES INTERNES
# ════════════════════════════════════════════════════════════════

def valider_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f"ID invalide : '{id_str}'.")

def serialiser_doc(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc

def fetch_sous_docs(collection_nom: str, id_commune: str) -> list[dict]:
    docs = list(get_collection(collection_nom).find({"id_commune": id_commune}))
    return [serialiser_doc(doc) for doc in docs]

def remonter_hierarchie(id_arrondissement: str) -> dict:
    arrondissement = get_collection(Collections.ARRONDISSEMENTS).find_one({"_id": ObjectId(id_arrondissement)})
    departement = None
    region = None

    if arrondissement:
        arrondissement = serialiser_doc(arrondissement)
        departement = get_collection(Collections.DEPARTEMENTS).find_one({"_id": ObjectId(arrondissement["id_departement"])})
        if departement:
            departement = serialiser_doc(departement)
            region = get_collection(Collections.REGIONS).find_one({"_id": ObjectId(departement["id_region"])})
            if region:
                region = serialiser_doc(region)

    return {"arrondissement": arrondissement, "departement": departement, "region": region}

# ════════════════════════════════════════════════════════════════
# ROUTES GENERALES
# ════════════════════════════════════════════════════════════════
@app.get("/", include_in_schema=False)
def servir_interface(atlas_session: str | None = Cookie(default=None)):
    logger.info(f"🔍 Requête sur '/' reçue. Cookie 'atlas_session' présent : {bool(atlas_session)}")
    
    if not atlas_session:
        logger.warning("⚠️ Aucun cookie trouvé. Redirection vers /login.")
        return RedirectResponse(url="/login", status_code=302)
    
    client = verifier_api_key(atlas_session)
    if not client:
        logger.warning(f"⚠️ Cookie présent mais CLÉ INVALIDE ou RÉVOQUÉE ({atlas_session[:15]}...). Redirection et suppression du cookie.")
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("atlas_session")
        return response
    
    logger.info("✅ Authentification réussie. Service de index.html.")
    return FileResponse("static/index.html")

@app.get("/login", include_in_schema=False)
def servir_login():
    """Sert la page de connexion (publique, sans authentification)."""
    return FileResponse("static/login.html")

@app.post("/api/login", include_in_schema=False)
async def traiter_login(
    api_key: str = Form(...)
):
    """
    Reçoit la clé API du formulaire, la vérifie, et crée le cookie de session si elle est valide.
    """
    # 1. Nettoyer les espaces et vérifier la clé
    clean_api_key = api_key.strip()
    logger.info(f"Tentative de connexion avec la clé (début) : {clean_api_key[:15]}...")
    
    client = verifier_api_key(clean_api_key)
    
    if not client:
        logger.warning("⚠️ ÉCHEC : La clé API est invalide ou introuvable en base de données.")
        return RedirectResponse(url="/login?error=invalid_key", status_code=302)
    
    logger.info("✅ SUCCÈS : Clé valide. Préparation de la redirection avec cookie.")
    
    # 2. Créer l'objet de réponse de redirection
    response = RedirectResponse(url="/", status_code=302)
    
    # 3. ATTACHER le cookie directement à cet objet de redirection
    response.set_cookie(
        key="atlas_session",
        value=clean_api_key,
        httponly=True,      # Invisible au JavaScript
        secure=True,       # Mettre à True uniquement en production avec HTTPS
        samesite="lax",     # Protection basique contre les attaques CSRF
        max_age=86400 * 7   # Le cookie expire dans 7 jours
    )
    
    # 4. Retourner la réponse (qui contient maintenant à la fois la redirection ET le cookie)
    return response

@app.get("/health", tags=["Sante & Stats"], response_model=HealthResponse, responses={500: {"model": ErrorResponse}})
def verifier_sante():
    mongodb_ok = check_connection()
    return {"statut": "en ligne", "mongodb": "connecte" if mongodb_ok else "deconnecte", "base_de_donnees": MONGODB_DB}

@app.get("/stats", tags=["Sante & Stats"], response_model=StatsResponse, responses={500: {"model": ErrorResponse}})
def statistiques_globales():
    return {
        "regions": get_collection(Collections.REGIONS).count_documents({}),
        "departements": get_collection(Collections.DEPARTEMENTS).count_documents({}),
        "arrondissements": get_collection(Collections.ARRONDISSEMENTS).count_documents({}),
        "communes": get_collection(Collections.COMMUNES).count_documents({}),
        "villages": get_collection(Collections.VILLAGES).count_documents({}),
        "chefferies": get_collection(Collections.CHEFFERIES).count_documents({}),
        "ethnies": get_collection(Collections.ETHNIES).count_documents({}),
        "marches": get_collection(Collections.MARCHES).count_documents({}),
        "lieux": get_collection(Collections.LIEUX).count_documents({}),
        "cooperatives": get_collection(Collections.COOPERATIVES).count_documents({}),
        "exercices": get_collection(Collections.EXERCICES).count_documents({}),
    }
    

# ════════════════════════════════════════════════════════════════
# ROUTE IMPORT
# ════════════════════════════════════════════════════════════════

@app.post(
    "/import", 
    tags=["Import & Export"],
    response_model=ImportReportResponse,
    summary="Importer un fichier CSV KoboCollect (Authentification requise)",
    description="Necessite une cle API valide avec le scope 'write'.",
    responses={
         # [AUTH] Documentation des erreurs d'authentification
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Clef invalide ou permissions insuffisantes", "model": ErrorResponse},
        400: {"description": "Fichier invalide ou erreur de parsing", "model": ErrorResponse},
        500: {"description": "Erreur interne lors de l'insertion", "model": ErrorResponse}
    }
)
async def importer_csv(
    fichier: UploadFile = File(..., description="Fichier CSV KoboCollect a uploader"),
    client: dict = Depends(require_scope("write"))
    ):
    logger.info(f"Import initiee par le client : {client['client_name']} (Scopes: {client['scopes']})")

    if not fichier.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Le fichier doit etre au format CSV (.csv).")

    logger.info(f"Fichier recu : {fichier.filename}")
    try:
        contenu = await fichier.read()
    except Exception as erreur:
        raise HTTPException(status_code=500, detail=f"Impossible de lire le fichier : {erreur}")

    try:
        communes_parsees = parser_csv(contenu)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=f"Erreur de format CSV : {erreur}")

    if not communes_parsees:
        raise HTTPException(status_code=400, detail="Aucune commune valide trouvee dans le fichier CSV.")

    try:
        rapport = inserer_toutes_communes(communes_parsees)
    except Exception as erreur:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'insertion en base de donnees : {erreur}")

    logger.info(f"Import termine — {rapport['succes']} succes / {rapport['erreurs']} erreurs.")
    return rapport

# ════════════════════════════════════════════════════════════════
# ROUTES HIERARCHIE
# ════════════════════════════════════════════════════════════════

@app.get(
    "/regions",
    tags=["Hierarchie"],
    response_model=RegionsListResponse,
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
def lister_regions(client: dict = Depends(require_scope("read"))):
    logger.info(f"Liste des regions consultee par : {client['client_name']}")
    regions = list(get_collection(Collections.REGIONS).find())
    for region in regions:
        id_region = str(region["_id"])
        region["_id"] = id_region
        region["nb_departements"] = get_collection(Collections.DEPARTEMENTS).count_documents({"id_region": id_region})
    return {"total": len(regions), "regions": regions}

@app.get(
    "/regions/{id_region}"
    , tags=["Hierarchie"],
    response_model=RegionDetailResponse,
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    })
def detail_region(id_region: str, client: dict = Depends(require_scope("read"))):
    
    objet_id = valider_object_id(id_region)
    region = get_collection(Collections.REGIONS).find_one({"_id": objet_id})
    if not region:
        raise HTTPException(status_code=404, detail=f"Region introuvable pour l'ID : {id_region}.")
    
    region = serialiser_doc(region)
    departements = list(get_collection(Collections.DEPARTEMENTS).find({"id_region": id_region}))
    for d in departements:
        id_dept = str(d["_id"])
        d["_id"] = id_dept
        d["nb_arrondissements"] = get_collection(Collections.ARRONDISSEMENTS).count_documents({"id_departement": id_dept})

    return {"region": region, "departements": departements}

@app.get(
    "/departements/{id_departement}",
    tags=["Hierarchie"], response_model=DepartementDetailResponse, 
   responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    })
def detail_departement(id_departement: str, client: dict = Depends(require_scope("read"))):
    objet_id = valider_object_id(id_departement)
    departement = get_collection(Collections.DEPARTEMENTS).find_one({"_id": objet_id})
    if not departement:
        raise HTTPException(status_code=404, detail=f"Departement introuvable pour l'ID : {id_departement}.")
    
    departement = serialiser_doc(departement)
    arrondissements = list(get_collection(Collections.ARRONDISSEMENTS).find({"id_departement": id_departement}))
    for a in arrondissements:
        id_arr = str(a["_id"])
        a["_id"] = id_arr
        a["nb_communes"] = get_collection(Collections.COMMUNES).count_documents({"id_arrondissement": id_arr})

    return {"departement": departement, "arrondissements": arrondissements}

@app.get(
    "/arrondissements/{id_arrondissement}",
    tags=["Hierarchie"], response_model=ArrondissementDetailResponse,
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    })
def detail_arrondissement(id_arrondissement: str, client: dict = Depends(require_scope("read"))):
    objet_id = valider_object_id(id_arrondissement)
    arrondissement = get_collection(Collections.ARRONDISSEMENTS).find_one({"_id": objet_id})
    if not arrondissement:
        raise HTTPException(status_code=404, detail=f"Arrondissement introuvable pour l'ID : {id_arrondissement}.")
    
    arrondissement = serialiser_doc(arrondissement)
    communes = list(get_collection(Collections.COMMUNES).find({"id_arrondissement": id_arrondissement}, {"nom": 1, "coordonnees": 1, "connectivite_constante": 1, "contact_mairie": 1, "langues_locales": 1}))
    for c in communes:
        c["_id"] = str(c["_id"])

    return {"arrondissement": arrondissement, "communes": communes}

# ════════════════════════════════════════════════════════════════
# ROUTES COMMUNES
# ════════════════════════════════════════════════════════════════

@app.get(
    "/communes",
    tags=["Communes & Lieux"],
    response_model=CommunesListResponse, 
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    description="La recherche par nom est insensible a la casse."
)
def lister_communes(
    region: str = Query(default=None, description="Filtrer par nom de region", examples=["Centre", "Littoral"]),
    departement: str = Query(default=None, description="Filtrer par nom de departement", examples=["Mfoundi", "Wouri"]),
    client: dict = Depends(require_scope("read"))
):
    ids_arrondissements_valides = None
    if region or departement:
        filtre_region = {"nom": {"$regex": region, "$options": "i"}} if region else {}
        ids_regions = [str(r["_id"]) for r in get_collection(Collections.REGIONS).find(filtre_region, {"_id": 1})]
        if not ids_regions: return {"total": 0, "communes": []}

        filtre_dept = {"id_region": {"$in": ids_regions}}
        if departement: filtre_dept["nom"] = {"$regex": departement, "$options": "i"}
        
        ids_departements = [str(d["_id"]) for d in get_collection(Collections.DEPARTEMENTS).find(filtre_dept, {"_id": 1})]
        if not ids_departements: return {"total": 0, "communes": []}

        ids_arrondissements_valides = [str(a["_id"]) for a in get_collection(Collections.ARRONDISSEMENTS).find({"id_departement": {"$in": ids_departements}}, {"_id": 1})]
        if not ids_arrondissements_valides: return {"total": 0, "communes": []}

    filtre_commune = {"id_arrondissement": {"$in": ids_arrondissements_valides}} if ids_arrondissements_valides else {}
    communes = list(get_collection(Collections.COMMUNES).find(filtre_commune, {"nom": 1, "id_arrondissement": 1, "coordonnees": 1, "connectivite_constante": 1, "langues_locales": 1, "contact_mairie": 1}))

    resultats = []
    for commune in communes:
        commune = serialiser_doc(commune)
        hierarchie = remonter_hierarchie(commune["id_arrondissement"])
        resultats.append({
            "commune": commune,
            "region": hierarchie["region"]["nom"] if hierarchie["region"] else None,
            "departement": hierarchie["departement"]["nom"] if hierarchie["departement"] else None,
            "arrondissement": hierarchie["arrondissement"]["nom"] if hierarchie["arrondissement"] else None,
        })
    return {"total": len(resultats), "communes": resultats}

@app.get(
    "/communes/{id_commune}",
    tags=["Communes & Lieux"], 
    response_model=CommuneDetailResponse, 
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    })
def detail_commune(id_commune: str, client: dict = Depends(require_scope("read"))):
    objet_id = valider_object_id(id_commune)
    commune = get_collection(Collections.COMMUNES).find_one({"_id": objet_id})
    if not commune:
        raise HTTPException(status_code=404, detail=f"Commune introuvable pour l'ID : {id_commune}.")
    
    commune = serialiser_doc(commune)
    hierarchie = remonter_hierarchie(commune["id_arrondissement"])

    return {
        "commune": commune, "hierarchie": hierarchie,
        "villages": fetch_sous_docs(Collections.VILLAGES, id_commune),
        "chefferies": fetch_sous_docs(Collections.CHEFFERIES, id_commune),
        "ethnies": fetch_sous_docs(Collections.ETHNIES, id_commune),
        "marches": fetch_sous_docs(Collections.MARCHES, id_commune),
        "lieux": fetch_sous_docs(Collections.LIEUX, id_commune),
        "cooperatives": fetch_sous_docs(Collections.COOPERATIVES, id_commune),
        "exercices": fetch_sous_docs(Collections.EXERCICES, id_commune),
    }

# ════════════════════════════════════════════════════════════════
# ROUTES SOUS-DOCUMENTS (Pattern réutilisé pour la propreté)
# ════════════════════════════════════════════════════════════════

def creer_route_sous_document(nom_collection: str, nom_endpoint: str, description: str):
    """Fonction utilitaire pour éviter de répéter 100 lignes de code identique"""
    @app.get(
        f"/{nom_endpoint}",
        tags=["Communes & Lieux"],
       responses={
            401: {"description": "Clef API manquante", "model": ErrorResponse},
            403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
            500: {"model": ErrorResponse}
        })
    def lister(
        id_commune: str = Query(default=None, description="Filtrer par ID MongoDB de la commune", examples=["60d5ec49f1b2c8b1f8e4e1a2"]),
         client: dict = Depends(require_scope("read"))
    ):
        filtre = {"id_commune": id_commune} if id_commune else {}
        docs = list(get_collection(nom_collection).find(filtre))
        for doc in docs: doc["_id"] = str(doc["_id"])
        return {"total": len(docs), "data": docs} # "data" correspond au schema SousDocumentListResponse

# Génération automatique des routes simples
creer_route_sous_document(Collections.VILLAGES, "villages", "Liste des villages")
creer_route_sous_document(Collections.CHEFFERIES, "chefferies", "Liste des chefferies")
creer_route_sous_document(Collections.ETHNIES, "ethnies", "Liste des ethnies")
creer_route_sous_document(Collections.MARCHES, "marches", "Liste des marches")
creer_route_sous_document(Collections.COOPERATIVES, "cooperatives", "Liste des cooperatives")
creer_route_sous_document(Collections.EXERCICES, "exercices", "Liste des exercices")

@app.get(
    "/lieux/types",
    tags=["Communes & Lieux"],
    response_model=LieuxTypesResponse,
     responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        500: {"model": ErrorResponse}
    })

def lister_types_lieux(client: dict = Depends(require_scope("read"))):
    pipeline = [{"$group": {"_id": "$type_nom", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    resultats = list(get_collection(Collections.LIEUX).aggregate(pipeline))
    return {"types": [{"type": r["_id"], "count": r["count"]} for r in resultats if r["_id"]]}

@app.get(
    "/lieux",
    tags=["Communes & Lieux"],
     responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
def lister_lieux(
    id_commune: str = Query(default=None, description="Filtrer par ID commune", examples=["60d5ec49f1b2c8b1f8e4e1a2"]),
    type_lieu: str = Query(default=None, description="Filtrer par type (ex: scolaire, urgence)", examples=["scolaire", "urgence"]),
    client: dict = Depends(require_scope("read"))
):
    filtre = {}
    if id_commune: filtre["id_commune"] = id_commune
    if type_lieu: filtre["type_nom"] = {"$regex": type_lieu, "$options": "i"}
    
    lieux = list(get_collection(Collections.LIEUX).find(filtre))
    for l in lieux: l["_id"] = str(l["_id"])
    return {"total": len(lieux), "data": lieux}

# ════════════════════════════════════════════════════════════════
# ROUTE EXPORT
# ════════════════════════════════════════════════════════════════

@app.get(
    "/export", tags=["Import & Export"],
   responses={
        200: {"description": "Fichier genere avec succes (CSV ou Excel)"},
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        400: {"description": "Format invalide", "model": ErrorResponse},
        404: {"description": "Aucune commune trouvee", "model": ErrorResponse}
    }
)
def exporter_donnees(
    format: str = Query(default="csv", description="Format d'export", examples=["csv", "excel"]),
    region: str = Query(default=None, description="Filtrer par nom de region", examples=["Centre", "Littoral"]),
    client: dict = Depends(require_scope("read")) 
):
    if format not in ("csv", "excel"):
        raise HTTPException(status_code=400, detail="Format invalide. Utilisez 'csv' ou 'excel'.")

    resultats = lister_communes(region=region)
    communes = resultats["communes"]
    if not communes:
        raise HTTPException(status_code=404, detail="Aucune commune trouvee pour cet export.")

    lignes = []
    for item in communes:
        c, contact, coords = item["commune"], item["commune"].get("contact_mairie", {}), item["commune"].get("coordonnees", {})
        lignes.append({
            "ID": c.get("_id"), "Region": item.get("region"), "Departement": item.get("departement"),
            "Arrondissement": item.get("arrondissement"), "Commune": c.get("nom"),
            "Telephone": ", ".join(contact.get("telephones", [])), "Mail": ", ".join(contact.get("mails", [])),
            "Code postal": contact.get("code_postal"), "Latitude": coords.get("latitude"), "Longitude": coords.get("longitude"),
            "Connectivite": "Oui" if c.get("connectivite_constante") else "Non",
            "Langues locales": " | ".join(c.get("langues_locales", [])),
        })

    df = pd.DataFrame(lignes)
    buffer = io.BytesIO()
    if format == "csv":
        df.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")
        media_type, filename = "text/csv", "communes_export.csv"
    else:
        df.to_excel(buffer, index=False, engine="openpyxl")
        media_type, filename = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "communes_export.xlsx"
    
    buffer.seek(0)
    return StreamingResponse(buffer, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

# ════════════════════════════════════════════════════════════════
# ROUTES SYNCHRONISATION MOBILE
# ════════════════════════════════════════════════════════════════

@app.get(
    "/sync/status", 
    tags=["Sync Mobile"], 
    response_model=SyncStatusResponse, 
     responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
    )
def sync_status(client: dict = Depends(require_scope("read"))):
    logger.info(f"Sync status consultee par : {client['client_name']}")
    collections = {
        "regions": Collections.REGIONS, "departements": Collections.DEPARTEMENTS, "arrondissements": Collections.ARRONDISSEMENTS,
        "communes": Collections.COMMUNES, "villages": Collections.VILLAGES, "chefferies": Collections.CHEFFERIES,
        "ethnies": Collections.ETHNIES, "marches": Collections.MARCHES, "lieux": Collections.LIEUX,
        "cooperatives": Collections.COOPERATIVES, "exercices": Collections.EXERCICES,
    }
    status = {}
    for nom, col_name in collections.items():
        dernier = get_collection(col_name).find_one({"updated_at": {"$exists": True}}, sort=[("updated_at", -1)])
        status[nom] = dernier["updated_at"].isoformat() if dernier and dernier.get("updated_at") else None
    
    return {"server_time": datetime.now(timezone.utc).isoformat(), "collections": status}

@app.get(
    "/sync/changes",
    tags=["Sync Mobile"], 
    response_model=SyncChangesResponse,
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        400: {"description": "Timestamp invalide", "model": ErrorResponse}
    }
)
def sync_changes(
    since: str = Query(..., description="Timestamp ISO 8601 de la derniere sync du mobile", examples=["2026-05-01T00:00:00Z", "2026-06-01T14:30:00+00:00"]),
    client: dict = Depends(require_scope("read"))
):
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Timestamp invalide : '{since}'. Format attendu : ISO 8601 (ex: 2026-05-01T00:00:00Z)")

    filtre_date = {"updated_at": {"$gt": since_dt}}
    def fetch_changes(collection_nom: str) -> list[dict]:
        docs = list(get_collection(collection_nom).find(filtre_date))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            if doc.get("created_at"): doc["created_at"] = doc["created_at"].isoformat()
            if doc.get("updated_at"): doc["updated_at"] = doc["updated_at"].isoformat()
        return docs

    return {
        "since": since, "server_time": datetime.now(timezone.utc).isoformat(),
        "changes": {
            "regions": fetch_changes(Collections.REGIONS), "departements": fetch_changes(Collections.DEPARTEMENTS),
            "arrondissements": fetch_changes(Collections.ARRONDISSEMENTS), "communes": fetch_changes(Collections.COMMUNES),
            "villages": fetch_changes(Collections.VILLAGES), "chefferies": fetch_changes(Collections.CHEFFERIES),
            "ethnies": fetch_changes(Collections.ETHNIES), "marches": fetch_changes(Collections.MARCHES),
            "lieux": fetch_changes(Collections.LIEUX), "cooperatives": fetch_changes(Collections.COOPERATIVES),
            "exercices": fetch_changes(Collections.EXERCICES),
        }
    }

@app.get(
    "/sync/full",
    tags=["Sync Mobile"],
    response_model=SyncFullResponse,
    responses={
        401: {"description": "Clef API manquante", "model": ErrorResponse},
        403: {"description": "Permissions insuffisantes", "model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
def sync_full(client: dict = Depends(require_scope("read"))):
    logger.info(f"Sync full initiee par : {client['client_name']}")
    def fetch_all(collection_nom: str) -> list[dict]:
        docs = list(get_collection(collection_nom).find())
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            if doc.get("created_at"): doc["created_at"] = doc["created_at"].isoformat()
            if doc.get("updated_at"): doc["updated_at"] = doc["updated_at"].isoformat()
        return docs

    return {
        "server_time": datetime.now(timezone.utc).isoformat(),
        "data": {
            "regions": fetch_all(Collections.REGIONS), "departements": fetch_all(Collections.DEPARTEMENTS),
            "arrondissements": fetch_all(Collections.ARRONDISSEMENTS), "communes": fetch_all(Collections.COMMUNES),
            "villages": fetch_all(Collections.VILLAGES), "chefferies": fetch_all(Collections.CHEFFERIES),
            "ethnies": fetch_all(Collections.ETHNIES), "marches": fetch_all(Collections.MARCHES),
            "lieux": fetch_all(Collections.LIEUX), "cooperatives": fetch_all(Collections.COOPERATIVES),
            "exercices": fetch_all(Collections.EXERCICES),
        }
    }