# Atlas Numérique du Cameroun — Documentation de l'API

Cette documentation technique présente de manière détaillée l'ensemble des points d'accès (endpoints) de l'API de l'**Atlas Numérique du Cameroun**. Elle permet à tout développeur d'intégrer l'API ou de concevoir des clients (web, mobiles, etc.) compatibles.

L'API est développée en **FastAPI** et s'interface avec une base de données **MongoDB**.

---

## 1. Informations Générales & Protocoles

### URL de Base
* **Développement local** : `http://localhost:8000`
* **Production** : (Se référer à l'URL de déploiement, ex. sur Render.com)

### En-têtes HTTP Recommandés
Pour toutes les requêtes retournant ou consommant du JSON, il est fortement recommandé de spécifier l'en-tête suivant :
```http
Accept: application/json
```

Pour les endpoints de type modification ou envoi de fichiers (`POST /import`), l'en-tête de contenu suivant est obligatoire et géré automatiquement par les clients HTTP lors de l'upload :
```http
Content-Type: multipart/form-data
```

### Authentification
Pour le moment, l'API ne dispose pas de couche d'authentification active. Toutes les requêtes de consultation et d'import/export sont publiques.

---

## 2. Structure Standard des Réponses d'Erreur

Toutes les erreurs générées par l'API (codes de statut `400`, `404`, `500`) suivent le format standard défini ci-dessous :

**Schéma JSON (`ErrorResponse`) :**
```json
{
  "detail": "Message d'erreur décrivant le problème rencontré."
}
```

* **400 Bad Request** : Paramètre invalide, format de données incorrect (ex. ID MongoDB invalide ou format de fichier CSV non pris en charge).
* **404 Not Found** : Ressource demandée introuvable en base de données.
* **500 Internal Server Error** : Problème au niveau du serveur ou de la connexion à la base de données.

---

## 3. Liste Détaillée des Points d'Accès (Endpoints)

```mermaid
graph TD
    subgraph Sante & Stats
        H[GET /health]
        ST[GET /stats]
    end
    subgraph Import & Export
        IM[POST /import]
        EX[GET /export]
    end
    subgraph Hiérarchie Administrative
        R[GET /regions]
        RD[GET /regions/{id}]
        D[GET /departements/{id}]
        A[GET /arrondissements/{id}]
    end
    subgraph Communes & Lieux
        C[GET /communes]
        CD[GET /communes/{id}]
        SD[GET /villages, /chefferies, /marches...]
        L[GET /lieux]
        LT[GET /lieux/types]
    end
    subgraph Synchronisation Mobile
        SS[GET /sync/status]
        SC[GET /sync/changes]
        SF[GET /sync/full]
    end
```

### 3.1. Monitoring & Statistiques

#### `GET /health`
* **Description** : Vérifie l'état de fonctionnement de l'application et la connexion à la base de données MongoDB (route essentielle pour les pings de monitoring).
* **Tags** : `Sante & Stats`
* **En-têtes** : `Accept: application/json`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/health" -H "Accept: application/json"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "statut": "en ligne",
    "mongodb": "connecte",
    "base_de_donnees": "atlas_cameroun"
  }
  ```

---

#### `GET /stats`
* **Description** : Retourne les statistiques d'occupation de la base de données sous forme de décompte de documents pour chaque collection.
* **Tags** : `Sante & Stats`
* **En-têtes** : `Accept: application/json`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/stats" -H "Accept: application/json"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "regions": 10,
    "departements": 58,
    "arrondissements": 360,
    "communes": 360,
    "villages": 5000,
    "chefferies": 500,
    "ethnies": 250,
    "marches": 1200,
    "lieux": 8000,
    "cooperatives": 300,
    "exercices": 1000
  }
  ```

---

### 3.2. Importation & Exportation

#### `POST /import`
* **Description** : Reçoit un fichier CSV KoboCollect, parse son contenu et distribue les enregistrements dans les collections MongoDB appropriées.
* **Tags** : `Import & Export`
* **En-têtes requis** :
  * `Content-Type: multipart/form-data`
