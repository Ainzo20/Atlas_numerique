"""
models.py
---------
Definition des structures de donnees (modeles) de l'application.

Chaque classe represente une collection MongoDB et definit
la structure attendue des documents. Ces modeles servent de
reference pour la construction des documents avant insertion.

Aucune logique metier ici — uniquement les structures.
"""


def make_region(nom: str) -> dict:
    """
    Construit un document Region.

    Args:
        nom (str): Nom de la region.

    Returns:
        dict: Document pret a etre insere dans la collection regions.
    """
    return {
        "nom": nom,
        "geometrie": None,       # alimenté via GeoJSON separement
        "superficie": None,
        "population": None,
        "capitale": None,
        "chef_region": None,
        "date_creation": None,
    }


def make_departement(nom: str, id_region: str) -> dict:
    """
    Construit un document Departement.

    Args:
        nom (str): Nom du departement.
        id_region (str): Identifiant MongoDB de la region parente.

    Returns:
        dict: Document pret a etre insere dans la collection departements.
    """
    return {
        "nom": nom,
        "id_region": id_region,
        "geometrie": None,
        "superficie": None,
        "population": None,
        "chef_departement": None,
        "code_postal": None,
    }


def make_arrondissement(nom: str, id_departement: str) -> dict:
    """
    Construit un document Arrondissement.

    Args:
        nom (str): Nom de l'arrondissement.
        id_departement (str): Identifiant MongoDB du departement parent.

    Returns:
        dict: Document pret a etre insere dans la collection arrondissements.
    """
    return {
        "nom": nom,
        "id_departement": id_departement,
        "geometrie": None,
        "superficie": None,
        "population": None,
        "chef_arrondissement": None,
        "code_postal": None,
    }


def make_commune(
    nom: str,
    id_arrondissement: str,
    contact_mairie: dict,
    contact_personne_ressource: dict,
    coordonnees: dict,
    langues_locales: list[str],
    delegations_ministeres: list[str],
    agriculture_artisanat: list[str],
    image_url: str | None,
    gare_voyageurs: list[dict],
    connectivite_constante: bool,
    villages_non_connectes: list[str],
    lien_etranger: bool,
    pays_etrangers: list[str],
    autres_informations: str | None,
    kobocollect_uuid: str | None,
    submitted_by: str | None,
    submission_time: str | None,
) -> dict:
    """
    Construit un document Commune.

       Args:
        nom (str): Nom de la commune.
        id_arrondissement (str): Identifiant MongoDB de l'arrondissement parent.
        contact_mairie (dict): Contact mairie {telephones, mails, code_postal}.
        contact_personne_ressource (dict): Personne ressource
            {nom, role, telephones, mails, code_postal}.
        coordonnees (dict): GPS {latitude, longitude, altitude, precision}.
        langues_locales (list[str]): Liste des langues locales.
        delegations_ministeres (list[str]): Liste des delegations.
        agriculture_artisanat (list[str]): Activites agricoles et artisanales.
        image_url (str | None): URL de l'image de la carte.
        gare_voyageurs (list[dict]): Gares avec nom et coordonnees.
        connectivite_constante (bool): Connexion internet constante ou non.
        villages_non_connectes (list[str]): Villages sans connexion.
        lien_etranger (bool): Liee a un pays etranger ou non.
        pays_etrangers (list[str]): Pays etrangers concernes.
        autres_informations (str | None): Informations complementaires.
        kobocollect_uuid (str | None): UUID de tracabilite KoboCollect.
        submitted_by (str | None): Agent qui a soumis le formulaire.
        submission_time (str | None): Heure de soumission KoboCollect.

    Returns:
        dict: Document pret a etre insere dans la collection communes.
    """
    return {
        "nom": nom,
        "id_arrondissement": id_arrondissement,
        "id_type": None,               # enrichi manuellement
        "id_communaute_urbaine": None, # enrichi manuellement
        "population": None,
        "superficie": None,
        "culture_dominante": None,
        "objet_art_dominant": None,
        "contact_mairie": contact_mairie,
        "contact_personne_ressource": contact_personne_ressource,
        "coordonnees": coordonnees,
        "langues_locales": langues_locales,
        "delegations_ministeres": delegations_ministeres,
        "agriculture_artisanat": agriculture_artisanat,
        "image_url": image_url,
        "gare_voyageurs": gare_voyageurs,
        "connectivite_constante": connectivite_constante,
        "villages_non_connectes": villages_non_connectes,
        "lien_etranger": lien_etranger,
        "pays_etrangers": pays_etrangers,
        "autres_informations": autres_informations,
        "kobocollect_uuid": kobocollect_uuid,
        "submitted_by": submitted_by,
        "submission_time": submission_time,
    }


