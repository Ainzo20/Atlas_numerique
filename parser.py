"""
parser.py
---------
Lecture, nettoyage et transformation du fichier CSV KoboCollect.

Ce module est le coeur du projet. Il prend en entree un fichier CSV
brut exporte depuis KoboCollect et retourne une liste de dictionnaires
structures, prets a etre inseres dans MongoDB via database.py.

Conventions du CSV traitees ici :
- Separateur de colonnes      : ;
- Separateur d'entites        : |
- Separateur d'attributs      : ::
- Valeurs multiples           : ,
- Valeur manquante            : RAS  → convertie en None
- Prefixe village/quartier    : V:: ou Q::
"""

import logging
import pandas as pd
from io import BytesIO

from models import (
    make_chefferie, make_cooperative, make_ethnie,
    make_exercice, make_jour_marche, make_lieu,
    make_village_quartier,
)

# ── Logger de ce module ─────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constantes ──────────────────────────────────────────────────
SEP_ENTITES    = "|"
SEP_ATTRIBUTS  = "::"
SEP_VALEURS    = ","
VALEUR_ABSENTE = "RAS"

# ── Mapping : nom interne → nom exact dans le CSV (ancien ou nouveau) ──
# Permet la compatibilité ascendante : si le nouveau nom n'existe pas,
# on fallback vers l'ancien nom défini ici.
# ── Mapping : nom interne → nom EXACT dans le CSV (avec accents) ──
COLONNES = {
    # Hiérarchie
    "region":         "Région",
    "departement":    "Département",
    "arrondissement": "Arrondissement",

    # Contacts
    "contact_mairie": "Contact de la mairie",
    "contact_ressource": "Contact de la personne ressource",

    # GPS Commune
    "gps_commune-Latitude":  "_Coordonnées GPS de la commune_latitude",
    "gps_commune-Longitude": "_Coordonnées GPS de la commune_longitude",
    "gps_commune-Altitude":  "_Coordonnées GPS de la commune_altitude",
    "gps_commune-Accuracy":  "_Coordonnées GPS de la commune_precision",

    # Entités principales
    "villages_quartiers": "Villages et quartiers",
    "chefferies":         "Chefferies de la commune",
    "zone_electrifiee":   "La zone est-elle entièrement électrifiée ?",
    "villages_non_electrifies": "Lister les villages/quartiers électrifiés",
    "ethnies":            "Ethnies présentes dans la commune",
    "langues_locales":    "Langues locales parlées",
    "marches":            "Marchés et jours de marché",
    "ecoles":             "Écoles et leurs types",
    "urgences":           "Services d'urgence et de sécurité",
    "sites_touristiques": "Sites touristiques et culturels",
    "points_religieux":   "Lieux de culte et points religieux",
    "points_eau":         "Points d'eau",
    "infra_sportives":    "Infrastructures sportives",
    "points_reference":   "Points de référence (bars, hôtels, restaurants...)",
    "connectivite":       "La connexion internet est-elle constante ?",
    "villages_non_connectes": "Villages/quartiers avec connexion internet",
    "lien_etranger":      "La commune est-elle liée à des pays étrangers ?",
    "pays_etrangers":     "Pays étrangers concernés",
    "nb_habitants":       "Nombre d'habitants de la commune",
    "delegations_ministeres": "Délégations des ministères sectoriels",
    "agriculture_artisanat": "Activités agricoles et artisanales",
    "besoins_technologiques": "Besoins technologiques de la commune",
    "gare_voyageurs":     "Gare(s) voyageurs",
    "cooperatives":       "Coopératives, GIC et associations",
    "image_carte":        "Photo de la carte de la commune_URL",
    "autres_infos":       "Autres informations pertinentes",

    # Métadonnées KoboCollect
    "kobocollect_uuid":   "_uuid",
    "submitted_by":       "_submitted_by",
    "submission_time":    "_submission_time",
}

# Types de lieux reconnus (nom interne → type dans MongoDB)
TYPES_LIEUX = {
    "points_religieux":    "religieux",
    "points_reference":    "reference",
    "sites_touristiques":  "touristique",
    "ecoles":              "scolaire",
    "urgences":            "urgence",
    "points_eau":          "eau",
    "infra_sportives":     "sportif",
}


