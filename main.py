"""
main.py
-------
Point d'entree de l'application FastAPI.

Ce module definit toutes les routes HTTP de l'application :
- GET  /                          → sert l'interface web (index.html)
- GET  /health                    → verifie la connexion MongoDB
- GET  /stats                     → statistiques globales de la BD
- POST /import                    → recoit le CSV et lance l'import
- GET  /regions                   → liste toutes les regions
- GET  /regions/{id}              → detail d'une region + departements
- GET  /departements/{id}         → detail d'un departement + arrondissements
- GET  /arrondissements/{id}      → detail d'un arrondissement + communes
- GET  /communes                  → liste les communes avec filtres
- GET  /communes/{id}             → detail complet d'une commune
- GET  /export                    → exporte les donnees en CSV ou Excel

L'interface web (HTML/CSS/JS) est servie depuis le dossier static/.
"""

import io
import logging

import pandas as pd
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import MONGODB_DB
from database import (
    Collections,
    check_connection,
    get_collection,
    inserer_toutes_communes,
)
from parser import parser_csv


# ── Configuration du logger global ─────────────────────────────
# Tous les modules qui utilisent logging.getLogger(__name__)
# heritent de cette configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
)
logger = logging.getLogger(__name__)


# ── Initialisation de l'application FastAPI ─────────────────────
app = FastAPI(
    title="Atlas Numerique du Cameroun",
    description="API d'importation et de visualisation des donnees geographiques.",
    version="1.0.0",
)


# ── Montage des fichiers statiques ──────────────────────────────
# FastAPI sert automatiquement les fichiers du dossier static/
# index.html sera accessible sur http://localhost:8000/
app.mount("/static", StaticFiles(directory="static"), name="static")


# ════════════════════════════════════════════════════════════════
# UTILITAIRES INTERNES
# Fonctions privees utilisees par plusieurs routes.
# ════════════════════════════════════════════════════════════════

def valider_object_id(id_str: str) -> ObjectId:
    """
    Valide et convertit une chaine en ObjectId MongoDB.
    Leve une HTTPException 400 si l'ID est invalide.

    Args:
        id_str (str): Chaine representant un ObjectId MongoDB.

    Returns:
        ObjectId: L'ObjectId valide.

    Raises:
        HTTPException 400: Si la chaine n'est pas un ObjectId valide.
    """
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"ID invalide : '{id_str}'."
        )


def serialiser_doc(doc: dict) -> dict:
    """
    Convertit l'_id ObjectId d'un document MongoDB en string.
    Necessaire car ObjectId n'est pas serialisable en JSON.

    Args:
        doc (dict): Document MongoDB brut.

    Returns:
        dict: Document avec _id converti en string.
    """
    doc["_id"] = str(doc["_id"])
    return doc


def fetch_sous_docs(collection_nom: str, id_commune: str) -> list[dict]:
    """
    Recupere tous les sous-documents d'une collection
    lies a une commune via le champ id_commune.

    Args:
        collection_nom (str): Nom de la collection MongoDB.
        id_commune (str): ID de la commune parente.

    Returns:
        list[dict]: Liste des documents avec _id converti en string.
    """
    docs = list(
        get_collection(collection_nom).find({"id_commune": id_commune})
    )
    return [serialiser_doc(doc) for doc in docs]


def remonter_hierarchie(id_arrondissement: str) -> dict:
    """
    Remonte la hierarchie a partir d'un arrondissement
    pour recuperer le departement et la region parents.

    Args:
        id_arrondissement (str): ID MongoDB de l'arrondissement.

    Returns:
        dict: {arrondissement, departement, region} — None si introuvable.
    """
    arrondissement = get_collection(Collections.ARRONDISSEMENTS).find_one(
        {"_id": ObjectId(id_arrondissement)}
    )
    departement = None
    region      = None

    if arrondissement:
        arrondissement = serialiser_doc(arrondissement)
        departement = get_collection(Collections.DEPARTEMENTS).find_one(
            {"_id": ObjectId(arrondissement["id_departement"])}
        )
        if departement:
            departement = serialiser_doc(departement)
            region = get_collection(Collections.REGIONS).find_one(
                {"_id": ObjectId(departement["id_region"])}
            )
            if region:
                region = serialiser_doc(region)

    return {
        "arrondissement": arrondissement,
        "departement":    departement,
        "region":         region,
    }