* **Corps de requête (Body - Form-Data)** :
  * `fichier` : (fichier binaire) Fichier CSV KoboCollect à téléverser.
* **Exemple d'appel** :
  ```bash
  curl -X POST "http://localhost:8000/import" \
    -F "fichier=@chemin/vers/mon_fichier.csv"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "total": 2,
    "succes": 2,
    "erreurs": 0,
    "details": [
      {
        "statut": "nouvelle",
        "commune": "Ngaoundéré I",
        "id_commune": "60d5ec49f1b2c8b1f8e4e1a2",
        "sous_documents": {
          "villages": 4,
          "chefferies": 2,
          "ethnies": 1,
          "marches": 2,
          "lieux": 5,
          "cooperatives": 1,
          "exercices": 1
        }
      }
    ]
  }
  ```
* **Codes d'erreur spécifiques** :
  * **400 Bad Request** : Fichier n'ayant pas l'extension `.csv` ou mal formaté.
  * **500 Internal Server Error** : Impossible de lire le fichier ou erreur de base de données.

---

#### `GET /export`
* **Description** : Génère et exporte les données consolidées des communes au format CSV ou Excel.
* **Tags** : `Import & Export`
* **Paramètres de requête (Query)** :
  * `format` *(string, optionnel, défaut : `"csv"`)* : Format d'export désiré. Valeurs acceptées : `"csv"`, `"excel"`.
  * `region` *(string, optionnel)* : Filtre l'export sur une région spécifique (ex. `"Littoral"`, recherche insensible à la casse).
* **En-têtes de réponse générés** :
  * Si CSV :
    * `Content-Type: text/csv`
    * `Content-Disposition: attachment; filename=communes_export.csv`
  * Si Excel :
    * `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
    * `Content-Disposition: attachment; filename=communes_export.xlsx`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/export?format=excel&region=Centre" --output communes_centre.xlsx
  ```
* **Codes d'erreur spécifiques** :
  * **400 Bad Request** : Format d'export invalide.
  * **404 Not Found** : Aucune commune trouvée pour le filtre spécifié.

---

### 3.3. Hiérarchie Administrative

#### `GET /regions`
* **Description** : Liste l'intégralité des régions avec, pour chacune d'elles, le nombre total de départements rattachés.
* **Tags** : `Hierarchie`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/regions"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "total": 10,
    "regions": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e1a0",
        "nom": "Centre",
        "nb_departements": 10
      },
      {
        "_id": "60d5ec49f1b2c8b1f8e4e1a1",
        "nom": "Littoral",
        "nb_departements": 4
      }
    ]
  }
  ```

---

#### `GET /regions/{id_region}`
* **Description** : Fournit le détail complet d'une région ainsi que la liste de tous ses départements associés (avec le nombre d'arrondissements par département).
* **Tags** : `Hierarchie`
* **Paramètres de chemin (Path)** :
  * `id_region` *(string, requis)* : Identifiant unique de la région (ObjectId MongoDB de 24 caractères hexadécimaux).
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/regions/60d5ec49f1b2c8b1f8e4e1a0"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "region": {
      "_id": "60d5ec49f1b2c8b1f8e4e1a0",
      "nom": "Centre",
      "geometrie": null,
      "superficie": 38950,
      "population": 4200000,
      "capitale": "Yaoundé",
      "chef_region": "Gouverneur X",
      "date_creation": null
    },
    "departements": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e2b0",
        "nom": "Mfoundi",
        "id_region": "60d5ec49f1b2c8b1f8e4e1a0",
        "nb_arrondissements": 7
      }
    ]
  }
  ```

---

