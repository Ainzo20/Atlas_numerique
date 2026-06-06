# schemas.py
# -----------
# Schemas Pydantic pour la documentation OpenAPI.
# Chaque champ est type explicitement pour que Swagger UI
# affiche les structures JSON completes.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any


# ════════════════════════════════════════════════════════════════
# MODÈLES PARTAGÉS
# ════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Structure standard retournée en cas d'erreur (400, 401, 403, 404, 500)"""
    detail: str = Field(
        description="Message d'erreur explicite indiquant la cause du problème",
        examples=["ID invalide : '123'.", "Cle API invalide."]
    )

class CoordonneesSchema(BaseModel):
    """Coordonnees GPS d'un point geographique"""
    latitude: Optional[float] = Field(default=None, description="Latitude GPS", examples=[3.8666])
    longitude: Optional[float] = Field(default=None, description="Longitude GPS", examples=[11.5166])
    altitude: Optional[float] = Field(default=None, description="Altitude en metres", examples=[750.0])
    precision: Optional[float] = Field(default=None, description="Precision du releve GPS en metres", examples=[5.0])

class CoordonneesLieuSchema(BaseModel):
    """Coordonnees simplifiees pour les lieux (sans altitude/precision)"""
    latitude: Optional[float] = Field(default=None, examples=[3.89])
    longitude: Optional[float] = Field(default=None, examples=[11.52])

class ContactMairieSchema(BaseModel):
    """Informations de contact de la mairie"""
    telephones: List[str] = Field(default_factory=list, examples=[["+237699999999"]])
    mails: List[str] = Field(default_factory=list, examples=[["mairie@yaounde1.cm"]])
    code_postal: Optional[str] = Field(default=None, examples=["00237"])

class ContactPersonneSchema(BaseModel):
    """Contact de la personne ressource"""
    nom: Optional[str] = Field(default=None, examples=["Jean Etoa"])
    role: Optional[str] = Field(default=None, examples=["Chef Service Technique"])
    telephones: List[str] = Field(default_factory=list)
    mails: List[str] = Field(default_factory=list)
    code_postal: Optional[str] = Field(default=None)

class GareVoyageursSchema(BaseModel):
    """Gare routiere ou ferroviaire"""
    nom: str = Field(description="Nom de la gare", examples=["Gare routière de Nlongkak"])
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)


# ════════════════════════════════════════════════════════════════
# SANTÉ & STATISTIQUES
# ════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    statut: str = Field(description="Etat de l'application", examples=["en ligne"])
    mongodb: str = Field(description="Etat de la connexion MongoDB", examples=["connecte", "deconnecte"])
    base_de_donnees: str = Field(description="Nom de la base de donnees active", examples=["atlas_cameroun"])

class StatsResponse(BaseModel):
    regions: int = Field(description="Nombre de regions", examples=[10])
    departements: int = Field(description="Nombre de departements", examples=[58])
    arrondissements: int = Field(description="Nombre d'arrondissements", examples=[360])
    communes: int = Field(description="Nombre de communes", examples=[360])
    villages: int = Field(description="Nombre de villages", examples=[5000])
    chefferies: int = Field(description="Nombre de chefferies", examples=[500])
    ethnies: int = Field(description="Nombre d'ethnies", examples=[250])
    marches: int = Field(description="Nombre de marches", examples=[1200])
    lieux: int = Field(description="Nombre de lieux", examples=[8000])
    cooperatives: int = Field(description="Nombre de cooperatives", examples=[300])
    exercices: int = Field(description="Nombre d'exercices annuels", examples=[1000])


# ════════════════════════════════════════════════════════════════
# IMPORT & EXPORT
# ════════════════════════════════════════════════════════════════

class ImportDetailItem(BaseModel):
    """Detail de l'import pour une commune specifique"""
    statut: str = Field(description="Statut de l'operation", examples=["existante", "nouvelle", "erreur"])
    commune: str = Field(description="Nom de la commune traitee", examples=["Ngaoundere I"])
    id_commune: Optional[str] = Field(default=None, description="Identifiant MongoDB de la commune")
    sous_documents: Optional[dict] = Field(
        default=None,
        description="Nombre de sous-documents inseres par categorie",
        examples=[{"villages": 3, "chefferies": 2, "ethnies": 0, "marches": 2, "lieux": 4, "cooperatives": 0}]
    )
    message: Optional[str] = Field(default=None, description="Message d'erreur si statut=erreur")

class ImportReportResponse(BaseModel):
    """Rapport complet retourne apres un import CSV"""
    total: int = Field(description="Nombre total de lignes traitees dans le CSV", examples=[2])
    succes: int = Field(description="Nombre de communes importees avec succes", examples=[2])
    erreurs: int = Field(description="Nombre de lignes rejetees", examples=[0])
    details: List[ImportDetailItem] = Field(description="Detail ligne par ligne de l'import")


