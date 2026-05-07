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

# ════════════════════════════════════════════════════════════════
# FONCTIONS D'INSERTION ET DE RECHERCHE
# Ces fonctions gerent la logique d'ecriture dans MongoDB.
# Elles sont appelees par main.py apres le parsing du CSV.
# ════════════════════════════════════════════════════════════════

from bson import ObjectId


def trouver_ou_creer(
    collection_nom: str,
    filtre: dict,
    document: dict
) -> str:
    """
    Cherche un document dans une collection selon un filtre.
    Si trouve, retourne son _id.
    Si non trouve, l'insere et retourne le nouvel _id.

    C'est la fonction centrale de la validation hierarchique :
    elle garantit qu'on ne cree pas de doublons pour les regions,
    departements et arrondissements.

    Args:
        collection_nom (str): Nom de la collection MongoDB.
        filtre (dict): Criteres de recherche (ex: {"nom": "Adamaoua"}).
        document (dict): Document a inserer si non trouve.

    Returns:
        str: Identifiant MongoDB (_id) du document trouve ou cree.
    """
    collection = get_collection(collection_nom)

    # On cherche d'abord si le document existe deja
    existant = collection.find_one(filtre)

    if existant:
        logger.info(
            f"[{collection_nom}] Document existant trouve : {filtre}"
        )
        # On retourne l'_id sous forme de string pour faciliter
        # son utilisation comme reference dans d'autres documents
        return str(existant["_id"])

    # Document absent — on l'insere
    resultat = collection.insert_one(document)
    logger.info(
        f"[{collection_nom}] Nouveau document insere : {filtre}"
    )
    return str(resultat.inserted_id)


def commune_existe(
    nom: str,
    id_arrondissement: str
) -> str | None:
    """
    Verifie si une commune existe deja dans la base de donnees
    en comparant son nom ET son arrondissement parent.

    La combinaison nom + id_arrondissement est la cle d'unicite
    d'une commune — deux communes peuvent avoir le meme nom
    dans des arrondissements differents.

    Args:
        nom (str): Nom de la commune.
        id_arrondissement (str): ID MongoDB de l'arrondissement parent.

    Returns:
        str | None: L'_id de la commune si elle existe, None sinon.
    """
    collection = get_collection(Collections.COMMUNES)

    existante = collection.find_one({
        "nom": nom,
        "id_arrondissement": id_arrondissement,
    })

    if existante:
        return str(existante["_id"])

    return None


def inserer_sous_documents(
    collection_nom: str,
    documents: list[dict],
    id_commune: str
) -> int:
    """
    Insere une liste de sous-documents dans une collection
    en remplacant le placeholder PENDING par le vrai id_commune.

    Args:
        collection_nom (str): Nom de la collection cible.
        documents (list[dict]): Liste de documents a inserer.
        id_commune (str): Vrai ID MongoDB de la commune parente.

    Returns:
        int: Nombre de documents inseres.
    """
    if not documents:
        return 0

    collection = get_collection(collection_nom)

    # On remplace "PENDING" par le vrai id_commune dans chaque document
    for doc in documents:
        doc["id_commune"] = id_commune

    resultat = collection.insert_many(documents)
    logger.info(
        f"[{collection_nom}] {len(resultat.inserted_ids)} document(s) insere(s)."
    )
    return len(resultat.inserted_ids)