# ════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ════════════════════════════════════════════════════════════════

def nettoyer_valeur(valeur: str) -> str | None:
    """
    Nettoie une valeur brute issue du CSV.
    - Supprime les espaces en debut et fin
    - Convertit RAS en None

    Args:
        valeur (str): Valeur brute du CSV.

    Returns:
        str | None: Valeur nettoyee, ou None si absente.
    """
    if not isinstance(valeur, str):
        return None
    valeur = valeur.strip()
    if valeur.upper() == VALEUR_ABSENTE or valeur == "":
        return None
    return valeur


def eclater_entites(cellule: str) -> list[str]:
    """
    Eclate une cellule contenant plusieurs entites separees par |.
    Filtre les entites vides ou RAS.

    Args:
        cellule (str): Contenu brut de la cellule CSV.

    Returns:
        list[str]: Liste des entites valides.
    """
    if not nettoyer_valeur(cellule):
        return []
    entites = [e.strip() for e in cellule.split(SEP_ENTITES)]
    return [e for e in entites if nettoyer_valeur(e)]


def eclater_attributs(entite: str) -> list[str | None]:
    """
    Eclate une entite en ses attributs separes par ::.
    Chaque attribut est nettoye (RAS → None).

    Args:
        entite (str): Entite brute avec attributs.

    Returns:
        list[str | None]: Liste des attributs nettoyes.
    """
    attributs = entite.split(SEP_ATTRIBUTS)
    return [nettoyer_valeur(a) for a in attributs]


def eclater_valeurs_multiples(valeur: str) -> list[str]:
    """
    Eclate un attribut contenant plusieurs valeurs separees par virgule.

    Args:
        valeur (str): Valeur brute avec plusieurs entrees.

    Returns:
        list[str]: Liste des valeurs valides.
    """
    if not nettoyer_valeur(valeur):
        return []
    valeurs = [v.strip() for v in valeur.split(SEP_VALEURS)]
    return [v for v in valeurs if nettoyer_valeur(v)]


def convertir_float(valeur: str | None) -> float | None:
    """
    Convertit une chaine de caracteres en float.

    Args:
        valeur (str | None): Valeur a convertir.

    Returns:
        float | None: Valeur convertie ou None.
    """
    if not valeur:
        return None
    try:
        return float(valeur)
    except ValueError:
        logger.warning(f"Impossible de convertir '{valeur}' en float.")
        return None


def convertir_bool(valeur: str | None) -> bool:
    """
    Convertit une reponse Oui/Non du CSV en booleen Python.

    Args:
        valeur (str | None): "Oui" ou "Non" issu du CSV.

    Returns:
        bool: True si "Oui", False sinon.
    """
    if not valeur:
        return False
    return valeur.strip().lower() == "oui"


def lire_cellule(ligne: pd.Series, nom_interne: str) -> str:
    """
    Lit une cellule en essayant d'abord le nom interne (nouveau format KoboCollect),
    puis fallback vers l'ancien nom via le dictionnaire COLONNES.

    Args:
        ligne (pd.Series): Ligne du DataFrame.
        nom_interne (str): Nom interne clean (ex: "region", "contact_mairie").

    Returns:
        str: Valeur nettoyée ou chaîne vide.
    """
    # 1. Essai avec le nom interne (nouveau format KoboCollect)
    valeur = ligne.get(nom_interne)

    # 2. Fallback vers l'ancien nom si présent dans le mapping
    if pd.isna(valeur) or (isinstance(valeur, str) and valeur.strip() == ""):
        ancien_nom = COLONNES.get(nom_interne)
        if ancien_nom:
            valeur = ligne.get(ancien_nom)

    # 3. Nettoyage standard
    if pd.isna(valeur):
        return ""
    return str(valeur).strip()


# ════════════════════════════════════════════════════════════════
# FONCTIONS DE PARSING PAR TYPE DE CHAMP
# ════════════════════════════════════════════════════════════════

