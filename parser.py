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
# NOTE : le vrai export KoboCollect utilise "/" comme separateur d'entites,
# pas "|". Si un jour une entite contient elle-meme un "/" (adresse,
# horaire...), il faudra revoir ce choix avec le formulaire XLSForm.
SEP_ENTITES    = "/"
SEP_ATTRIBUTS  = "::"
SEP_VALEURS    = ","
VALEUR_ABSENTE = "RAS"

COLONNES = {
    "region":         "Région",
    "departement":    "Département",
    "arrondissement": "Arrondissement",

    "contact_mairie": "Contact de la mairie",
    "contact_ressource": "Contact de la personne ressource",

    "gps_commune-Latitude":  "_Coordonnées GPS de la commune_latitude",
    "gps_commune-Longitude": "_Coordonnées GPS de la commune_longitude",
    "gps_commune-Altitude":  "_Coordonnées GPS de la commune_altitude",
    "gps_commune-Accuracy":  "_Coordonnées GPS de la commune_precision",

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

    "kobocollect_uuid":   "_uuid",
    "submitted_by":       "_submitted_by",
    "submission_time":    "_submission_time",
}

TYPES_LIEUX = {
    "points_religieux":    "religieux",
    "points_reference":    "reference",
    "sites_touristiques":  "touristique",
    "ecoles":              "scolaire",
    "urgences":            "urgence",
    "points_eau":          "eau",
    "infra_sportives":     "sportif",
}


def nettoyer_valeur(valeur: str):
    if not isinstance(valeur, str):
        return None
    valeur = valeur.strip()
    if valeur.upper() == VALEUR_ABSENTE or valeur == "":
        return None
    return valeur


def eclater_entites(cellule: str):
    if not nettoyer_valeur(cellule):
        return []
    entites = [e.strip() for e in cellule.split(SEP_ENTITES)]
    return [e for e in entites if nettoyer_valeur(e)]


def eclater_attributs(entite: str):
    attributs = entite.split(SEP_ATTRIBUTS)
    return [nettoyer_valeur(a) for a in attributs]


def eclater_valeurs_multiples(valeur: str):
    if not nettoyer_valeur(valeur):
        return []
    valeurs = [v.strip() for v in valeur.split(SEP_VALEURS)]
    return [v for v in valeurs if nettoyer_valeur(v)]


def convertir_float(valeur):
    if not valeur:
        return None
    try:
        return float(valeur)
    except ValueError:
        logger.warning(f"Impossible de convertir '{valeur}' en float.")
        return None


def convertir_bool(valeur):
    if not valeur:
        return False
    return valeur.strip().lower() == "oui"


def lire_cellule(ligne: pd.Series, nom_interne: str) -> str:
    valeur = ligne.get(nom_interne)

    if pd.isna(valeur) or (isinstance(valeur, str) and valeur.strip() == ""):
        ancien_nom = COLONNES.get(nom_interne)
        if ancien_nom:
            valeur = ligne.get(ancien_nom)

    if pd.isna(valeur):
        return ""
    return str(valeur).strip()


def parser_contact(cellule: str) -> dict:
    parties = cellule.split(SEP_ENTITES)
    while len(parties) < 3:
        parties.append(VALEUR_ABSENTE)

    return {
        "telephones": eclater_valeurs_multiples(parties[0]),
        "mails": eclater_valeurs_multiples(parties[1]),
        "code_postal": nettoyer_valeur(parties[2]),
    }


def parser_contact_ressource(cellule: str) -> dict:
    # NOTE : contrairement aux autres champs structures (villages, marches),
    # celui-ci utilise le meme separateur "/" que les entites, pas "::".
    # Format reel observe : nom/role/tel/mail[/code_postal]
    parties = cellule.split(SEP_ENTITES)
    while len(parties) < 5:
        parties.append(VALEUR_ABSENTE)

    return {
        "nom": nettoyer_valeur(parties[0]),
        "role": nettoyer_valeur(parties[1]),
        "telephones": eclater_valeurs_multiples(parties[2]),
        "mails": eclater_valeurs_multiples(parties[3]),
        "code_postal": nettoyer_valeur(parties[4]),
    }


def parser_villages_quartiers(cellule: str, id_commune: str):
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
            resultats.append(make_village_quartier(nom, type_localite, id_commune))
    return resultats


def parser_chefferies(cellule: str, id_commune: str):
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 5:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            resultats.append(make_chefferie(
                nom,
                convertir_float(attributs[1]),
                convertir_float(attributs[2]),
                convertir_float(attributs[3]),
                convertir_float(attributs[4]),
                id_commune
            ))
    return resultats