#### `GET /departements/{id_departement}`
* **Description** : Fournit le détail d'un département ainsi que la liste de ses arrondissements (avec le nombre de communes par arrondissement).
* **Tags** : `Hierarchie`
* **Paramètres de chemin (Path)** :
  * `id_departement` *(string, requis)* : Identifiant unique du département (ObjectId MongoDB).
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/departements/60d5ec49f1b2c8b1f8e4e2b0"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "departement": {
      "_id": "60d5ec49f1b2c8b1f8e4e2b0",
      "nom": "Mfoundi",
      "id_region": "60d5ec49f1b2c8b1f8e4e1a0",
      "geometrie": null,
      "superficie": 297,
      "population": 2500000,
      "chef_departement": "Préfet Y",
      "code_postal": "8000"
    },
    "arrondissements": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e3c0",
        "nom": "Yaoundé I",
        "id_departement": "60d5ec49f1b2c8b1f8e4e2b0",
        "nb_communes": 1
      }
    ]
  }
  ```

---

#### `GET /arrondissements/{id_arrondissement}`
* **Description** : Fournit le détail d'un arrondissement ainsi que la liste résumée des communes qui y sont localisées.
* **Tags** : `Hierarchie`
* **Paramètres de chemin (Path)** :
  * `id_arrondissement` *(string, requis)* : Identifiant unique de l'arrondissement (ObjectId MongoDB).
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/arrondissements/60d5ec49f1b2c8b1f8e4e3c0"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "arrondissement": {
      "_id": "60d5ec49f1b2c8b1f8e4e3c0",
      "nom": "Yaoundé I",
      "id_departement": "60d5ec49f1b2c8b1f8e4e2b0"
    },
    "communes": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e4d0",
        "nom": "Yaoundé I",
        "coordonnees": {
          "latitude": 3.8666,
          "longitude": 11.5166,
          "altitude": 750.0,
          "precision": 5.0
        },
        "connectivite_constante": true,
        "contact_mairie": {
          "telephones": ["+237699999999"],
          "mails": ["mairie@yaounde1.cm"],
          "code_postal": "00237"
        },
        "langues_locales": ["Ewondo", "Eton"]
      }
    ]
  }
  ```

---

### 3.4. Communes & Lieux