# ════════════════════════════════════════════════════════════════
# ROUTES GENERALES
# ════════════════════════════════════════════════════════════════

@app.get("/", include_in_schema=False)
def servir_interface():
    """
    Sert la page principale de l'interface web.

    Returns:
        FileResponse: Le fichier index.html du dossier static/.
    """
    return FileResponse("static/index.html")


@app.get("/health")
def verifier_sante():
    """
    Verifie que l'application est en ligne et que MongoDB repond.
    Utile pour Render.com qui ping cette route pour maintenir
    le service actif.

    Returns:
        dict: Statut de l'application et de la connexion MongoDB.
    """
    mongodb_ok = check_connection()

    return {
        "statut":          "en ligne",
        "mongodb":         "connecte" if mongodb_ok else "deconnecte",
        "base_de_donnees": MONGODB_DB,
    }


@app.get("/stats")
def statistiques_globales():
    """
    Retourne le nombre de documents dans chaque collection.

    Permet de verifier apres un import que les chiffres correspondent
    au fichier CSV source — outil de validation visuelle essentiel.

    Returns:
        dict: Compteurs de documents par collection.
    """
    return {
        "regions":         get_collection(Collections.REGIONS).count_documents({}),
        "departements":    get_collection(Collections.DEPARTEMENTS).count_documents({}),
        "arrondissements": get_collection(Collections.ARRONDISSEMENTS).count_documents({}),
        "communes":        get_collection(Collections.COMMUNES).count_documents({}),
        "villages":        get_collection(Collections.VILLAGES).count_documents({}),
        "chefferies":      get_collection(Collections.CHEFFERIES).count_documents({}),
        "ethnies":         get_collection(Collections.ETHNIES).count_documents({}),
        "marches":         get_collection(Collections.MARCHES).count_documents({}),
        "lieux":           get_collection(Collections.LIEUX).count_documents({}),
        "cooperatives":    get_collection(Collections.COOPERATIVES).count_documents({}),
        "exercices":       get_collection(Collections.EXERCICES).count_documents({}),
    }


# ════════════════════════════════════════════════════════════════
# ROUTE IMPORT
# ════════════════════════════════════════════════════════════════

@app.post("/import")
async def importer_csv(fichier: UploadFile = File(...)):
    """
    Recoit un fichier CSV KoboCollect, le parse et insere
    les donnees dans MongoDB.

    Le fichier doit respecter les conventions definies dans
    le document technique (separateurs ; | :: , RAS).

    Args:
        fichier (UploadFile): Fichier CSV uploade par l'agent.

    Returns:
        dict: Rapport d'import avec nombre de succes et erreurs.

    Raises:
        HTTPException 400: Si le fichier n'est pas un CSV valide.
        HTTPException 500: Si une erreur survient pendant l'import.
    """
    # ── Validation du type de fichier ───────────────────────────
    if not fichier.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit etre au format CSV (.csv)."
        )

    logger.info(f"Fichier recu : {fichier.filename}")

    # ── Lecture du contenu en memoire ───────────────────────────
    try:
        contenu = await fichier.read()
    except Exception as erreur:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de lire le fichier : {erreur}"
        )

    # ── Parsing du CSV ───────────────────────────────────────────
    try:
        communes_parsees = parser_csv(contenu)
    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=f"Erreur de format CSV : {erreur}"
        )

    if not communes_parsees:
        raise HTTPException(
            status_code=400,
            detail="Aucune commune valide trouvee dans le fichier CSV."
        )

    # ── Insertion dans MongoDB ───────────────────────────────────
    try:
        rapport = inserer_toutes_communes(communes_parsees)
    except Exception as erreur:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'insertion en base de donnees : {erreur}"
        )

    logger.info(
        f"Import termine — "
        f"{rapport['succes']} succes / {rapport['erreurs']} erreurs."
    )

    return rapport


