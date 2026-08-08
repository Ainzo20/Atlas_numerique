# Atlas Numérique du Cameroun

Plateforme web d'importation, de structuration et de diffusion publique des données géographiques et administratives du Cameroun, collectées via KoboCollect. Comprend une carte interactive, une consultation publique des données par catégorie, et un espace d'administration protégé pour l'import de données.

---

## Table des matières

- [Contexte](#contexte)
- [Stack technique](#stack-technique)
- [Architecture du projet](#architecture-du-projet)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Modèle d'authentification](#modèle-dauthentification)
- [Prérequis](#prérequis)
- [Installation locale](#installation-locale)
- [Configuration (.env)](#configuration-env)
- [Création du premier compte admin](#création-du-premier-compte-admin)
- [Lancement](#lancement)
- [Utilisation](#utilisation)
- [Structure des données](#structure-des-données)
- [Format CSV attendu](#format-csv-attendu)
- [Données GeoJSON](#données-geojson)
- [Déploiement sur Render](#déploiement-sur-render)
- [Limites connues](#limites-connues)
- [Feuille de route](#feuille-de-route)
- [Contribuer](#contribuer)

---

## Contexte

Les données géographiques sur les localités du Cameroun sont collectées sur le terrain via des fiches papier remplies par les mairies, saisies dans **KoboCollect**, qui génère des fichiers CSV en sortie.

Ce projet fournit :
1. Un **backend FastAPI** qui lit ces fichiers CSV, restructure les données selon la hiérarchie administrative du Cameroun, les insère dans MongoDB, et les diffuse publiquement via une API REST.
2. Une **interface web** avec carte interactive (Leaflet), permettant à tout visiteur de consulter/filtrer les données, et à un administrateur authentifié d'importer de nouveaux fichiers CSV.

Le site web est **public en lecture** — n'importe quel visiteur peut consulter la carte, rechercher, filtrer et voir les détails des communes/lieux/régions. Seul l'**import de données** est réservé aux comptes administrateurs.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Backend / API | Python 3.11+ — FastAPI |
| Authentification | JWT (PyJWT) + hachage bcrypt (module `bcrypt`, sans `passlib`) |
| Parsing CSV | pandas |
| Base de données | MongoDB (pymongo) |
| Instance BD (test) | MongoDB Atlas — tier gratuit (512MB) |
| Frontend | HTML + CSS + JavaScript vanilla (modules ES6) |
| Carte interactive | Leaflet.js + couches GeoJSON |
| Hébergement (test) | Render.com — tier gratuit |
| Versionning | GitHub |

---

## Architecture du projet

```
atlas-cameroun/
├── main.py                # Point d'entree FastAPI — definition des routes
├── auth.py                 # Authentification : hachage mdp, JWT, dependances FastAPI
├── parser.py                # Lecture, nettoyage et transformation du CSV
├── database.py              # Connexion MongoDB et operations CRUD
├── models.py                 # Structures des collections MongoDB (dont make_user)
├── config.py                  # Chargement et validation des variables d'environnement
├── create_admin.py             # Script CLI de creation d'un compte administrateur
├── static/
│   ├── index.html            # Coquille HTML : topbar + sidebar + conteneur #app
│   ├── login.html             # Page de connexion admin
│   ├── css/
│   │   ├── base.css             # Variables :root, reset, typographie
│   │   ├── layout.css            # Topbar, sidebar, structure de page
│   │   ├── composants.css        # Cartes, tableaux, modal, boutons, fiches
│   │   ├── carte.css              # Tooltips Leaflet, panneau lateral
│   │   └── responsive.css         # Media queries (mobile/desktop)
│   ├── js/
│   │   ├── core/
│   │   │   ├── auth.js              # Session JWT cookie (login/logout/checkSession)
│   │   │   ├── api.js                # Tous les appels fetch() centralises
│   │   │   ├── ui-state.js           # Affichage topbar selon etat de connexion
│   │   │   └── router.js             # Routeur cote client (history.pushState)
│   │   ├── components/
│   │   │   ├── carte.js               # Leaflet : polygones regions, marqueurs, panneau
│   │   │   ├── panneau-lateral.js      # Panneau escamotable generique
│   │   │   ├── fiche-item.js           # Carte visuelle reutilisable (grilles)
│   │   │   └── sidebar.js               # Navigation laterale generee dynamiquement
│   │   ├── pages/
│   │   │   ├── carte-page.js             # Page d'accueil "/"
│   │   │   ├── pages-tableau.js           # Regions, communes, villages, lieux, etc.
│   │   │   └── import.js                   # Page d'import CSV (admin)
│   │   └── main.js                          # Point d'entree : routes + init
│   └── geojson/
│       ├── regions.geojson                # Polygones regions (WGS84)
│       └── districts.geojson               # Polygones districts (WGS84, pas encore utilise)
├── requirements.txt        # Dependances Python
├── .env                     # Variables d'environnement (JAMAIS commite)
├── .gitignore
└── README.md
```

### Backend

Application FastAPI classique avec séparation claire des responsabilités :

- **`main.py`** — déclaration des routes uniquement, délègue la logique métier
- **`auth.py`** — toute la logique d'authentification : hachage de mots de passe (bcrypt direct, sans passlib), création/décodage de JWT, dépendances FastAPI (`exiger_admin` pour protéger une route, `get_utilisateur_optionnel` pour une route publique qui s'adapte sans bloquer)
- **`database.py`** — connexion MongoDB (pattern singleton), fonctions génériques d'insertion/recherche (`trouver_ou_creer` évite les doublons dans la hiérarchie administrative)
- **`models.py`** — fonctions `make_*()` qui construisent les documents MongoDB (aucune logique métier, uniquement des structures)
- **`config.py`** — lecture centralisée des variables `.env`, lève une erreur claire si une variable requise est absente

**Toutes les routes de lecture sont publiques** (`/regions`, `/communes`, `/lieux`, `/sync/*`, etc.) — aucune authentification requise. Seule la route `/import` est protégée par `Depends(exiger_admin)`.

### Frontend

Architecture modulaire par responsabilité, remplaçant l'ancien `app.js` monolithique :

- **`core/`** — briques transverses réutilisées partout : appels API, état d'authentification, routage
- **`components/`** — éléments d'interface réutilisables sur plusieurs pages (carte Leaflet, panneau latéral, fiche visuelle générique, sidebar)
- **`pages/`** — une fonction par page, appelée par le routeur, qui remplit `#app`

**Navigation par URL réelle** (pas de simple changement de classe CSS) : `router.js` utilise `history.pushState()`, ce qui permet le bouton retour du navigateur et des liens directs vers une page précise.

**Carte interactive** : Leaflet.js, centrée sur le Cameroun, affiche les polygones de régions (survol → tooltip avec nom/population) et des marqueurs pour chaque commune (clic → panneau latéral avec détails complets : GPS, contacts, villages/lieux rattachés, langues locales).

---

## Modèle d'authentification

Le système d'authentification a été entièrement repensé pour abandonner l'ancien mécanisme de clé API générée par script (jugé trop risqué à opérer : clé transmise à la main, aucune rotation, aucun compte nommé).

**Modèle actuel** : compte utilisateur (`username` + mot de passe haché) stocké dans la collection MongoDB `users`, session basée sur un **JWT signé**, transmis via un cookie `atlas_session` (`httponly`, `secure`, `samesite=lax`).

### Fonctionnement

1. L'administrateur se connecte via `/login` avec `username` + mot de passe
2. Le backend vérifie les identifiants (`authentifier_utilisateur()` dans `auth.py`), compare le mot de passe au hash bcrypt stocké
3. Si valide, un JWT est généré (`creer_token_session()`) contenant `sub` (username), `role`, `exp` (expiration), `iat` (émission)
4. Le token est posé dans un cookie `atlas_session`
5. Chaque requête vers une route protégée décode ce cookie via `exiger_admin()` ; chaque requête vers une route publique adaptative (ex: `/api/me`) utilise `get_utilisateur_optionnel()`, qui ne bloque jamais

### Rôles

Un seul rôle actif actuellement : `admin`. Le champ `role` dans le document utilisateur est prévu pour être étendu plus tard (ex: `editeur`) sans changement de `auth.py` — seule la vérification dans `exiger_admin()` évoluerait.

### Sécurité — points d'attention

- **`JWT_SECRET`** doit être une chaîne aléatoire longue, différente entre dev/prod, jamais commitée
- En cas de fuite du secret ou d'un cookie de session, régénérer immédiatement `JWT_SECRET` invalide toutes les sessions actives (pas de révocation individuelle de token pour l'instant — amélioration possible future via une table `sessions_revoquees` ou un `jti`)
- Le hachage utilise `bcrypt` **directement**, sans `passlib` — `passlib` (non maintenu depuis 2020) est incompatible avec `bcrypt >= 4.1`

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

Dépendances clés pour l'authentification :
```
bcrypt
pyjwt
```

---

## Configuration (.env)

Créer un fichier `.env` à la racine du projet avec les variables suivantes :

```env
# MongoDB
MONGODB_URI=mongodb+srv://<utilisateur>:<motdepasse>@<cluster>.mongodb.net/
MONGODB_DB=atlas_cameroun

# Authentification JWT
JWT_SECRET=<chaine_aleatoire_longue>
JWT_EXPIRE_MINUTES=480
```

### Génération de `JWT_SECRET`

Ne jamais choisir cette valeur à la main. La générer aléatoirement :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copier le résultat tel quel dans `.env`.

| Variable | Obligatoire | Description |
|---|---|---|
| `MONGODB_URI` | Oui | URI de connexion MongoDB (Atlas ou local) |
| `MONGODB_DB` | Oui | Nom de la base de données |
| `JWT_SECRET` | Oui | Clé de signature des tokens JWT — aléatoire, longue, jamais commitée |
| `JWT_EXPIRE_MINUTES` | Non (défaut : 480, soit 8h) | Durée de validité d'une session admin avant reconnexion requise |

> **Important** : `.env` ne doit **jamais** être commité. Vérifier qu'il figure bien dans `.gitignore`, ainsi que tout fichier pouvant contenir un cookie/token de session (ex: `cookies.txt` généré par des tests `curl`).
>
> En cas de fuite accidentelle d'un secret ou d'un fichier de cookies dans l'historique git : régénérer immédiatement `JWT_SECRET`, et purger l'historique git (`git filter-repo` ou réinitialisation de l'historique), pas seulement supprimer le fichier du dernier commit.

---

## Création du premier compte admin

Il n'existe plus de script de génération de clé API. Un compte administrateur se crée via :

```bash
python3 create_admin.py
```

Le script demande un `username` et un mot de passe (saisie masquée via `getpass`), hache le mot de passe avec bcrypt, et insère le document dans la collection `users`. Il vérifie que le `username` n'existe pas déjà avant insertion.

---

## Lancement

```bash
uvicorn main:app --reload
```

L'application est accessible sur : `http://localhost:8000`

- `/` — carte interactive (accès public)
- `/login` — connexion administrateur
- `/import` — import CSV (accès admin uniquement, via navigation authentifiée)

---

## Utilisation

### Consultation publique (aucune authentification requise)

- Carte interactive : survol des régions (tooltip avec population), clic sur une commune (panneau latéral avec détails complets)
- Navigation par la barre latérale : régions, communes, villages, lieux, chefferies, marchés, ethnies, coopératives, exercices
- Export CSV/Excel des données

### Import d'un fichier CSV (administrateur)

1. Se connecter via `/login`
2. Cliquer sur **"Importer"** dans la topbar (visible uniquement une fois connecté)
3. Sélectionner le fichier CSV exporté depuis KoboCollect
4. Consulter le rapport d'import (communes importées, erreurs éventuelles)

---

## Structure des données

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

users               # Comptes administrateurs (username, hashed_password, role, is_active)
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

> **Point de vigilance qualité des données** : des coordonnées GPS incorrectes ont été observées sur certaines communes importées (valeurs valides mais géographiquement erronées, probablement liées à une erreur de saisie terrain). Un script de validation/détection d'anomalies GPS à l'import est à prévoir (feuille de route).

---

## Données GeoJSON

Les polygones de limites administratives (`static/geojson/regions.geojson`, `districts.geojson`) proviennent de sources externes et doivent être reprojetés avant utilisation.

- **Format attendu par Leaflet** : WGS84 (EPSG:4326) — latitude/longitude standards
- **Format source courant** (GADM, exports SIG) : souvent EPSG:3857 (Web Mercator, coordonnées en mètres) — **incompatible tel quel**
- **Conversion** : via [mapshaper.org](https://mapshaper.org) (commande `-proj wgs84` dans la console) ou tout outil équivalent, à faire une seule fois par fichier, jamais côté client à l'exécution
- **Correspondance de noms** : le champ `properties.region` (ou `NAME`) du GeoJSON doit correspondre exactement au nom stocké dans MongoDB (`hierarchie.region`) pour permettre la mise en relation

`districts.geojson` est converti et présent mais **pas encore intégré** dans `carte.js` (seul `regions.geojson` est chargé actuellement).

---

## Déploiement sur Render

### 1. Pousser le code sur GitHub

```bash
git add .
git commit -m "description du changement"
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
MONGODB_URI          = mongodb+srv://...
MONGODB_DB           = atlas_cameroun
JWT_SECRET           = <valeur generee, differente de celle du dev local>
JWT_EXPIRE_MINUTES   = 480
```

> Sans `JWT_SECRET` défini sur Render, le déploiement plantera au démarrage (`config.py` lève une erreur bloquante si la variable est absente).

### 4. Déployer

Render détecte automatiquement chaque push sur `main` et redéploie.

---

## Limites connues

| Limite | Détail |
|---|---|
| MongoDB Atlas gratuit — 512MB | Suffisant pour les tests. En production, prévoir un abonnement payant ou un serveur propre avec MongoDB installé. |
| Render gratuit — mise en veille | L'instance s'endort après 15 minutes d'inactivité. Le premier chargement après inactivité prend ~30 secondes. |
| `districts.geojson` non utilisé | Converti et présent mais pas encore chargé dans `carte.js`. |
| Sous-types des lieux | Les sous-types ne sont pas dans le CSV. Ils doivent être enrichis manuellement via l'interface après import. |
| Chefferies — ancien format KoboCollect | L'ancien CSV KoboCollect limite à 3 chefferies par commune. Le nouveau format proposé (séparateur `\|`) lève cette limite. |
| Révocation de session individuelle | Impossible actuellement de révoquer un seul token JWT sans régénérer `JWT_SECRET` (ce qui invalide toutes les sessions). |
| Contenu descriptif des régions | `models.py` ne stocke actuellement aucun champ narratif (climat, culture, description) pour les régions/communes — uniquement des données structurées. Extension prévue avec le futur CRUD. |
| Données GPS non validées à l'import | Aucune vérification de cohérence géographique des coordonnées saisies (des erreurs de saisie terrain peuvent produire des points valides mais mal placés). |

---

## Feuille de route

- [ ] CRUD administrateur (créer/modifier/supprimer communes, lieux, régions...), protégé par `exiger_admin`
- [ ] Enrichissement du modèle région/commune avec des champs descriptifs (climat, culture, économie, image) pour un rendu encyclopédique de l'atlas
- [ ] Navigation hiérarchique centrée sur la carte (clic région → recentrage/isolement de la vue sur cette région, puis départements, puis communes)
- [ ] Marqueurs différenciés par catégorie sur la carte (villages, lieux, chefferies, marchés — actuellement seules les communes sont affichées)
- [ ] Filtres sur les pages de consultation (par région, par type) pour rester lisible à mesure que le volume de données augmente
- [ ] Recherche globale côté client (nom de commune/lieu/région → résultat), sans nouvel endpoint dédié dans un premier temps
- [ ] Intégration de `districts.geojson` (actuellement converti mais non utilisé)
- [ ] Script de validation des coordonnées GPS à l'import
- [ ] Layout admin séparé (`/admin/*`)
- [ ] Nettoyage du code frontend legacy restant (dashboard et certaines fonctions de l'ancien `app.js` pas encore migrées vers le routeur)

---

## Contribuer

1. Forker le dépôt
2. Créer une branche : `git checkout -b feature/nom-de-la-feature`
3. Commiter les changements : `git commit -m "description claire"`
4. Pousser : `git push origin feature/nom-de-la-feature`
5. Ouvrir une Pull Request

---

> Documentation complète de l'API disponible via Swagger UI, à `/docs` une fois l'application lancée.