#### `GET /communes`
* **Description** : Liste toutes les communes de l'Atlas. Permet des filtres optionnels combinables par région ou par département (recherche par expressions régulières insensible à la casse). Chaque commune retournée inclut le nom de son arrondissement, département et région pour affichage direct.
* **Tags** : `Communes & Lieux`
* **Paramètres de requête (Query)** :
  * `region` *(string, optionnel)* : Filtrer par nom de région (ex. `"Littoral"`).
  * `departement` *(string, optionnel)* : Filtrer par nom de département (ex. `"Wouri"`).
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/communes?region=Centre&departement=Mfoundi"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "total": 1,
    "communes": [
      {
        "commune": {
          "_id": "60d5ec49f1b2c8b1f8e4e4d0",
          "nom": "Yaoundé I",
          "id_arrondissement": "60d5ec49f1b2c8b1f8e4e3c0",
          "coordonnees": {
            "latitude": 3.8666,
            "longitude": 11.5166,
            "altitude": 750.0,
            "precision": 5.0
          },
          "connectivite_constante": true,
          "contact_mairie": {
            "telephones": ["+237699999999"],
            "mails": ["mairie@yaounde1.cm"],
            "code_postal": "00237"
          },
          "langues_locales": ["Ewondo", "Eton"]
        },
        "region": "Centre",
        "departement": "Mfoundi",
        "arrondissement": "Yaoundé I"
      }
    ]
  }
  ```

---

#### `GET /communes/{id_commune}`
* **Description** : Renvoie les détails complets d'une commune avec sa hiérarchie ascendante résolue ainsi que l'ensemble des sous-documents associés (villages, chefferies, ethnies, marchés, lieux d'intérêt, coopératives, exercices annuels).
* **Tags** : `Communes & Lieux`
* **Paramètres de chemin (Path)** :
  * `id_commune` *(string, requis)* : Identifiant MongoDB de la commune.
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/communes/60d5ec49f1b2c8b1f8e4e4d0"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "commune": {
      "_id": "60d5ec49f1b2c8b1f8e4e4d0",
      "nom": "Yaoundé I",
      "id_arrondissement": "60d5ec49f1b2c8b1f8e4e3c0",
      "contact_mairie": {
        "telephones": ["+237699999999"],
        "mails": ["mairie@yaounde1.cm"],
        "code_postal": "00237"
      },
      "contact_personne_ressource": {
        "nom": "Jean Etoa",
        "role": "Chef Service Technique",
        "telephones": ["+237677777777"],
        "mails": ["j.etoa@mail.cm"],
        "code_postal": null
      },
      "coordonnees": {
        "latitude": 3.8666,
        "longitude": 11.5166,
        "altitude": 750.0,
        "precision": 5.0
      },
      "langues_locales": ["Ewondo", "Eton"],
      "delegations_ministeres": ["MINAT", "MINDUH"],
      "agriculture_artisanat": ["Maraîchage", "Artisanat d'art"],
      "image_url": "http://localhost:8000/static/uploads/yaounde1.jpg",
      "gare_voyageurs": [
        {"nom": "Gare routière de Nlongkak", "latitude": 3.882, "longitude": 11.515}
      ],
      "connectivite_constante": true,
      "villages_non_connectes": [],
      "lien_etranger": false,
      "pays_etrangers": [],
      "autres_informations": "Zone urbaine dense",
      "kobocollect_uuid": "f2a893db-0000-1111-2222-333344445555",
      "submitted_by": "Agent_01",
      "submission_time": "2026-06-01T10:00:00"
    },
    "hierarchie": {
      "arrondissement": {
        "_id": "60d5ec49f1b2c8b1f8e4e3c0",
        "nom": "Yaoundé I",
        "id_departement": "60d5ec49f1b2c8b1f8e4e2b0"
      },
      "departement": {
        "_id": "60d5ec49f1b2c8b1f8e4e2b0",
        "nom": "Mfoundi",
        "id_region": "60d5ec49f1b2c8b1f8e4e1a0"
      },
      "region": {
        "_id": "60d5ec49f1b2c8b1f8e4e1a0",
        "nom": "Centre"
      }
    },
    "villages": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5e0",
        "nom": "Nlongkak",
        "type": "quartier",
        "chef": "M. Atangana",
        "population": 15000,
        "superficie": null,
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ],
    "chefferies": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5f0",
        "nom": "Chefferie de 3e degré de Nlongkak",
        "latitude": 3.882,
        "longitude": 11.518,
        "altitude": 745.0,
        "precision": 4.0,
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ],
    "ethnies": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5a0",
        "nom": "Ewondo",
        "salutations": "Mbege",
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ],
    "marches": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5b0",
        "nom": "Marché de Nlongkak",
        "jour": "Mardi | Vendredi",
        "heure_debut": "07:00",
        "heure_fin": "18:00",
        "description": "Marché de vivres frais",
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ],
    "lieux": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5c0",
        "nom": "Lycée de Waldji",
        "type_nom": "scolaire",
        "sous_type_id": null,
        "description": null,
        "coordonnees": {"latitude": 3.89, "longitude": 11.52},
        "image_url": null,
        "heure_ouverture": null,
        "heure_fermeture": null,
        "contact": null,
        "condition_acces": null,
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ],
    "cooperatives": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5d0",
        "nom": "GIC Maraîchers du Mfoundi",
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ],
    "exercices": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5e1",
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0",
        "maire": "M. Mbarga",
        "budget_annuel": 500000000,
        "annee": "2025",
        "nombre_habitants": 320000,
        "taux_electrification": 85.5,
        "taux_connectivite": 70.0,
        "villages_non_electrifies": ["Village X", "Village Y"],
        "besoins_technologiques": ["Adduction d'eau", "Couverture internet 4G"]
      }
    ]
  }
  ```

---

