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

# Separateurs
SEP_ENTITES    = "|"   # entre entites distinctes
SEP_ATTRIBUTS  = "::"  # entre attributs d'une entite
SEP_VALEURS    = ","   # entre valeurs multiples d'un attribut
VALEUR_ABSENTE = "RAS" # valeur manquante dans le CSV

# Types de lieux reconnus
TYPES_LIEUX = {
    "Points religieux":                    "religieux",
    "Points de reference dans le secteur (bar, hotel, etc.)": "reference",
    "Sites touristiques":                  "touristique",
    "Ecoles et types":                     "scolaire",
    "Urgences":                            "urgence",
    "Points d eau":                        "eau",
    "Infrastructures sportives":           "sportif",
}


# ════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# Ces fonctions sont petites et font une seule chose chacune.
# Elles sont utilisees par les fonctions de parsing plus bas.
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

    # RAS signifie "Rien A Signaler" — on stocke None dans MongoDB
    if valeur.upper() == VALEUR_ABSENTE or valeur == "":
        return None

    return valeur


def eclater_entites(cellule: str) -> list[str]:
    """
    Eclate une cellule contenant plusieurs entites separees par |.
    Filtre les entites vides ou RAS.

    Exemple :
        "Baladji|Dang|RAS" → ["Baladji", "Dang"]

    Args:
        cellule (str): Contenu brut de la cellule CSV.

    Returns:
        list[str]: Liste des entites valides.
    """
    if not nettoyer_valeur(cellule):
        return []

    entites = [e.strip() for e in cellule.split(SEP_ENTITES)]

    # On garde uniquement les entites non vides et non RAS
    return [e for e in entites if nettoyer_valeur(e)]