def parser_contact(cellule: str) -> dict:
    """
    Parse un champ contact au format : telephone|mail|code_postal

    Args:
        cellule (str): Contenu brut du champ contact.

    Returns:
        dict: Contact structure avec telephones, mails et code_postal.
    """
    parties = cellule.split(SEP_ENTITES)
    while len(parties) < 3:
        parties.append(VALEUR_ABSENTE)

    return {
        "telephones": eclater_valeurs_multiples(parties[0]),
        "mails": eclater_valeurs_multiples(parties[1]),
        "code_postal": nettoyer_valeur(parties[2]),
    }


def parser_contact_ressource(cellule: str) -> dict:
    """
    Parse le champ contact de la personne ressource.
    Format : nom::role::telephone::mail::code_postal

    Args:
        cellule (str): Contenu brut du champ personne ressource.

    Returns:
        dict: Personne ressource structuree.
    """
    parties = cellule.split(SEP_ATTRIBUTS)
    while len(parties) < 5:
        parties.append(VALEUR_ABSENTE)

    return {
        "nom": nettoyer_valeur(parties[0]),
        "role": nettoyer_valeur(parties[1]),
        "telephones": eclater_valeurs_multiples(parties[2]),
        "mails": eclater_valeurs_multiples(parties[3]),
        "code_postal": nettoyer_valeur(parties[4]),
    }


def parser_villages_quartiers(cellule: str, id_commune: str) -> list[dict]:
    """
    Parse le champ villages/quartiers. Prefixe V:: ou Q::.

    Args:
        cellule (str): Contenu brut du champ.
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents villages/quartiers.
    """
    resultats = []
    for entite in eclater_entites(cellule):
        if entite.upper().startswith("V::"):
            type_localite, nom = "village", entite[3:].strip()
        elif entite.upper().startswith("Q::"):
            type_localite, nom = "quartier", entite[3:].strip()
        else:
            logger.warning(f"Village/quartier sans prefixe ignore : '{entite}'")
            continue
        if nom:
            # Signature: make_village_quartier(nom, type_localite, id_commune)
            resultats.append(make_village_quartier(nom, type_localite, id_commune))
    return resultats


def parser_chefferies(cellule: str, id_commune: str) -> list[dict]:
    """
    Parse le champ chefferies. Format : nom::lat::lng::altitude::precision

    Args:
        cellule (str): Contenu brut du champ chefferies.
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents chefferies.
    """
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 5:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            # Signature: make_chefferie(nom, lat, lng, alt, prec, id_commune)
            resultats.append(make_chefferie(
                nom,
                convertir_float(attributs[1]),
                convertir_float(attributs[2]),
                convertir_float(attributs[3]),
                convertir_float(attributs[4]),
                id_commune
            ))
    return resultats


def parser_lieux(cellule: str, type_lieu: str, id_commune: str) -> list[dict]:
    """
    Parse un champ de lieux. Format : nom::latitude::longitude

    Args:
        cellule (str): Contenu brut du champ.
        type_lieu (str): Type du lieu.
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents lieux.
    """
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 3:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            # Signature: make_lieu(nom, type_nom, lat, lng, id_commune)
            resultats.append(make_lieu(
                nom,
                type_lieu,
                convertir_float(attributs[1]),
                convertir_float(attributs[2]),
                id_commune
            ))
    return resultats


def parser_marches(cellule: str, id_commune: str) -> list[dict]:
    """
    Parse le champ marches. Format : nom::jour::heure_debut::heure_fin

    Args:
        cellule (str): Contenu brut du champ marches.
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents jours_marche.
    """
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 4:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            # Signature: make_jour_marche(nom, jour, deb, fin, id_commune)
            resultats.append(make_jour_marche(
                nom,
                attributs[1],
                attributs[2],
                attributs[3],
                id_commune
            ))
    return resultats


def parser_liste_simple(cellule: str) -> list[str]:
    """
    Parse un champ contenant une liste simple d'entites separees par |.

    Args:
        cellule (str): Contenu brut du champ.

    Returns:
        list[str]: Liste de valeurs nettoyees.
    """
    return eclater_entites(cellule)


def parser_gare(cellule: str) -> list[dict]:
    """
    Parse le champ gare voyageurs. Format : nom::lat::lng

    Args:
        cellule (str): Contenu brut du champ gare.

    Returns:
        list[dict]: Liste de gares avec nom et coordonnees.
    """
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 3:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            resultats.append({
                "nom": nom,
                "latitude": convertir_float(attributs[1]),
                "longitude": convertir_float(attributs[2]),
            })
    return resultats