# ════════════════════════════════════════════════════════════════
# ROUTES HIERARCHIE
# ════════════════════════════════════════════════════════════════

@app.get("/regions")
def lister_regions():
    """
    Retourne toutes les regions enregistrees avec leur
    nombre de departements.

    Returns:
        dict: {total, regions}
    """
    regions = list(get_collection(Collections.REGIONS).find())

    for region in regions:
        id_region = str(region["_id"])
        region["_id"] = id_region
        region["nb_departements"] = get_collection(
            Collections.DEPARTEMENTS
        ).count_documents({"id_region": id_region})

    return {"total": len(regions), "regions": regions}


@app.get("/regions/{id_region}")
def detail_region(id_region: str):
    """
    Retourne une region avec tous ses departements
    et le nombre d'arrondissements par departement.

    Args:
        id_region (str): L'_id MongoDB de la region.

    Returns:
        dict: {region, departements}

    Raises:
        HTTPException 400: ID invalide.
        HTTPException 404: Region introuvable.
    """
    objet_id = valider_object_id(id_region)

    region = get_collection(Collections.REGIONS).find_one({"_id": objet_id})
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"Region introuvable pour l'ID : {id_region}."
        )
    region = serialiser_doc(region)

    departements = list(
        get_collection(Collections.DEPARTEMENTS).find({"id_region": id_region})
    )
    for d in departements:
        id_dept = str(d["_id"])
        d["_id"] = id_dept
        d["nb_arrondissements"] = get_collection(
            Collections.ARRONDISSEMENTS
        ).count_documents({"id_departement": id_dept})

    return {"region": region, "departements": departements}


@app.get("/departements/{id_departement}")
def detail_departement(id_departement: str):
    """
    Retourne un departement avec ses arrondissements
    et le nombre de communes par arrondissement.

    Args:
        id_departement (str): L'_id MongoDB du departement.

    Returns:
        dict: {departement, arrondissements}

    Raises:
        HTTPException 400: ID invalide.
        HTTPException 404: Departement introuvable.
    """
    objet_id = valider_object_id(id_departement)

    departement = get_collection(Collections.DEPARTEMENTS).find_one(
        {"_id": objet_id}
    )
    if not departement:
        raise HTTPException(
            status_code=404,
            detail=f"Departement introuvable pour l'ID : {id_departement}."
        )
    departement = serialiser_doc(departement)

    arrondissements = list(
        get_collection(Collections.ARRONDISSEMENTS).find(
            {"id_departement": id_departement}
        )
    )
    for a in arrondissements:
        id_arr = str(a["_id"])
        a["_id"] = id_arr
        a["nb_communes"] = get_collection(
            Collections.COMMUNES
        ).count_documents({"id_arrondissement": id_arr})

    return {"departement": departement, "arrondissements": arrondissements}


@app.get("/arrondissements/{id_arrondissement}")
def detail_arrondissement(id_arrondissement: str):
    """
    Retourne un arrondissement avec ses communes.

    Args:
        id_arrondissement (str): L'_id MongoDB de l'arrondissement.

    Returns:
        dict: {arrondissement, communes}

    Raises:
        HTTPException 400: ID invalide.
        HTTPException 404: Arrondissement introuvable.
    """
    objet_id = valider_object_id(id_arrondissement)

    arrondissement = get_collection(Collections.ARRONDISSEMENTS).find_one(
        {"_id": objet_id}
    )
    if not arrondissement:
        raise HTTPException(
            status_code=404,
            detail=f"Arrondissement introuvable pour l'ID : {id_arrondissement}."
        )
    arrondissement = serialiser_doc(arrondissement)

    communes = list(
        get_collection(Collections.COMMUNES).find(
            {"id_arrondissement": id_arrondissement},
            {
                "nom":                  1,
                "coordonnees":          1,
                "connectivite_constante": 1,
                "contact_mairie":       1,
                "langues_locales":      1,
            }
        )
    )
    for c in communes:
        c["_id"] = str(c["_id"])

    return {"arrondissement": arrondissement, "communes": communes}