def parser_lieux(cellule: str, type_lieu: str, id_commune: str):
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 3:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            resultats.append(make_lieu(
                nom,
                type_lieu,
                convertir_float(attributs[1]),
                convertir_float(attributs[2]),
                id_commune
            ))
    return resultats


def parser_marches(cellule: str, id_commune: str):
    resultats = []
    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)
        while len(attributs) < 4:
            attributs.append(None)
        nom = attributs[0]
        if nom:
            resultats.append(make_jour_marche(
                nom,
                attributs[1],
                attributs[2],
                attributs[3],
                id_commune
            ))
    return resultats


def parser_liste_simple(cellule: str):
    """
    Parse un champ liste simple. Le separateur reel observe varie selon
    le champ : la plupart utilisent "/" (SEP_ENTITES), mais certains
    champs Kobo de type "select_multiple" (ex: langues locales) utilisent
    "," a la place. On tente "/" d'abord ; si une seule "entite" ressort
    et qu'elle contient une virgule, on retente avec la virgule.
    A VERIFIER avec le XLSForm si d'autres champs sont dans ce cas.
    """
    entites = eclater_entites(cellule)
    if len(entites) == 1 and SEP_VALEURS in entites[0]:
        return eclater_valeurs_multiples(entites[0])
    return entites


def parser_gare(cellule: str):
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
    return {
        "latitude": convertir_float(lire_cellule(ligne, "gps_commune-Latitude")),
        "longitude": convertir_float(lire_cellule(ligne, "gps_commune-Longitude")),
        "altitude": convertir_float(lire_cellule(ligne, "gps_commune-Altitude")),
        "precision": convertir_float(lire_cellule(ligne, "gps_commune-Accuracy")),
    }


def parser_csv(contenu_fichier: bytes):
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
    region_nom         = lire_cellule(ligne, "region")
    departement_nom    = lire_cellule(ligne, "departement")
    arrondissement_nom = lire_cellule(ligne, "arrondissement")

    if not region_nom or not departement_nom or not arrondissement_nom:
        raise ValueError(f"Champs hierarchiques manquants (Region / Departement / Arrondissement).")

    commune_nom = arrondissement_nom

    contact_mairie = parser_contact(lire_cellule(ligne, "contact_mairie"))
    contact_ressource = parser_contact_ressource(lire_cellule(ligne, "contact_ressource"))

    coordonnees = parser_coordonnees_commune(ligne)

    langues         = parser_liste_simple(lire_cellule(ligne, "langues_locales"))
    delegations     = parser_liste_simple(lire_cellule(ligne, "delegations_ministeres"))
    agriculture     = parser_liste_simple(lire_cellule(ligne, "agriculture_artisanat"))
    image_url       = nettoyer_valeur(lire_cellule(ligne, "image_carte"))
    autres_infos    = nettoyer_valeur(lire_cellule(ligne, "autres_infos"))
    connectivite    = convertir_bool(lire_cellule(ligne, "connectivite"))
    lien_etranger   = convertir_bool(lire_cellule(ligne, "lien_etranger"))
    pays_etrangers  = parser_liste_simple(lire_cellule(ligne, "pays_etrangers"))
    non_connectes   = parser_liste_simple(lire_cellule(ligne, "villages_non_connectes"))

    gares = parser_gare(lire_cellule(ligne, "gare_voyageurs"))

    uuid            = nettoyer_valeur(lire_cellule(ligne, "kobocollect_uuid"))
    submitted_by    = nettoyer_valeur(lire_cellule(ligne, "submitted_by"))
    submission_time = nettoyer_valeur(lire_cellule(ligne, "submission_time"))

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

    lieux = []
    for nom_interne, type_lieu in TYPES_LIEUX.items():
        lieux += parser_lieux(lire_cellule(ligne, nom_interne), type_lieu, ID_PENDING)

    nb_habitants_str = lire_cellule(ligne, "nb_habitants")
    try:
        nb_habitants = int(nb_habitants_str) if nb_habitants_str else None
    except ValueError:
        nb_habitants = None

    non_electrifies = parser_liste_simple(lire_cellule(ligne, "villages_non_electrifies"))
    besoins = parser_liste_simple(lire_cellule(ligne, "besoins_technologiques"))

    electrifie = convertir_bool(lire_cellule(ligne, "zone_electrifiee"))
    taux_electrification = 100.0 if electrifie else 0.0

    exercice = make_exercice(
        ID_PENDING,
        None,
        nb_habitants,
        taux_electrification,
        None,
        non_electrifies,
        besoins,
    )

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