#### `GET /villages`, `GET /chefferies`, `GET /ethnies`, `GET /marches`, `GET /cooperatives`, `GET /exercices`
* **Description** : Routes utilitaires simplifiées permettant de lister à plat les enregistrements de chaque catégorie. Elles supportent toutes le filtre par identifiant de commune.
* **Tags** : `Communes & Lieux`
* **Paramètres de requête (Query)** :
  * `id_commune` *(string, optionnel)* : Identifiant unique de la commune pour filtrer la liste.
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/marches?id_commune=60d5ec49f1b2c8b1f8e4e4d0"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "total": 1,
    "data": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5b0",
        "nom": "Marché de Nlongkak",
        "jour": "Mardi | Vendredi",
        "heure_debut": "07:00",
        "heure_fin": "18:00",
        "description": "Marché de vivres frais",
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ]
  }
  ```

---

#### `GET /lieux/types`
* **Description** : Regroupe et compte les lieux d'intérêt (Points d'Intérêt) enregistrés en base par type (ex. scolaire, religieux, urgence, eau, etc.). Utile pour alimenter des filtres d'affichage.
* **Tags** : `Communes & Lieux`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/lieux/types"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "types": [
      { "type": "scolaire", "count": 150 },
      { "type": "religieux", "count": 110 },
      { "type": "eau", "count": 80 },
      { "type": "reference", "count": 60 },
      { "type": "urgence", "count": 45 },
      { "type": "touristique", "count": 30 },
      { "type": "sportif", "count": 25 }
    ]
  }
  ```

---

#### `GET /lieux`
* **Description** : Permet de lister tous les lieux d'intérêt avec filtres de sélection optionnels combinables.
* **Tags** : `Communes & Lieux`
* **Paramètres de requête (Query)** :
  * `id_commune` *(string, optionnel)* : ID unique de la commune.
  * `type_lieu` *(string, optionnel)* : Type de lieu à filtrer (ex. `"scolaire"`, recherche insensible à la casse).
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/lieux?type_lieu=scolaire"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "total": 1,
    "data": [
      {
        "_id": "60d5ec49f1b2c8b1f8e4e5c0",
        "nom": "Lycée de Waldji",
        "type_nom": "scolaire",
        "sous_type_id": null,
        "description": "Lycée d'enseignement secondaire public",
        "coordonnees": {
          "latitude": 3.89,
          "longitude": 11.52
        },
        "image_url": null,
        "heure_ouverture": null,
        "heure_fermeture": null,
        "contact": null,
        "condition_acces": "Gratuit",
        "id_commune": "60d5ec49f1b2c8b1f8e4e4d0"
      }
    ]
  }
  ```

---

### 3.5. Synchronisation Mobile (Offline-First)

L'API de l'Atlas Numérique propose des endpoints optimisés pour les applications mobiles nécessitant de fonctionner hors-ligne (offline-first).

#### Workflow de Synchronisation Mobile recommandé :
1. **Premier démarrage (Initialisation)** :
   * L'application mobile télécharge l'intégralité de la base de données via :
     `GET /sync/full`
   * Elle stocke localement l'heure du serveur retournée dans le champ `server_time` (ex. `2026-06-03T14:30:00+00:00`).
2. **Vérification ultérieure des mises à jour** :
   * Régulièrement (ou lors d'une action manuelle), le mobile interroge :
     `GET /sync/status`
   * Il compare les timestamps de ses collections locales avec les timestamps retournés par le serveur.
3. **Mise à jour incrémentale** :
   * Si un décalage est identifié, le mobile appelle l'endpoint suivant en passant son dernier timestamp stocké dans le paramètre `since` :
     `GET /sync/changes?since=VOTRE_TIMESTAMP_LOCAL`
   * Le mobile applique les modifications reçues dans sa base locale SQLite/Realm et met à jour son timestamp de référence avec le nouveau `server_time` fourni par la réponse.

---

#### `GET /sync/status`
* **Description** : Récupère la date de la dernière modification (`updated_at`) pour chacune des collections de données géographiques et administratives, ainsi que l'heure courante du serveur.
* **Tags** : `Sync Mobile`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/sync/status"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "server_time": "2026-06-03T14:30:00+00:00",
    "collections": {
      "regions": "2026-05-01T10:00:00+00:00",
      "departements": "2026-05-01T10:15:00+00:00",
      "arrondissements": "2026-05-01T10:30:00+00:00",
      "communes": "2026-06-01T08:30:00+00:00",
      "villages": "2026-06-01T08:31:00+00:00",
      "chefferies": "2026-06-01T08:32:00+00:00",
      "ethnies": "2026-06-01T08:33:00+00:00",
      "marches": "2026-06-01T08:34:00+00:00",
      "lieux": "2026-06-01T08:35:00+00:00",
      "cooperatives": "2026-06-01T08:36:00+00:00",
      "exercices": "2026-06-01T08:37:00+00:00"
    }
  }
  ```