def eclater_attributs(entite: str) -> list[str | None]:
    """
    Eclate une entite en ses attributs separes par ::.
    Chaque attribut est nettoye (RAS → None).

    Exemple :
        "Lamido::7.32::13.58::1104::3"
        → ["Lamido", "7.32", "13.58", "1104", "3"]

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
    Filtre les valeurs vides ou RAS.

    Exemple :
        "+237 222 001,+237 222 002" → ["+237 222 001", "+237 222 002"]

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
    Retourne None si la conversion est impossible.

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


def lire_cellule(ligne: pd.Series, colonne: str) -> str:
    """
    Lit la valeur d'une cellule dans une ligne du DataFrame.
    Retourne une chaine vide si la colonne est absente ou NaN.

    Args:
        ligne (pd.Series): Ligne du DataFrame pandas.
        colonne (str): Nom de la colonne a lire.

    Returns:
        str: Valeur de la cellule ou chaine vide.
    """
    valeur = ligne.get(colonne, "")

    # pandas represente les valeurs manquantes par NaN (float)
    # on les convertit en chaine vide
    if pd.isna(valeur):
        return ""

    return str(valeur).strip()


# ════════════════════════════════════════════════════════════════
# FONCTIONS DE PARSING PAR TYPE DE CHAMP
# Chaque fonction sait lire un champ specifique du CSV
# et retourne une structure Python propre.
# ════════════════════════════════════════════════════════════════

def parser_contact(cellule: str) -> dict:
    """
    Parse un champ contact au format : telephone|mail|code_postal
    Chaque partie peut contenir plusieurs valeurs separees par virgule.
    RAS est converti en liste vide.

    Exemple :
        "+237 222 001,+237 222 002|mairie@cm.gov|237001"
        → {
            "telephones":  ["+237 222 001", "+237 222 002"],
            "mails":       ["mairie@cm.gov"],
            "code_postal": "237001"
          }

    Args:
        cellule (str): Contenu brut du champ contact.

    Returns:
        dict: Contact structure avec telephones, mails et code_postal.
    """
    # On decoupe en 3 parties fixes : telephone | mail | code_postal
    parties = cellule.split(SEP_ENTITES)

    # On s'assure d'avoir exactement 3 parties, meme si certaines manquent
    while len(parties) < 3:
        parties.append(VALEUR_ABSENTE)

    telephones  = eclater_valeurs_multiples(parties[0])
    mails       = eclater_valeurs_multiples(parties[1])
    code_postal = nettoyer_valeur(parties[2])

    return {
        "telephones": telephones,
        "mails": mails,
        "code_postal": code_postal,
    }


def parser_villages_quartiers(
    cellule: str,
    id_commune: str
) -> list[dict]:
    """
    Parse le champ villages/quartiers.
    Chaque entite est prefixee par V:: (village) ou Q:: (quartier).

    Exemple :
        "V::Baladji|Q::Centre|V::Dang"
        → [
            {"nom": "Baladji", "type": "village", ...},
            {"nom": "Centre",  "type": "quartier", ...},
            {"nom": "Dang",    "type": "village", ...},
          ]

    Args:
        cellule (str): Contenu brut du champ.
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents villages/quartiers.
    """
    resultats = []

    for entite in eclater_entites(cellule):

        # Detection du type via le prefixe V:: ou Q::
        if entite.upper().startswith("V::"):
            type_localite = "village"
            nom = entite[3:].strip()  # on retire le prefixe "V::"

        elif entite.upper().startswith("Q::"):
            type_localite = "quartier"
            nom = entite[3:].strip()  # on retire le prefixe "Q::"

        else:
            # Pas de prefixe reconnu — on log et on ignore
            logger.warning(
                f"Village/quartier sans prefixe V:: ou Q:: ignore : '{entite}'"
            )
            continue

        if nom:
            resultats.append(
                make_village_quartier(nom, type_localite, id_commune)
            )

    return resultats


def parser_chefferies(cellule: str, id_commune: str) -> list[dict]:
    """
    Parse le champ chefferies.
    Format de chaque chefferie : nom::lat::lng::altitude::precision

    Exemple :
        "Lamido::7.32::13.58::1104::3|Chefferie Beka::7.29::13.56::1098::5"

    Args:
        cellule (str): Contenu brut du champ chefferies.
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents chefferies.
    """
    resultats = []

    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)

        # On attend 5 attributs : nom, lat, lng, altitude, precision
        # S'il en manque on complete avec None
        while len(attributs) < 5:
            attributs.append(None)

        nom       = attributs[0]
        latitude  = convertir_float(attributs[1])
        longitude = convertir_float(attributs[2])
        altitude  = convertir_float(attributs[3])
        precision = convertir_float(attributs[4])

        if nom:
            resultats.append(
                make_chefferie(nom, latitude, longitude, altitude, precision, id_commune)
            )

    return resultats


def parser_lieux(
    cellule: str,
    type_lieu: str,
    id_commune: str
) -> list[dict]:
    """
    Parse un champ de lieux (ecoles, urgences, sites, etc.).
    Format de chaque lieu : nom::latitude::longitude

    Exemple :
        "Hopital Regional::7.32::13.58|Pharmacie::RAS::RAS"

    Args:
        cellule (str): Contenu brut du champ.
        type_lieu (str): Type du lieu (ex: "urgence", "scolaire").
        id_commune (str): ID MongoDB de la commune parente.

    Returns:
        list[dict]: Liste de documents lieux.
    """
    resultats = []

    for entite in eclater_entites(cellule):
        attributs = eclater_attributs(entite)

        # On attend 3 attributs : nom, lat, lng
        while len(attributs) < 3:
            attributs.append(None)

        nom       = attributs[0]
        latitude  = convertir_float(attributs[1])
        longitude = convertir_float(attributs[2])

        if nom:
            resultats.append(
                make_lieu(nom, type_lieu, latitude, longitude, id_commune)
            )

    return resultats


def parser_marches(cellule: str, id_commune: str) -> list[dict]:
    """
    Parse le champ marches.
    Format : nom::jour::heure_debut::heure_fin

    Exemple :
        "Grand Marche::Lundi::06:00::18:00|Marche Beka::Vendredi::07:00::17:00"

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

        nom        = attributs[0]
        jour       = attributs[1]
        heure_deb  = attributs[2]
        heure_fin  = attributs[3]

        if nom:
            resultats.append(
                make_jour_marche(nom, jour, heure_deb, heure_fin, id_commune)
            )

    return resultats


def parser_liste_simple(cellule: str) -> list[str]:
    """
    Parse un champ contenant une liste simple d'entites separees par |.
    Utilise pour les ethnies, langues, delegations, cooperatives, etc.

    Exemple :
        "Foulbé|Mboum|Haoussa" → ["Foulbé", "Mboum", "Haoussa"]

    Args:
        cellule (str): Contenu brut du champ.

    Returns:
        list[str]: Liste de valeurs nettoyees.
    """
    return eclater_entites(cellule)