# ════════════════════════════════════════════════════════════════
# ROUTES COMMUNES
# ════════════════════════════════════════════════════════════════

@app.get("/communes")
def lister_communes(
    region: str = Query(default=None, description="Filtrer par nom de region"),
    departement: str = Query(default=None, description="Filtrer par nom de departement"),
):
    """
    Retourne la liste des communes avec leurs informations principales.
    Permet de filtrer par region et/ou departement.

    La recherche est insensible a la casse.

    Args:
        region (str | None): Nom de la region pour filtrer.
        departement (str | None): Nom du departement pour filtrer.

    Returns:
        dict: {total, communes}
    """
    ids_arrondissements_valides = None

    if region or departement:

        # Etape 1 — Regions
        filtre_region = {}
        if region:
            filtre_region["nom"] = {"$regex": region, "$options": "i"}

        ids_regions = [
            str(r["_id"])
            for r in get_collection(Collections.REGIONS).find(
                filtre_region, {"_id": 1}
            )
        ]
        if not ids_regions:
            return {"total": 0, "communes": []}

        # Etape 2 — Departements
        filtre_dept = {"id_region": {"$in": ids_regions}}
        if departement:
            filtre_dept["nom"] = {"$regex": departement, "$options": "i"}

        ids_departements = [
            str(d["_id"])
            for d in get_collection(Collections.DEPARTEMENTS).find(
                filtre_dept, {"_id": 1}
            )
        ]
        if not ids_departements:
            return {"total": 0, "communes": []}

        # Etape 3 — Arrondissements
        ids_arrondissements_valides = [
            str(a["_id"])
            for a in get_collection(Collections.ARRONDISSEMENTS).find(
                {"id_departement": {"$in": ids_departements}}, {"_id": 1}
            )
        ]
        if not ids_arrondissements_valides:
            return {"total": 0, "communes": []}

    # ── Requete finale sur les communes ─────────────────────────
    filtre_commune = {}
    if ids_arrondissements_valides:
        filtre_commune["id_arrondissement"] = {
            "$in": ids_arrondissements_valides
        }

    communes = list(
        get_collection(Collections.COMMUNES).find(
            filtre_commune,
            {
                "nom":                    1,
                "id_arrondissement":      1,
                "coordonnees":            1,
                "connectivite_constante": 1,
                "langues_locales":        1,
                "contact_mairie":         1,
            }
        )
    )

    # On enrichit chaque commune avec sa hierarchie complete
    # pour permettre l'affichage region/departement/arrondissement
    # directement dans le tableau de bord sans appel supplementaire
    resultats = []
    for commune in communes:
        commune = serialiser_doc(commune)
        hierarchie = remonter_hierarchie(commune["id_arrondissement"])
        resultats.append({
            "commune":   commune,
            "region":    hierarchie["region"]["nom"] if hierarchie["region"] else None,
            "departement": hierarchie["departement"]["nom"] if hierarchie["departement"] else None,
            "arrondissement": hierarchie["arrondissement"]["nom"] if hierarchie["arrondissement"] else None,
        })

    return {"total": len(resultats), "communes": resultats}