def make_village_quartier(
    nom: str,
    type_localite: str,
    id_commune: str,
) -> dict:
    """
    Construit un document Village ou Quartier.

    Args:
        nom (str): Nom du village ou quartier.
        type_localite (str): "village" ou "quartier".
        id_commune (str): Identifiant MongoDB de la commune parente.

    Returns:
        dict: Document pret a etre insere dans la collection villages_quartiers.
    """
    return {
        "nom": nom,
        "type": type_localite,   # "village" ou "quartier"
        "chef": None,
        "population": None,
        "superficie": None,
        "id_commune": id_commune,
    }


def make_chefferie(
    nom: str,
    latitude: float | None,
    longitude: float | None,
    altitude: float | None,
    precision: float | None,
    id_commune: str,
) -> dict:
    """
    Construit un document Chefferie.

    Args:
        nom (str): Nom de la chefferie.
        latitude (float | None): Latitude GPS.
        longitude (float | None): Longitude GPS.
        altitude (float | None): Altitude en metres.
        precision (float | None): Precision du releve GPS.
        id_commune (str): Identifiant MongoDB de la commune parente.

    Returns:
        dict: Document pret a etre insere dans la collection chefferies.
    """
    return {
        "nom": nom,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "precision": precision,
        "id_commune": id_commune,
    }


def make_ethnie(nom: str, id_commune: str) -> dict:
    """
    Construit un document Ethnie.

    Args:
        nom (str): Nom de l'ethnie.
        id_commune (str): Identifiant MongoDB de la commune parente.

    Returns:
        dict: Document pret a etre insere dans la collection ethnies.
    """
    return {
        "nom": nom,
        "salutations": None,  # enrichi manuellement
        "id_commune": id_commune,
    }


def make_jour_marche(
    nom: str,
    jour: str | None,
    heure_debut: str | None,
    heure_fin: str | None,
    id_commune: str,
) -> dict:
    """
    Construit un document Jour de Marche.

    Args:
        nom (str): Nom du marche.
        jour (str | None): Jour(s) de marche.
        heure_debut (str | None): Heure d'ouverture.
        heure_fin (str | None): Heure de fermeture.
        id_commune (str): Identifiant MongoDB de la commune parente.

    Returns:
        dict: Document pret a etre insere dans la collection jours_marche.
    """
    return {
        "nom": nom,
        "jour": jour,
        "heure_debut": heure_debut,
        "heure_fin": heure_fin,
        "description": None,
        "id_commune": id_commune,
    }


def make_lieu(
    nom: str,
    type_nom: str,
    latitude: float | None,
    longitude: float | None,
    id_commune: str,
) -> dict:
    """
    Construit un document Lieu.

    Args:
        nom (str): Nom du lieu.
        type_nom (str): Type du lieu (scolaire, urgence, touristique,
                        eau, sportif, religieux, reference).
        latitude (float | None): Latitude GPS.
        longitude (float | None): Longitude GPS.
        id_commune (str): Identifiant MongoDB de la commune parente.

    Returns:
        dict: Document pret a etre insere dans la collection lieux.
    """
    return {
        "nom": nom,
        "type_nom": type_nom,
        "sous_type_id": None,   # enrichi manuellement apres import
        "description": None,
        "coordonnees": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "image_url": None,
        "heure_ouverture": None,
        "heure_fermeture": None,
        "contact": None,
        "condition_acces": None,
        "id_commune": id_commune,
    }


def make_cooperative(nom: str, id_commune: str) -> dict:
    """
    Construit un document Cooperative / GIC.

    Args:
        nom (str): Nom de la cooperative ou GIC.
        id_commune (str): Identifiant MongoDB de la commune parente.

    Returns:
        dict: Document pret a etre insere dans la collection cooperatives.
    """
    return {
        "nom": nom,
        "id_commune": id_commune,
    }


def make_exercice(
    id_commune: str,
    annee: str | None,
    nombre_habitants: int | None,
    taux_electrification: float | None,
    taux_connectivite: float | None,
    villages_non_electrifies: list[str],
    besoins_technologiques: list[str],
) -> dict:
    """
    Construit un document Exercice annuel.

    Args:
        id_commune (str): Identifiant MongoDB de la commune parente.
        annee (str | None): Annee de l'exercice.
        nombre_habitants (int | None): Nombre d'habitants.
        taux_electrification (float | None): Taux d'electrification en %.
        taux_connectivite (float | None): Taux de connectivite en %.
        villages_non_electrifies (list[str]): Villages sans electricite.
        besoins_technologiques (list[str]): Besoins technologiques identifies.

    Returns:
        dict: Document pret a etre insere dans la collection exercices.
    """
    return {
        "id_commune": id_commune,
        "maire": None,           # enrichi manuellement
        "budget_annuel": None,   # enrichi manuellement
        "annee": annee,
        "nombre_habitants": nombre_habitants,
        "taux_electrification": taux_electrification,
        "taux_connectivite": taux_connectivite,
        "villages_non_electrifies": villages_non_electrifies,
        "besoins_technologiques": besoins_technologiques,
    }