def parser_gare(cellule: str) -> list[dict]:
    """
    Parse le champ gare voyageurs.
    Format : nom::lat::lng  (plusieurs gares separees par |)

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

        nom       = attributs[0]
        latitude  = convertir_float(attributs[1])
        longitude = convertir_float(attributs[2])

        if nom:
            resultats.append({
                "nom": nom,
                "latitude": latitude,
                "longitude": longitude,
            })

    return resultats


def parser_coordonnees_commune(ligne: pd.Series) -> dict:
    """
    Lit et structure les coordonnees GPS de la commune
    depuis les 4 colonnes GPS du CSV KoboCollect.

    Args:
        ligne (pd.Series): Ligne du DataFrame.

    Returns:
        dict: Coordonnees GPS {latitude, longitude, altitude, precision}.
    """
    return {
        "latitude":  convertir_float(lire_cellule(
            ligne, "_Coordonnees GPS (commune)_latitude")),
        "longitude": convertir_float(lire_cellule(
            ligne, "_Coordonnees GPS (commune)_longitude")),
        "altitude":  convertir_float(lire_cellule(
            ligne, "_Coordonnees GPS (commune)_altitude")),
        "precision": convertir_float(lire_cellule(
            ligne, "_Coordonnees GPS (commune)_precision")),
    }


# ════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# C'est le point d'entree de ce module.
# Elle orchestre toutes les fonctions ci-dessus.
# ════════════════════════════════════════════════════════════════

def parser_csv(contenu_fichier: bytes) -> list[dict]:
    """
    Fonction principale du module.
    Lit un fichier CSV KoboCollect et retourne une liste de communes
    structurees avec toutes leurs donnees associees.

    Chaque element de la liste retournee est un dictionnaire contenant :
    - Les donnees de la commune
    - Les listes de sous-documents (villages, chefferies, lieux, etc.)
    - Les informations de hierarchie (region, departement, arrondissement)

    Args:
        contenu_fichier (bytes): Contenu brut du fichier CSV uploade.

    Returns:
        list[dict]: Liste de communes structurees pretes pour l'insertion.

    Raises:
        ValueError: Si le fichier CSV est vide ou mal forme.
    """
    logger.info("Debut du parsing du fichier CSV...")

    # ── Lecture du CSV avec pandas ──────────────────────────────
    # On utilise BytesIO pour lire depuis la memoire (pas depuis le disque)
    try:
        df = pd.read_csv(
            BytesIO(contenu_fichier),
            sep=";",            # separateur de colonnes
            dtype=str,          # tout lire comme texte pour eviter les
                                # conversions automatiques de pandas
            keep_default_na=False,  # on gere nous-memes les valeurs vides
        )
    except Exception as erreur:
        raise ValueError(f"Impossible de lire le fichier CSV : {erreur}")

    if df.empty:
        raise ValueError("Le fichier CSV est vide.")

    logger.info(f"{len(df)} ligne(s) trouvee(s) dans le CSV.")

    communes_parsees = []

    # ── Traitement ligne par ligne ──────────────────────────────
    # Chaque ligne = une commune
    for index, ligne in df.iterrows():

        # numero de ligne pour les messages d'erreur (commence a 2
        # car la ligne 1 est l'en-tete)
        numero_ligne = index + 2

        try:
            commune_parsee = _parser_ligne(ligne, numero_ligne)
            communes_parsees.append(commune_parsee)
            logger.info(
                f"Ligne {numero_ligne} — "
                f"Commune '{commune_parsee['commune']['nom']}' parsee."
            )

        except Exception as erreur:
            # Une ligne mal formee n'arrete pas le traitement des autres
            logger.error(
                f"Ligne {numero_ligne} ignoree a cause d'une erreur : {erreur}"
            )
            continue

    logger.info(
        f"Parsing termine. "
        f"{len(communes_parsees)}/{len(df)} communes parsees avec succes."
    )

    return communes_parsees


def _parser_ligne(ligne: pd.Series, numero_ligne: int) -> dict:
    """
    Parse une seule ligne du CSV et retourne un dictionnaire structure
    contenant la commune et tous ses sous-documents.

    Cette fonction est privee (prefixe _) — elle n'est appelee
    que par parser_csv().

    Args:
        ligne (pd.Series): Ligne du DataFrame a parser.
        numero_ligne (int): Numero de la ligne (pour les logs).

    Returns:
        dict: Structure complete de la commune avec ses sous-documents.

    Raises:
        ValueError: Si les champs obligatoires sont manquants.
    """

    # ── Champs obligatoires ─────────────────────────────────────
    # Sans ces champs on ne peut pas construire la hierarchie
    region_nom         = lire_cellule(ligne, "Region")
    departement_nom    = lire_cellule(ligne, "Departement")
    arrondissement_nom = lire_cellule(ligne, "Arrondissement")

    if not region_nom or not departement_nom or not arrondissement_nom:
        raise ValueError(
            f"Champs hierarchiques manquants "
            f"(Region / Departement / Arrondissement)."
        )

    # ── Nom de la commune ───────────────────────────────────────
    # Le CSV KoboCollect n'a pas de colonne "Commune" explicite.
    # On utilise l'arrondissement comme nom de commune (a affiner
    # si le format evolue).
    commune_nom = arrondissement_nom

    # ── Contacts ────────────────────────────────────────────────
    contact_mairie = parser_contact(
        lire_cellule(ligne, "Contact de la mairie (telephone|mail|code_postal)")
    )
    contact_ressource = parser_contact(
        lire_cellule(ligne, "Contact de la personne ressource (telephone|mail|code_postal)")
    )

    # ── Coordonnees GPS de la commune ───────────────────────────
    coordonnees = parser_coordonnees_commune(ligne)

    # ── Champs simples de la commune ────────────────────────────
    langues         = parser_liste_simple(lire_cellule(ligne, "Langues locales"))
    delegations     = parser_liste_simple(lire_cellule(ligne, "Delegations des ministeres sectoriels"))
    agriculture     = parser_liste_simple(lire_cellule(ligne, "Agriculture/artisanat"))
    image_url       = nettoyer_valeur(lire_cellule(ligne, "Image de la carte de la commune_URL"))
    autres_infos    = nettoyer_valeur(lire_cellule(ligne, "Autres informations"))
    connectivite    = convertir_bool(lire_cellule(ligne, "Connectivite internet constante?"))
    lien_etranger   = convertir_bool(lire_cellule(ligne, "Est-elle liee avec les pays etrangers"))
    pays_etrangers  = parser_liste_simple(lire_cellule(ligne, "si oui, lister les pays etrangers."))
    non_connectes   = parser_liste_simple(lire_cellule(ligne, "Sinon, listez les villages connectes"))

    # ── Gare voyageurs ──────────────────────────────────────────
    gares = parser_gare(lire_cellule(ligne, "Voyages - lieu de la gare voyageur"))

    # ── Tracabilite KoboCollect ─────────────────────────────────
    uuid            = nettoyer_valeur(lire_cellule(ligne, "_uuid"))
    submitted_by    = nettoyer_valeur(lire_cellule(ligne, "_submitted_by"))
    submission_time = nettoyer_valeur(lire_cellule(ligne, "_submission_time"))

    # ── Sous-documents (seront inseres dans leurs collections) ──
    # id_commune sera assigned lors de l'insertion dans database.py
    # Pour l'instant on utilise un placeholder "PENDING"
    ID_PENDING = "PENDING"

    villages = parser_villages_quartiers(
        lire_cellule(ligne, "Quartiers ou villages"), ID_PENDING
    )

    chefferies = parser_chefferies(
        lire_cellule(ligne, "Chefferies"), ID_PENDING
    )

    ethnies = [
        make_ethnie(nom, ID_PENDING)
        for nom in parser_liste_simple(lire_cellule(ligne, "Ethnies"))
    ]

    marches = parser_marches(
        lire_cellule(ligne, "Marches et jours du marche"), ID_PENDING
    )

    cooperatives = [
        make_cooperative(nom, ID_PENDING)
        for nom in parser_liste_simple(lire_cellule(ligne, "Cooperatives, GIC, etc."))
    ]

    # ── Lieux (toutes categories) ───────────────────────────────
    lieux = []
    for colonne_csv, type_lieu in TYPES_LIEUX.items():
        lieux += parser_lieux(
            lire_cellule(ligne, colonne_csv), type_lieu, ID_PENDING
        )

    # ── Exercice annuel ─────────────────────────────────────────
    nb_habitants = lire_cellule(ligne, "Nombre d habitants de la commune")
    try:
        nb_habitants = int(nb_habitants) if nb_habitants else None
    except ValueError:
        nb_habitants = None

    non_electrifies = parser_liste_simple(
        lire_cellule(ligne, "Si non, lister les villages electrifies.")
    )
    besoins = parser_liste_simple(
        lire_cellule(ligne, "Besoins en terme de technologie")
    )

    # taux_electrification : Oui → 100.0, Non → 0.0, on affinera manuellement
    electrifie = convertir_bool(
        lire_cellule(ligne, "Zone entierement electrifiee?")
    )
    taux_electrification = 100.0 if electrifie else 0.0

    exercice = make_exercice(
        id_commune=ID_PENDING,
        annee=None,             # non present dans le CSV — a enrichir
        nombre_habitants=nb_habitants,
        taux_electrification=taux_electrification,
        taux_connectivite=None, # non present dans le CSV — a enrichir
        villages_non_electrifies=non_electrifies,
        besoins_technologiques=besoins,
    )

    # ── Retour structure complete ────────────────────────────────
    # database.py utilisera cette structure pour inserer dans MongoDB
    return {
        # Hierarchie — utilisee par database.py pour trouver/creer
        # les documents parents avant d'inserer la commune
        "hierarchie": {
            "region": region_nom,
            "departement": departement_nom,
            "arrondissement": arrondissement_nom,
        },

        # Document commune (sans id_arrondissement — sera ajoute par database.py)
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

        # Sous-documents — seront inseres dans leurs collections respectives
        # apres l'insertion de la commune (pour recuperer son vrai _id MongoDB)
        "villages":      villages,
        "chefferies":    chefferies,
        "ethnies":       ethnies,
        "marches":       marches,
        "lieux":         lieux,
        "cooperatives":  cooperatives,
        "exercice":      exercice,
    }