@app.get("/communes/{id_commune}")
def detail_commune(id_commune: str):
    """
    Retourne les informations completes d'une commune
    avec tous ses sous-documents et sa hierarchie complete.

    Args:
        id_commune (str): L'_id MongoDB de la commune.

    Returns:
        dict: Commune complete avec hierarchie et tous ses sous-documents.

    Raises:
        HTTPException 400: ID invalide.
        HTTPException 404: Commune introuvable.
    """
    objet_id = valider_object_id(id_commune)

    commune = get_collection(Collections.COMMUNES).find_one({"_id": objet_id})
    if not commune:
        raise HTTPException(
            status_code=404,
            detail=f"Commune introuvable pour l'ID : {id_commune}."
        )
    commune = serialiser_doc(commune)

    # Hierarchie complete remontee depuis l'arrondissement
    hierarchie = remonter_hierarchie(commune["id_arrondissement"])

    return {
        "commune":      commune,
        "hierarchie":   hierarchie,
        "villages":     fetch_sous_docs(Collections.VILLAGES,     id_commune),
        "chefferies":   fetch_sous_docs(Collections.CHEFFERIES,   id_commune),
        "ethnies":      fetch_sous_docs(Collections.ETHNIES,       id_commune),
        "marches":      fetch_sous_docs(Collections.MARCHES,       id_commune),
        "lieux":        fetch_sous_docs(Collections.LIEUX,         id_commune),
        "cooperatives": fetch_sous_docs(Collections.COOPERATIVES,  id_commune),
        "exercices":    fetch_sous_docs(Collections.EXERCICES,     id_commune),
    }

# ════════════════════════════════════════════════════════════════
# ROUTES SOUS-DOCUMENTS
# Permettent de visualiser chaque collection independamment
# avec filtres par commune et/ou type.
# ════════════════════════════════════════════════════════════════

@app.get("/villages")
def lister_villages(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
):
    """
    Retourne tous les villages et quartiers.
    Filtre optionnel par commune.

    Args:
        id_commune (str | None): ID MongoDB de la commune.

    Returns:
        dict: {total, villages}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune

    villages = list(get_collection(Collections.VILLAGES).find(filtre))
    for v in villages:
        v["_id"] = str(v["_id"])

    return {"total": len(villages), "villages": villages}


@app.get("/chefferies")
def lister_chefferies(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
):
    """
    Retourne toutes les chefferies.
    Filtre optionnel par commune.

    Args:
        id_commune (str | None): ID MongoDB de la commune.

    Returns:
        dict: {total, chefferies}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune

    chefferies = list(get_collection(Collections.CHEFFERIES).find(filtre))
    for c in chefferies:
        c["_id"] = str(c["_id"])

    return {"total": len(chefferies), "chefferies": chefferies}


@app.get("/ethnies")
def lister_ethnies(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
):
    """
    Retourne toutes les ethnies.
    Filtre optionnel par commune.

    Args:
        id_commune (str | None): ID MongoDB de la commune.

    Returns:
        dict: {total, ethnies}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune

    ethnies = list(get_collection(Collections.ETHNIES).find(filtre))
    for e in ethnies:
        e["_id"] = str(e["_id"])

    return {"total": len(ethnies), "ethnies": ethnies}


@app.get("/marches")
def lister_marches(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
):
    """
    Retourne tous les marches.
    Filtre optionnel par commune.

    Args:
        id_commune (str | None): ID MongoDB de la commune.

    Returns:
        dict: {total, marches}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune

    marches = list(get_collection(Collections.MARCHES).find(filtre))
    for m in marches:
        m["_id"] = str(m["_id"])

    return {"total": len(marches), "marches": marches}