def inserer_commune_complete(commune_parsee: dict) -> dict:
    """
    Insere une commune complete dans MongoDB en respectant
    la hierarchie et en evitant les doublons.

    Ordre d'insertion :
    1. Region        (trouve ou cree)
    2. Departement   (trouve ou cree)
    3. Arrondissement (trouve ou cree)
    4. Commune       (trouve ou cree)
    5. Sous-documents (villages, chefferies, ethnies, etc.)

    Args:
        commune_parsee (dict): Structure retournee par parser_csv().

    Returns:
        dict: Rapport d'insertion {statut, commune, details}.
    """
    from models import (
        make_region, make_departement,
        make_arrondissement, make_commune
    )

    hierarchie = commune_parsee["hierarchie"]
    commune    = commune_parsee["commune"]

    # ── Etape 1 : Region ────────────────────────────────────────
    id_region = trouver_ou_creer(
        collection_nom=Collections.REGIONS,
        filtre={"nom": hierarchie["region"]},
        document=make_region(hierarchie["region"])
    )

    # ── Etape 2 : Departement ───────────────────────────────────
    id_departement = trouver_ou_creer(
        collection_nom=Collections.DEPARTEMENTS,
        filtre={
            "nom": hierarchie["departement"],
            "id_region": id_region,
        },
        document=make_departement(hierarchie["departement"], id_region)
    )

    # ── Etape 3 : Arrondissement ─────────────────────────────────
    id_arrondissement = trouver_ou_creer(
        collection_nom=Collections.ARRONDISSEMENTS,
        filtre={
            "nom": hierarchie["arrondissement"],
            "id_departement": id_departement,
        },
        document=make_arrondissement(hierarchie["arrondissement"], id_departement)
    )

    # ── Etape 4 : Commune ────────────────────────────────────────
    # On verifie d'abord si la commune existe deja
    id_commune_existante = commune_existe(
        nom=commune["nom"],
        id_arrondissement=id_arrondissement
    )

    if id_commune_existante:
        # La commune existe — on ajoute uniquement les sous-documents
        # sans ecraser les donnees existantes
        logger.info(
            f"Commune '{commune['nom']}' deja existante — "
            f"ajout des sous-documents uniquement."
        )
        id_commune = id_commune_existante
        statut = "existante"

    else:
        # Nouvelle commune — on l'insere
        doc_commune = make_commune(
            nom=commune["nom"],
            id_arrondissement=id_arrondissement,
            contact_mairie=commune["contact_mairie"],
            contact_personne_ressource=commune["contact_personne_ressource"],
            coordonnees=commune["coordonnees"],
            langues_locales=commune["langues_locales"],
            delegations_ministeres=commune["delegations_ministeres"],
            agriculture_artisanat=commune["agriculture_artisanat"],
            image_url=commune["image_url"],
            gare_voyageurs=commune["gare_voyageurs"],
            connectivite_constante=commune["connectivite_constante"],
            villages_non_connectes=commune["villages_non_connectes"],
            lien_etranger=commune["lien_etranger"],
            pays_etrangers=commune["pays_etrangers"],
            autres_informations=commune["autres_informations"],
            kobocollect_uuid=commune["kobocollect_uuid"],
            submitted_by=commune["submitted_by"],
            submission_time=commune["submission_time"],
        )
        # On ajoute id_arrondissement au document commune
        doc_commune["id_arrondissement"] = id_arrondissement

        resultat = get_collection(Collections.COMMUNES).insert_one(doc_commune)
        id_commune = str(resultat.inserted_id)
        statut = "nouvelle"
        logger.info(f"Commune '{commune['nom']}' inseree avec _id : {id_commune}")

    # ── Etape 5 : Sous-documents ─────────────────────────────────
    # On insere chaque collection de sous-documents
    nb_villages     = inserer_sous_documents(Collections.VILLAGES,     commune_parsee["villages"],     id_commune)
    nb_chefferies   = inserer_sous_documents(Collections.CHEFFERIES,   commune_parsee["chefferies"],   id_commune)
    nb_ethnies      = inserer_sous_documents(Collections.ETHNIES,       commune_parsee["ethnies"],       id_commune)
    nb_marches      = inserer_sous_documents(Collections.MARCHES,       commune_parsee["marches"],       id_commune)
    nb_lieux        = inserer_sous_documents(Collections.LIEUX,         commune_parsee["lieux"],         id_commune)
    nb_cooperatives = inserer_sous_documents(Collections.COOPERATIVES,  commune_parsee["cooperatives"],  id_commune)

    # L'exercice est un seul document — on le traite separement
    exercice = commune_parsee["exercice"]
    exercice["id_commune"] = id_commune
    get_collection(Collections.EXERCICES).insert_one(exercice)

    # ── Rapport d'insertion ──────────────────────────────────────
    return {
        "statut": statut,
        "commune": commune["nom"],
        "id_commune": id_commune,
        "sous_documents": {
            "villages":     nb_villages,
            "chefferies":   nb_chefferies,
            "ethnies":      nb_ethnies,
            "marches":      nb_marches,
            "lieux":        nb_lieux,
            "cooperatives": nb_cooperatives,
        }
    }


def inserer_toutes_communes(communes_parsees: list[dict]) -> dict:
    """
    Insere toutes les communes parsees dans MongoDB.
    Retourne un rapport global de l'import.

    Args:
        communes_parsees (list[dict]): Liste retournee par parser_csv().

    Returns:
        dict: Rapport global {total, succes, erreurs, details}.
    """
    rapport = {
        "total":   len(communes_parsees),
        "succes":  0,
        "erreurs": 0,
        "details": []
    }

    for commune_parsee in communes_parsees:
        try:
            resultat = inserer_commune_complete(commune_parsee)
            rapport["succes"] += 1
            rapport["details"].append(resultat)

        except Exception as erreur:
            rapport["erreurs"] += 1
            rapport["details"].append({
                "statut": "erreur",
                "commune": commune_parsee.get("commune", {}).get("nom", "inconnu"),
                "message": str(erreur)
            })
            logger.error(
                f"Erreur lors de l'insertion de la commune "
                f"'{commune_parsee.get('commune', {}).get('nom')}' : {erreur}"
            )

    logger.info(
        f"Import termine — "
        f"{rapport['succes']} succes / {rapport['erreurs']} erreurs."
    )
    return rapport