# ════════════════════════════════════════════════════════════════
# SOUS-DOCUMENTS TYPÉS
# ════════════════════════════════════════════════════════════════

class VillageSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(description="Nom du village ou quartier", examples=["Nlongkak"])
    type: Optional[str] = Field(default=None, description="Type: village ou quartier", examples=["quartier"])
    chef: Optional[str] = Field(default=None, description="Nom du chef", examples=["M. Atangana"])
    population: Optional[int] = Field(default=None, examples=[15000])
    superficie: Optional[float] = Field(default=None, description="Superficie en km²")
    id_commune: str = Field(description="ID de la commune parente")

class ChefferieSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(description="Nom de la chefferie", examples=["Chefferie de 3e degré de Nlongkak"])
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    altitude: Optional[float] = Field(default=None)
    precision: Optional[float] = Field(default=None)
    id_commune: str = Field(description="ID de la commune parente")

class EthnieSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(description="Nom de l'ethnie", examples=["Ewondo"])
    salutations: Optional[str] = Field(default=None, description="Salutations locales", examples=["Mbege"])
    id_commune: str = Field(description="ID de la commune parente")

class MarcheSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(description="Nom du marche", examples=["Marché de Nlongkak"])
    jour: Optional[str] = Field(default=None, description="Jour(s) de marche", examples=["Mardi | Vendredi"])
    heure_debut: Optional[str] = Field(default=None, examples=["07:00"])
    heure_fin: Optional[str] = Field(default=None, examples=["18:00"])
    description: Optional[str] = Field(default=None, examples=["Marché de vivres frais"])
    id_commune: str = Field(description="ID de la commune parente")

class LieuSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(description="Nom du lieu", examples=["Lycée de Waldji"])
    type_nom: Optional[str] = Field(default=None, description="Type de lieu", examples=["scolaire"])
    sous_type_id: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    coordonnees: Optional[CoordonneesLieuSchema] = None
    image_url: Optional[str] = Field(default=None)
    heure_ouverture: Optional[str] = Field(default=None)
    heure_fermeture: Optional[str] = Field(default=None)
    contact: Optional[str] = Field(default=None)
    condition_acces: Optional[str] = Field(default=None, examples=["Gratuit"])
    id_commune: str = Field(description="ID de la commune parente")

class CooperativeSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(description="Nom de la cooperative/GIC", examples=["GIC Maraîchers du Mfoundi"])
    id_commune: str = Field(description="ID de la commune parente")

class ExerciceSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    id_commune: str = Field(description="ID de la commune parente")
    maire: Optional[str] = Field(default=None, examples=["M. Mbarga"])
    budget_annuel: Optional[int] = Field(default=None, examples=[500000000])
    annee: Optional[str] = Field(default=None, examples=["2025"])
    nombre_habitants: Optional[int] = Field(default=None, examples=[320000])
    taux_electrification: Optional[float] = Field(default=None, examples=[85.5])
    taux_connectivite: Optional[float] = Field(default=None, examples=[70.0])
    villages_non_electrifies: List[str] = Field(default_factory=list)
    besoins_technologiques: List[str] = Field(default_factory=list)

class LieuTypeCountSchema(BaseModel):
    """Compteur par type de lieu"""
    type: str = Field(description="Nom du type de lieu", examples=["scolaire"])
    count: int = Field(description="Nombre de lieux de ce type", examples=[150])


# ════════════════════════════════════════════════════════════════
# HIÉRARCHIE GÉOGRAPHIQUE
# ════════════════════════════════════════════════════════════════

class RegionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB de la region")
    nom: str = Field(description="Nom de la region", examples=["Centre"])
    nb_departements: int = Field(description="Nombre de departements", examples=[10])

class RegionsListResponse(BaseModel):
    total: int = Field(description="Nombre total de regions", examples=[10])
    regions: List[RegionItem]

class RegionFullSchema(BaseModel):
    """Detail complet d'une region"""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Centre"])
    geometrie: Optional[Any] = Field(default=None, description="Donnees GeoJSON")
    superficie: Optional[float] = Field(default=None, examples=[38950])
    population: Optional[int] = Field(default=None, examples=[4200000])
    capitale: Optional[str] = Field(default=None, examples=["Yaoundé"])
    chef_region: Optional[str] = Field(default=None, examples=["Gouverneur X"])
    date_creation: Optional[str] = Field(default=None)

class DepartementWithCountSchema(BaseModel):
    """Departement avec compteur d'arrondissements"""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Mfoundi"])
    id_region: str = Field(description="ID de la region parente")
    nb_arrondissements: int = Field(examples=[7])