---

#### `GET /sync/changes`
* **Description** : Retourne uniquement les documents qui ont été créés ou mis à jour dans l'une des collections depuis le timestamp ISO 8601 fourni dans le paramètre `since`.
* **Tags** : `Sync Mobile`
* **Paramètres de requête (Query)** :
  * `since` *(string, requis)* : Date de référence au format ISO 8601 (ex. `2026-06-01T00:00:00Z` ou `2026-06-01T14:30:00+01:00`).
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/sync/changes?since=2026-06-01T00:00:00Z"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "since": "2026-06-01T00:00:00Z",
    "server_time": "2026-06-03T14:30:00+00:00",
    "changes": {
      "regions": [],
      "departements": [],
      "arrondissements": [],
      "communes": [
        {
          "_id": "60d5ec49f1b2c8b1f8e4e4d0",
          "nom": "Yaoundé I",
          "id_arrondissement": "60d5ec49f1b2c8b1f8e4e3c0",
          "created_at": "2026-05-15T09:00:00+00:00",
          "updated_at": "2026-06-01T08:30:00+00:00",
          "coordonnees": {
            "latitude": 3.8666,
            "longitude": 11.5166,
            "altitude": 750.0,
            "precision": 5.0
          },
          "connectivite_constante": true
        }
      ],
      "villages": [],
      "chefferies": [],
      "ethnies": [],
      "marches": [],
      "lieux": [],
      "cooperatives": [],
      "exercices": []
    }
  }
  ```
* **Codes d'erreur spécifiques** :
  * **400 Bad Request** : Format de timestamp invalide.

---

#### `GET /sync/full`
* **Description** : Renvoie l'intégralité des données géographiques et administratives de toutes les collections sous un format plat optimisé pour l'initialisation du terminal client.
* **Tags** : `Sync Mobile`
* **Exemple d'appel** :
  ```bash
  curl -X GET "http://localhost:8000/sync/full"
  ```
* **Réponse type (200 OK)** :
  ```json
  {
    "server_time": "2026-06-03T14:30:00+00:00",
    "data": {
      "regions": [
        {
          "_id": "60d5ec49f1b2c8b1f8e4e1a0",
          "nom": "Centre",
          "created_at": "2026-05-01T10:00:00+00:00",
          "updated_at": "2026-05-01T10:00:00+00:00"
        }
      ],
      "departements": [
        {
          "_id": "60d5ec49f1b2c8b1f8e4e2b0",
          "nom": "Mfoundi",
          "id_region": "60d5ec49f1b2c8b1f8e4e1a0",
          "created_at": "2026-05-01T10:15:00+00:00",
          "updated_at": "2026-05-01T10:15:00+00:00"
        }
      ],
      "arrondissements": [],
      "communes": [],
      "villages": [],
      "chefferies": [],
      "ethnies": [],
      "marches": [],
      "lieux": [],
      "cooperatives": [],
      "exercices": []
    }
  }
  ```