@app.get("/lieux/types")
def lister_types_lieux():
    """
    Retourne la liste des types de lieux disponibles
    dans la base de donnees avec leur nombre de lieux.

    Returns:
        dict: {types} — liste des types avec compteurs.
    """
    # On utilise une agregation MongoDB pour grouper par type
    pipeline = [
        {"$group": {"_id": "$type_nom", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    resultats = list(get_collection(Collections.LIEUX).aggregate(pipeline))

    return {
        "types": [
            {"type": r["_id"], "count": r["count"]}
            for r in resultats
            if r["_id"]
        ]
    }


@app.get("/lieux")
def lister_lieux(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
    type_lieu: str  = Query(default=None, description="Filtrer par type de lieu"),
):
    """
    Retourne tous les lieux avec filtres optionnels.

    Args:
        id_commune (str | None): ID MongoDB de la commune.
        type_lieu (str | None): Type de lieu (scolaire, urgence, etc.).

    Returns:
        dict: {total, lieux}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune
    if type_lieu:
        filtre["type_nom"] = {"$regex": type_lieu, "$options": "i"}

    lieux = list(get_collection(Collections.LIEUX).find(filtre))
    for l in lieux:
        l["_id"] = str(l["_id"])

    return {"total": len(lieux), "lieux": lieux}


@app.get("/cooperatives")
def lister_cooperatives(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
):
    """
    Retourne toutes les cooperatives et GIC.
    Filtre optionnel par commune.

    Args:
        id_commune (str | None): ID MongoDB de la commune.

    Returns:
        dict: {total, cooperatives}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune

    cooperatives = list(get_collection(Collections.COOPERATIVES).find(filtre))
    for c in cooperatives:
        c["_id"] = str(c["_id"])

    return {"total": len(cooperatives), "cooperatives": cooperatives}


@app.get("/exercices")
def lister_exercices(
    id_commune: str = Query(default=None, description="Filtrer par ID commune"),
):
    """
    Retourne tous les exercices annuels.
    Filtre optionnel par commune.

    Args:
        id_commune (str | None): ID MongoDB de la commune.

    Returns:
        dict: {total, exercices}
    """
    filtre = {}
    if id_commune:
        filtre["id_commune"] = id_commune

    exercices = list(get_collection(Collections.EXERCICES).find(filtre))
    for e in exercices:
        e["_id"] = str(e["_id"])

    return {"total": len(exercices), "exercices": exercices}
# ════════════════════════════════════════════════════════════════
# ROUTE EXPORT
# ════════════════════════════════════════════════════════════════

@app.get("/export")
def exporter_donnees(
    format: str = Query(
        default="csv",
        description="Format d'export : 'csv' ou 'excel'"
    ),
    region: str = Query(default=None, description="Filtrer par region"),
):
    """
    Exporte les donnees des communes en CSV ou Excel.
    Chaque ligne correspond a une commune avec ses infos principales
    et sa hierarchie (region, departement, arrondissement).

    Args:
        format (str): Format souhaite — 'csv' ou 'excel'.
        region (str | None): Filtrer par nom de region.

    Returns:
        StreamingResponse: Fichier a telecharger.

    Raises:
        HTTPException 400: Format invalide.
        HTTPException 404: Aucune commune trouvee.
    """
    if format not in ("csv", "excel"):
        raise HTTPException(
            status_code=400,
            detail="Format invalide. Utilisez 'csv' ou 'excel'."
        )

    resultats  = lister_communes(region=region)
    communes   = resultats["communes"]

    if not communes:
        raise HTTPException(
            status_code=404,
            detail="Aucune commune trouvee pour cet export."
        )

    # ── Construction du DataFrame ────────────────────────────────
    # On aplatit les champs imbriques pour le CSV/Excel
    lignes = []
    for item in communes:
        c       = item["commune"]
        contact = c.get("contact_mairie", {})
        coords  = c.get("coordonnees", {})

        lignes.append({
            "ID":              c.get("_id"),
            "Region":          item.get("region"),
            "Departement":     item.get("departement"),
            "Arrondissement":  item.get("arrondissement"),
            "Commune":         c.get("nom"),
            "Telephone":       ", ".join(contact.get("telephones", [])),
            "Mail":            ", ".join(contact.get("mails", [])),
            "Code postal":     contact.get("code_postal"),
            "Latitude":        coords.get("latitude"),
            "Longitude":       coords.get("longitude"),
            "Connectivite":    "Oui" if c.get("connectivite_constante") else "Non",
            "Langues locales": " | ".join(c.get("langues_locales", [])),
        })

    df     = pd.DataFrame(lignes)
    buffer = io.BytesIO()

    if format == "csv":
        df.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; filename=communes_export.csv"
            }
        )

    else:  # excel
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                    "attachment; filename=communes_export.xlsx"
            }
        )