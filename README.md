# Atlas Numérique du Cameroun — Importateur KoboCollect → MongoDB

Outil d'importation et de structuration des données géographiques collectées via KoboCollect vers une base de données MongoDB. Inclut une interface web simple pour l'import, la visualisation et l'export des données.

---

## Table des matières

- [Contexte](#contexte)
- [Stack technique](#stack-technique)
- [Architecture du projet](#architecture-du-projet)
- [Prérequis](#prérequis)
- [Installation locale](#installation-locale)
- [Configuration](#configuration)
- [Lancement](#lancement)
- [Utilisation](#utilisation)
- [Structure des données](#structure-des-données)
- [Format CSV attendu](#format-csv-attendu)
- [Déploiement sur Render](#déploiement-sur-render)
- [Limites connues](#limites-connues)
- [Contribuer](#contribuer)

---

## Contexte

Les données géographiques sur les localités du Cameroun sont collectées sur le terrain via des fiches papier remplies par les mairies. Ces fiches sont ensuite saisies dans **KoboCollect**, qui génère des fichiers CSV en sortie.

Ce projet fournit :
1. Un **script Python** qui lit ces fichiers CSV, éclate et restructure les données selon la hiérarchie administrative du Cameroun, puis les insère dans MongoDB.
2. Une **interface web** (HTML/CSS/JS) qui permet à un agent d'importer un CSV en un seul clic, de visualiser les données importées et d'exporter des rapports CSV/Excel.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Backend / API | Python 3.11+ — FastAPI |
| Parsing CSV | pandas |
| Base de données | MongoDB (pymongo) |
| Instance BD (test) | MongoDB Atlas — tier gratuit (512MB) |
| Frontend | HTML + CSS + JavaScript vanilla |
| Hébergement (test) | Render.com — tier gratuit |
| Versionning | GitHub |

---

## Architecture du projet

```
atlas-cameroun/
├── main.py              # Point d'entrée FastAPI — définition des routes
├── parser.py            # Lecture, nettoyage et transformation du CSV
├── database.py          # Connexion MongoDB et opérations CRUD
├── models.py            # Structures des collections MongoDB
├── static/
│   ├── index.html       # Interface web
│   ├── style.css        # Styles
│   └── app.js           # Logique frontend (upload, affichage, export)
├── requirements.txt     # Dépendances Python
├── .env.example         # Template des variables d'environnement
├── .gitignore
└── README.md
```

---

## Prérequis

- Python 3.11 ou supérieur
- pip
- Un compte [MongoDB Atlas](https://www.mongodb.com/atlas) (gratuit)
- Un compte [Render.com](https://render.com) (gratuit) — pour le déploiement
- Git

---

## Installation locale

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-utilisateur/atlas-cameroun.git
cd atlas-cameroun
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Copier le fichier d'environnement

```bash
cp .env.example .env
```

### 2. Remplir le fichier `.env`

```env
MONGODB_URI=mongodb+srv://<utilisateur>:<motdepasse>@<cluster>.mongodb.net/
MONGODB_DB=atlas_cameroun
```

> **Important** : Ne jamais commiter le fichier `.env`. Il est déjà dans le `.gitignore`.

---

## Lancement

```bash
uvicorn main:app --reload
```

L'application est accessible sur : `http://localhost:8000`

---

## Utilisation

### Import d'un fichier CSV

1. Ouvrir l'interface web sur `http://localhost:8000`
2. Cliquer sur **"Importer un fichier CSV"**
3. Sélectionner le fichier CSV exporté depuis KoboCollect
4. Cliquer sur **"Lancer l'import"**
5. Consulter le rapport d'import affiché (communes importées, erreurs éventuelles)

### Visualisation des données

- Le tableau de bord affiche les communes importées
- Filtres disponibles : par Région, par Département
- Chaque commune affiche ses informations principales

### Export des données

- Cliquer sur **"Exporter CSV"** ou **"Exporter Excel"**
- Choisir le périmètre : toutes les données, par région ou par département

---

## Structure des données

Les données sont organisées selon la hiérarchie administrative du Cameroun et stockées dans les collections MongoDB suivantes :

```
regions
  └── departements          (ref: id_region)
        └── arrondissements     (ref: id_departement)
              └── communes            (ref: id_arrondissement)
                    ├── villages_quartiers    (ref: id_commune)
                    ├── chefferies            (ref: id_commune)
                    ├── ethnies               (ref: id_commune)
                    ├── jours_marche          (ref: id_commune)
                    ├── lieux                 (ref: id_commune, type_id)
                    ├── cooperatives          (ref: id_commune)
                    └── exercices             (ref: id_commune)
```

### Collections de référence

```
types           # Types de lieux (scolaire, urgence, touristique, etc.)
sous_types      # Sous-types liés à un type (enrichissement manuel)
types_commune   # Types de communes (rurale, urbaine, etc.)
```

---

## Format CSV attendu

### Paramètres généraux

| Paramètre | Valeur |
|---|---|
| Encodage | UTF-8 |
| Séparateur de colonnes | `;` (point-virgule) |
| Séparateur valeurs multiples | `\|` (pipe) |
| Séparateur attributs internes | `::` (double deux-points) |

### Convention pour les champs multi-valeurs

**Villages** — séparés par `|`
```
Baladji|Dang|Ngaoundere Centre|Burkina
```

**Chefferies** — `nom::latitude::longitude::altitude::precision` séparés par `|`
```
Lamido Vina::7.3229::13.5842::1104::3|Chefferie Beka::7.2901::13.5621::1098::5
```

**Marchés** — `nom::jour::heure_debut::heure_fin` séparés par `|`
```
Grand Marche::Lundi::06:00::18:00|Marche Beka::Vendredi::07:00::17:00
```

### Colonnes requises

| Colonne | Collection cible |
|---|---|
| `Region` | regions |
| `Departement` | departements |
| `Arrondissement` | arrondissements |
| `Contact de la mairie` | communes |
| `Contact personne ressource` | communes |
| `Quartiers ou villages` | villages_quartiers |
| `Zone entierement electrifiee?` | exercices |
| `Si non, lister les villages electrifies` | exercices |
| `Langues locales` | communes |
| `Points religieux` | lieux (type: religieux) |
| `Points de reference` | lieux (type: reference) |
| `Sites touristiques` | lieux (type: touristique) |
| `GPS latitude / longitude / altitude / precision` | communes |
| `Ethnies` | ethnies |
| `Chefferies` | chefferies |
| `Ecoles et types` | lieux (type: scolaire) |
| `Delegations des ministeres` | communes |
| `Marches et jours` | jours_marche |
| `Urgences` | lieux (type: urgence) |
| `Points d eau` | lieux (type: eau) |
| `Agriculture/artisanat` | communes |
| `Infrastructures sportives` | lieux (type: sportif) |
| `Image URL` | communes |
| `Gare voyageurs` | communes |
| `Cooperatives, GIC` | cooperatives |
| `Connectivite internet` | communes |
| `Villages non connectes` | communes |
| `Lien pays etrangers` | communes |
| `Pays etrangers` | communes |
| `Nombre habitants` | exercices |
| `Besoins technologiques` | exercices |
| `Autres informations` | communes |
| `_uuid` | communes (tracabilite) |
| `_submitted_by` | communes (tracabilite) |
| `_submission_time` | communes (tracabilite) |

### Colonnes ignorées (métadonnées KoboCollect internes)

`start`, `end`, `_id`, `_validation_status`, `_notes`, `_status`, `__version__`, `_tags`, `_index`, `Votre avis sur l'application`

---

## Déploiement sur Render

### 1. Pousser le code sur GitHub

```bash
git add .
git commit -m "initial commit"
git push origin main
```

### 2. Créer un Web Service sur Render

- Aller sur [render.com](https://render.com) → **New** → **Web Service**
- Connecter le dépôt GitHub
- Configurer :

| Paramètre | Valeur |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port 10000` |

### 3. Ajouter les variables d'environnement sur Render

Dans **Environment** → **Add Environment Variable** :

```
MONGODB_URI   =  mongodb+srv://...
MONGODB_DB    =  atlas_cameroun
```

### 4. Déployer

Render détecte automatiquement chaque push sur `main` et redéploie.

---

## Limites connues

| Limite | Détail |
|---|---|
| MongoDB Atlas gratuit — 512MB | Suffisant pour les tests. En production, prévoir un abonnement payant ou un serveur propre avec MongoDB installé. |
| Render gratuit — mise en veille | L'instance s'endort après 15 minutes d'inactivité. Le premier chargement après inactivité prend ~30 secondes. |
| Géométries GeoJSON absentes | Les contours géographiques (régions, départements) ne proviennent pas du CSV KoboCollect. Ils doivent être fournis séparément pour activer la carte interactive. |
| Sous-types des lieux | Les sous-types ne sont pas dans le CSV. Ils doivent être enrichis manuellement via l'interface après import. |
| Chefferies — ancien format KoboCollect | L'ancien CSV KoboCollect limite à 3 chefferies par commune. Le nouveau format proposé (séparateur `\|`) lève cette limite. |

---

## Contribuer

1. Forker le dépôt
2. Créer une branche : `git checkout -b feature/nom-de-la-feature`
3. Commiter les changements : `git commit -m "description claire"`
4. Pousser : `git push origin feature/nom-de-la-feature`
5. Ouvrir une Pull Request

---

> Document technique complet disponible dans `/docs/doc_technique_atlas.pdf`