class RegionDetailResponse(BaseModel):
    region: RegionFullSchema = Field(description="Details complets de la region")
    departements: List[DepartementWithCountSchema] = Field(description="Departements avec nb_arrondissements")

class DepartementFullSchema(BaseModel):
    """Detail complet d'un departement"""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Mfoundi"])
    id_region: str = Field(description="ID de la region parente")
    geometrie: Optional[Any] = Field(default=None)
    superficie: Optional[float] = Field(default=None, examples=[297])
    population: Optional[int] = Field(default=None, examples=[2500000])
    chef_departement: Optional[str] = Field(default=None, examples=["Préfet Y"])
    code_postal: Optional[str] = Field(default=None, examples=["8000"])

class ArrondissementWithCountSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Yaoundé I"])
    id_departement: str = Field(description="ID du departement parent")
    nb_communes: int = Field(examples=[1])

class DepartementDetailResponse(BaseModel):
    departement: DepartementFullSchema = Field(description="Details complets du departement")
    arrondissements: List[ArrondissementWithCountSchema] = Field(description="Arrondissements avec nb_communes")

class ArrondissementBaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Yaoundé I"])
    id_departement: Optional[str] = Field(default=None)

class CommuneResumeSchema(BaseModel):
    """Resume d'une commune (champs principaux)"""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Yaoundé I"])
    coordonnees: Optional[CoordonneesSchema] = None
    connectivite_constante: Optional[bool] = Field(default=None)
    contact_mairie: Optional[ContactMairieSchema] = None
    langues_locales: List[str] = Field(default_factory=list)

class ArrondissementDetailResponse(BaseModel):
    arrondissement: ArrondissementBaseSchema = Field(description="Details de l'arrondissement")
    communes: List[CommuneResumeSchema] = Field(description="Communes (infos principales)")


# ════════════════════════════════════════════════════════════════
# COMMUNES & LIEUX
# ════════════════════════════════════════════════════════════════

class CommuneListItem(BaseModel):
    commune: CommuneResumeSchema = Field(description="Donnees de la commune")
    region: Optional[str] = Field(default=None, examples=["Centre"])
    departement: Optional[str] = Field(default=None, examples=["Mfoundi"])
    arrondissement: Optional[str] = Field(default=None, examples=["Yaoundé I"])

class CommunesListResponse(BaseModel):
    total: int = Field(description="Nombre total de communes trouvees", examples=[360])
    communes: List[CommuneListItem]

class CommuneFullSchema(BaseModel):
    """Donnees completes d'une commune"""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id", description="Identifiant MongoDB")
    nom: str = Field(examples=["Yaoundé I"])
    id_arrondissement: str = Field(description="ID de l'arrondissement parent")
    contact_mairie: Optional[ContactMairieSchema] = None
    contact_personne_ressource: Optional[ContactPersonneSchema] = None
    coordonnees: Optional[CoordonneesSchema] = None
    langues_locales: List[str] = Field(default_factory=list)
    delegations_ministeres: List[str] = Field(default_factory=list)
    agriculture_artisanat: List[str] = Field(default_factory=list)
    image_url: Optional[str] = Field(default=None)
    gare_voyageurs: List[GareVoyageursSchema] = Field(default_factory=list)
    connectivite_constante: Optional[bool] = Field(default=None)
    villages_non_connectes: List[str] = Field(default_factory=list)
    lien_etranger: Optional[bool] = Field(default=None)
    pays_etrangers: List[str] = Field(default_factory=list)
    autres_informations: Optional[str] = Field(default=None)
    kobocollect_uuid: Optional[str] = Field(default=None)
    submitted_by: Optional[str] = Field(default=None)
    submission_time: Optional[str] = Field(default=None)

class RegionBaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    nom: str = Field(examples=["Centre"])

class DepartementBaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    nom: str = Field(examples=["Mfoundi"])
    id_region: Optional[str] = Field(default=None)

class HierarchieSchema(BaseModel):
    arrondissement: Optional[ArrondissementBaseSchema] = None
    departement: Optional[DepartementBaseSchema] = None
    region: Optional[RegionBaseSchema] = None

class CommuneDetailResponse(BaseModel):
    commune: CommuneFullSchema = Field(description="Donnees completes de la commune")
    hierarchie: HierarchieSchema = Field(description="Hierarchie ascendante resolue")
    villages: List[VillageSchema] = Field(description="Villages lies")
    chefferies: List[ChefferieSchema] = Field(description="Chefferies liees")
    ethnies: List[EthnieSchema] = Field(description="Ethnies liees")
    marches: List[MarcheSchema] = Field(description="Marches lies")
    lieux: List[LieuSchema] = Field(description="Lieux lies")
    cooperatives: List[CooperativeSchema] = Field(description="Cooperatives liees")
    exercices: List[ExerciceSchema] = Field(description="Exercices lies")