def parser_coordonnees_commune(ligne: pd.Series) -> dict:
    """
    Lit et structure les coordonnees GPS de la commune.

    Args:
        ligne (pd.Series): Ligne du DataFrame.

    Returns:
        dict: Coordonnees GPS {latitude, longitude, altitude, precision}.
    """
    return {
        "latitude": convertir_float(lire_cellule(ligne, "gps_commune-Latitude")),
        "longitude": convertir_float(lire_cellule(ligne, "gps_commune-Longitude")),
        "altitude": convertir_float(lire_cellule(ligne, "gps_commune-Altitude")),
        "precision": convertir_float(lire_cellule(ligne, "gps_commune-Accuracy")),
    }


# ════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════════════════════════

def parser_csv(contenu_fichier: bytes) -> list[dict]:
    """
    Fonction principale du module.
    Lit un fichier CSV KoboCollect et retourne une liste de communes
    structurees avec toutes leurs donnees associees.

    Args:
        contenu_fichier (bytes): Contenu brut du fichier CSV uploade.

    Returns:
        list[dict]: Liste de communes structurees pretes pour l'insertion.

    Raises:
        ValueError: Si le fichier CSV est vide ou mal forme.
    """
    logger.info("Debut du parsing du fichier CSV...")

    try:
        df = pd.read_csv(
            BytesIO(contenu_fichier),
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
    except Exception as erreur:
        raise ValueError(f"Impossible de lire le fichier CSV : {erreur}")

    if df.empty:
        raise ValueError("Le fichier CSV est vide.")

    logger.info(f"{len(df)} ligne(s) trouvee(s) dans le CSV.")

    communes_parsees = []

    for index, ligne in df.iterrows():
        numero_ligne = index + 2
        try:
            commune_parsee = _parser_ligne(ligne, numero_ligne)
            communes_parsees.append(commune_parsee)
            logger.info(f"Ligne {numero_ligne} — Commune '{commune_parsee['commune']['nom']}' parsee.")
        except Exception as erreur:
            logger.error(f"Ligne {numero_ligne} ignoree a cause d'une erreur : {erreur}")
            continue

    logger.info(f"Parsing termine. {len(communes_parsees)}/{len(df)} communes parsees avec succes.")
    return communes_parsees


def _parser_ligne(ligne: pd.Series, numero_ligne: int) -> dict:
    """
    Parse une seule ligne du CSV et retourne un dictionnaire structure.

    Args:
        ligne (pd.Series): Ligne du DataFrame a parser.
        numero_ligne (int): Numero de la ligne (pour les logs).

    Returns:
        dict: Structure complete de la commune avec ses sous-documents.

    Raises:
        ValueError: Si les champs obligatoires sont manquants.
    """
    # ── Champs obligatoires ─────────────────────────────────────
    region_nom         = lire_cellule(ligne, "region")
    departement_nom    = lire_cellule(ligne, "departement")
    arrondissement_nom = lire_cellule(ligne, "arrondissement")

    if not region_nom or not departement_nom or not arrondissement_nom:
        raise ValueError(f"Champs hierarchiques manquants (Region / Departement / Arrondissement).")

    # ── Nom de la commune ───────────────────────────────────────
    commune_nom = arrondissement_nom

    # ── Contacts ────────────────────────────────────────────────
    contact_mairie = parser_contact(lire_cellule(ligne, "contact_mairie"))
    contact_ressource = parser_contact_ressource(lire_cellule(ligne, "contact_ressource"))

    # ── Coordonnees GPS de la commune ───────────────────────────
    coordonnees = parser_coordonnees_commune(ligne)

    # ── Champs simples de la commune ────────────────────────────
    langues         = parser_liste_simple(lire_cellule(ligne, "langues_locales"))
    delegations     = parser_liste_simple(lire_cellule(ligne, "delegations_ministeres"))
    agriculture     = parser_liste_simple(lire_cellule(ligne, "agriculture_artisanat"))
    image_url       = nettoyer_valeur(lire_cellule(ligne, "image_carte"))
    autres_infos    = nettoyer_valeur(lire_cellule(ligne, "autres_infos"))
    connectivite    = convertir_bool(lire_cellule(ligne, "connectivite"))
    lien_etranger   = convertir_bool(lire_cellule(ligne, "lien_etranger"))
    pays_etrangers  = parser_liste_simple(lire_cellule(ligne, "pays_etrangers"))
    non_connectes   = parser_liste_simple(lire_cellule(ligne, "villages_non_connectes"))

    # ── Gare voyageurs ──────────────────────────────────────────
    gares = parser_gare(lire_cellule(ligne, "gare_voyageurs"))

    # ── Tracabilite KoboCollect ─────────────────────────────────
    uuid            = nettoyer_valeur(lire_cellule(ligne, "kobocollect_uuid"))
    submitted_by    = nettoyer_valeur(lire_cellule(ligne, "submitted_by"))
    submission_time = nettoyer_valeur(lire_cellule(ligne, "submission_time"))

    # ── Sous-documents ──────────────────────────────────────────
    ID_PENDING = "PENDING"

    villages = parser_villages_quartiers(lire_cellule(ligne, "villages_quartiers"), ID_PENDING)
    chefferies = parser_chefferies(lire_cellule(ligne, "chefferies"), ID_PENDING)

    ethnies = [
        make_ethnie(nom, ID_PENDING)
        for nom in parser_liste_simple(lire_cellule(ligne, "ethnies"))
    ]

    marches = parser_marches(lire_cellule(ligne, "marches"), ID_PENDING)

    cooperatives = [
        make_cooperative(nom, ID_PENDING)
        for nom in parser_liste_simple(lire_cellule(ligne, "cooperatives"))
    ]

    # ── Lieux (toutes categories) ───────────────────────────────
    lieux = []
    for nom_interne, type_lieu in TYPES_LIEUX.items():
        lieux += parser_lieux(lire_cellule(ligne, nom_interne), type_lieu, ID_PENDING)

    # ── Exercice annuel ─────────────────────────────────────────
    nb_habitants_str = lire_cellule(ligne, "nb_habitants")
    try:
        nb_habitants = int(nb_habitants_str) if nb_habitants_str else None
    except ValueError:
        nb_habitants = None

    non_electrifies = parser_liste_simple(lire_cellule(ligne, "villages_non_electrifies"))
    besoins = parser_liste_simple(lire_cellule(ligne, "besoins_technologiques"))

    electrifie = convertir_bool(lire_cellule(ligne, "zone_electrifiee"))
    taux_electrification = 100.0 if electrifie else 0.0

    # Signature exacte de make_exercice :
    # make_exercice(id_commune, annee, nombre_habitants, taux_electrification,
    #               taux_connectivite, villages_non_electrifies, besoins_technologiques)
    exercice = make_exercice(
        ID_PENDING,              # id_commune
        None,                    # annee
        nb_habitants,            # nombre_habitants
        taux_electrification,    # taux_electrification
        None,                    # taux_connectivite
        non_electrifies,         # villages_non_electrifies
        besoins,                 # besoins_technologiques
    )

    # ── Retour structure complete ────────────────────────────────
    return {
        "hierarchie": {
            "region": region_nom,
            "departement": departement_nom,
            "arrondissement": arrondissement_nom,
        },
        "commune": {
            "nom": commune_nom,
            "contact_mairie": contact_mairie,
            "contact_personne_ressource": contact_ressource,
            "coordonnees": coordonnees,
            "langues_locales": langues,
            "delegations_ministeres": delegations,
            "agriculture_artisanat": agriculture,
            "image_url": image_url,
            "gare_voyageurs": gares,
            "connectivite_constante": connectivite,
            "villages_non_connectes": non_connectes,
            "lien_etranger": lien_etranger,
            "pays_etrangers": pays_etrangers,
            "autres_informations": autres_infos,
            "kobocollect_uuid": uuid,
            "submitted_by": submitted_by,
            "submission_time": submission_time,
        },
        "villages":      villages,
        "chefferies":    chefferies,
        "ethnies":       ethnies,
        "marches":       marches,
        "lieux":         lieux,
        "cooperatives":  cooperatives,
        "exercice":      exercice,
    }