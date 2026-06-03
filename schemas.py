# schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

# ════════════════════════════════════════════════════════════════
# MODÈLES PARTAGÉS
# ════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Structure standard retournée en cas d'erreur (400, 404, 500)"""
    detail: str = Field(
        description="Message d'erreur explicite indiquant la cause du problème",
        examples=["ID invalide : '123'.", "Le fichier doit etre au format CSV (.csv)."]
    )

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
    statut: str = Field(
        description="Statut de l'operation pour cette commune", 
        examples=["existante", "nouvelle", "erreur"]
    )
    commune: str = Field(description="Nom de la commune traitee", examples=["Ngaoundere I"])
    id_commune: str = Field(description="Identifiant MongoDB de la commune")
    sous_documents: Dict[str, int] = Field(
        description="Nombre de sous-documents inseres par categorie",
        examples=[{"villages": 3, "chefferies": 2, "ethnies": 0, "marches": 2, "lieux": 4, "cooperatives": 0}]
    )

class ImportReportResponse(BaseModel):
    """Rapport complet retourne apres un import CSV"""
    total: int = Field(description="Nombre total de lignes traitees dans le CSV", examples=[2])
    succes: int = Field(description="Nombre de communes importees avec succes", examples=[2])
    erreurs: int = Field(description="Nombre de lignes rejetees", examples=[0])
    details: List[ImportDetailItem] = Field(description="Detail ligne par ligne de l'import")
# ════════════════════════════════════════════════════════════════
# HIÉRARCHIE GÉOGRAPHIQUE
# ════════════════════════════════════════════════════════════════

class RegionItem(BaseModel):
    # Configuration pour gérer l'alias _id proprement
    model_config = ConfigDict(populate_by_name=True, by_alias=True)
    
    # Le champ s'appelle "id" en Python, mais s'affichera comme "_id" dans le JSON
    id: str = Field(alias="_id", description="Identifiant MongoDB de la region")
    nom: str = Field(description="Nom de la region", examples=["Centre"])
    nb_departements: int = Field(description="Nombre de departements dans cette region", examples=[10])

class RegionsListResponse(BaseModel):
    total: int = Field(description="Nombre total de regions", examples=[10])
    regions: List[RegionItem]

class RegionDetailResponse(BaseModel):
    region: Dict[str, Any] = Field(description="Details complets de la region")
    departements: List[Dict[str, Any]] = Field(description="Liste des departements de cette region avec nb_arrondissements")

class DepartementDetailResponse(BaseModel):
    departement: Dict[str, Any] = Field(description="Details complets du departement")
    arrondissements: List[Dict[str, Any]] = Field(description="Liste des arrondissements avec nb_communes")

class ArrondissementDetailResponse(BaseModel):
    arrondissement: Dict[str, Any] = Field(description="Details complets de l'arrondissement")
    communes: List[Dict[str, Any]] = Field(description="Liste des communes (infos principales)")

# ════════════════════════════════════════════════════════════════
# COMMUNES & LIEUX
# ════════════════════════════════════════════════════════════════

class CommuneListItem(BaseModel):
    commune: Dict[str, Any] = Field(description="Donnees de la commune")
    region: Optional[str] = Field(default=None, description="Nom de la region", examples=["Centre"])
    departement: Optional[str] = Field(default=None, description="Nom du departement", examples=["Mfoundi"])
    arrondissement: Optional[str] = Field(default=None, description="Nom de l'arrondissement", examples=["Yaounde I"])

class CommunesListResponse(BaseModel):
    total: int = Field(description="Nombre total de communes trouvees", examples=[360])
    communes: List[CommuneListItem]

class CommuneDetailResponse(BaseModel):
    commune: Dict[str, Any] = Field(description="Donnees completes de la commune")
    hierarchie: Dict[str, Optional[Dict[str, Any]]] = Field(description="Objet contenant region, departement, arrondissement")
    villages: List[Dict[str, Any]] = Field(description="Liste des villages lies")
    chefferies: List[Dict[str, Any]] = Field(description="Liste des chefferies liees")
    ethnies: List[Dict[str, Any]] = Field(description="Liste des ethnies liees")
    marches: List[Dict[str, Any]] = Field(description="Liste des marches lies")
    lieux: List[Dict[str, Any]] = Field(description="Liste des lieux lies")
    cooperatives: List[Dict[str, Any]] = Field(description="Liste des cooperatives liees")
    exercices: List[Dict[str, Any]] = Field(description="Liste des exercices lies")

class SousDocumentListResponse(BaseModel):
    total: int = Field(description="Nombre total d'elements", examples=[50])
    data: List[Dict[str, Any]] = Field(description="Liste des documents")

class LieuxTypesResponse(BaseModel):
    types: List[Dict[str, Any]] = Field(
        description="Liste des types de lieux avec leur compteur",
        examples=[{"type": "scolaire", "count": 150}, {"type": "urgence", "count": 45}]
    )

# ════════════════════════════════════════════════════════════════
# SYNCHRONISATION MOBILE
# ════════════════════════════════════════════════════════════════

class SyncStatusResponse(BaseModel):
    server_time: str = Field(description="Timestamp ISO 8601 actuel du serveur", examples=["2026-06-03T14:30:00+00:00"])
    collections: Dict[str, Optional[str]] = Field(
        description="Dernier timestamp de modification (updated_at) par collection",
        examples=[{"regions": "2026-05-01T10:00:00+00:00", "communes": "2026-06-01T08:30:00+00:00"}]
    )

class SyncChangesResponse(BaseModel):
    since: str = Field(description="Timestamp de reference fourni dans la requete", examples=["2026-05-01T00:00:00Z"])
    server_time: str = Field(description="Timestamp ISO 8601 actuel du serveur", examples=["2026-06-03T14:30:00+00:00"])
    changes: Dict[str, List[Dict[str, Any]]] = Field(description="Documents modifies ou crees par collection")

class SyncFullResponse(BaseModel):
    server_time: str = Field(description="Timestamp ISO 8601 actuel du serveur", examples=["2026-06-03T14:30:00+00:00"])
    data: Dict[str, List[Dict[str, Any]]] = Field(description="Integralite des donnees par collection")