class SousDocumentListResponse(BaseModel):
    total: int = Field(description="Nombre total d'elements", examples=[50])
    data: List[dict] = Field(description="Liste des documents")

class VillagesListResponse(BaseModel):
    total: int = Field(description="Nombre total de villages", examples=[50])
    data: List[VillageSchema]

class ChefferiesListResponse(BaseModel):
    total: int = Field(description="Nombre total de chefferies", examples=[20])
    data: List[ChefferieSchema]

class EthniesListResponse(BaseModel):
    total: int = Field(description="Nombre total d'ethnies", examples=[30])
    data: List[EthnieSchema]

class MarchesListResponse(BaseModel):
    total: int = Field(description="Nombre total de marches", examples=[40])
    data: List[MarcheSchema]

class CooperativesListResponse(BaseModel):
    total: int = Field(description="Nombre total de cooperatives", examples=[15])
    data: List[CooperativeSchema]

class ExercicesListResponse(BaseModel):
    total: int = Field(description="Nombre total d'exercices", examples=[10])
    data: List[ExerciceSchema]

class LieuxListResponse(BaseModel):
    total: int = Field(description="Nombre total de lieux", examples=[100])
    data: List[LieuSchema]

class LieuxTypesResponse(BaseModel):
    types: List[LieuTypeCountSchema] = Field(description="Types de lieux avec compteur")


# ════════════════════════════════════════════════════════════════
# SYNCHRONISATION MOBILE
# ════════════════════════════════════════════════════════════════

class SyncStatusResponse(BaseModel):
    server_time: str = Field(description="Timestamp ISO 8601 actuel du serveur", examples=["2026-06-03T14:30:00+00:00"])
    collections: dict[str, Optional[str]] = Field(
        description="Dernier timestamp de modification par collection",
        examples=[{"regions": "2026-05-01T10:00:00+00:00", "communes": "2026-06-01T08:30:00+00:00"}]
    )

class SyncChangesResponse(BaseModel):
    since: str = Field(description="Timestamp de reference fourni", examples=["2026-05-01T00:00:00Z"])
    server_time: str = Field(description="Timestamp ISO 8601 actuel du serveur", examples=["2026-06-03T14:30:00+00:00"])
    changes: dict[str, list[dict]] = Field(description="Documents modifies ou crees par collection")

class SyncFullResponse(BaseModel):
    server_time: str = Field(description="Timestamp ISO 8601 actuel du serveur", examples=["2026-06-03T14:30:00+00:00"])
    data: dict[str, list[dict]] = Field(description="Integralite des donnees par collection")


# ════════════════════════════════════════════════════════════════
# AUTHENTIFICATION — API KEYS
# ════════════════════════════════════════════════════════════════

class APIKeyCreateRequest(BaseModel):
    """Corps de la requete pour creer une cle API"""
    nom: str = Field(description="Nom descriptif du client", examples=["App Mobile v1", "Partenaire MINTP"])

class APIKeyCreateResponse(BaseModel):
    """Reponse apres creation d'une cle API (cle en clair, affichee une seule fois)"""
    key: str = Field(description="Cle API en clair — A COPIER IMMEDIATEMENT", examples=["ak_aBcDeFgHiJkLmNoPqRsTuVwXyZ012345678"])
    key_prefix: str = Field(description="Prefixe pour identification", examples=["ak_aBcDeFgHi"])
    nom: str = Field(description="Nom du client", examples=["App Mobile v1"])
    id: str = Field(description="Identifiant MongoDB de la cle")
    message: str = Field(
        default="Cle creee avec succes. Conservez-la precieusement, elle ne sera plus affichee.",
        description="Message d'avertissement"
    )

class APIKeyListItem(BaseModel):
    """Element de la liste des cles API (sans le hash)"""
    id: str = Field(description="Identifiant MongoDB")
    key_prefix: str = Field(description="Prefixe de la cle", examples=["ak_aBcDeFgHi"])
    nom: str = Field(description="Nom du client", examples=["App Mobile v1"])
    active: bool = Field(description="Cle active ou revoquee", examples=[True])
    created_at: Optional[str] = Field(default=None, description="Date de creation ISO 8601")
    last_used_at: Optional[str] = Field(default=None, description="Derniere utilisation ISO 8601")

class APIKeyListResponse(BaseModel):
    """Liste des cles API enregistrees"""
    total: int = Field(description="Nombre total de cles", examples=[3])
    api_keys: List[APIKeyListItem]