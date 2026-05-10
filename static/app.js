/**
 * app.js — Atlas Numérique du Cameroun
 * -------------------------------------
 * Organisation :
 * 1.  Configuration
 * 2.  Navigation
 * 3.  Santé & Stats
 * 4.  Import CSV
 * 5.  Régions
 * 6.  Communes
 * 7.  Villages & Quartiers
 * 8.  Lieux
 * 9.  Chefferies
 * 10. Marchés
 * 11. Ethnies
 * 12. Coopératives
 * 13. Exercices
 * 14. Export
 * 15. Modal commune
 * 16. Utilitaires
 * 17. Initialisation
 */


// ════════════════════════════════════════════════════════════════
// 1. CONFIGURATION
// ════════════════════════════════════════════════════════════════

const API = "";

let fichierSelectionne  = null;
let toutesLesCommunes   = [];
let tousLesVillages     = [];
let tousLesLieux        = [];


// ════════════════════════════════════════════════════════════════
// 2. NAVIGATION
// ════════════════════════════════════════════════════════════════

/**
 * Change la page active et charge les données correspondantes.
 * @param {string} page - Identifiant de la page
 */
function naviguer(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  document.getElementById(`page-${page}`).classList.add("active");

  const navItem = document.querySelector(`[data-page="${page}"]`);
  if (navItem) navItem.classList.add("active");

  // Réinitialiser les icônes Feather après le changement de page
  feather.replace();

  switch (page) {
    case "dashboard":    chargerDashboard();    break;
    case "regions":      chargerRegions();      break;
    case "communes":     chargerCommunes();     break;
    case "villages":     chargerVillages();     break;
    case "lieux":        chargerLieux();        break;
    case "chefferies":   chargerChefferies();   break;
    case "marches":      chargerMarches();      break;
    case "ethnies":      chargerEthnies();      break;
    case "cooperatives": chargerCooperatives(); break;
    case "exercices":    chargerExercices();    break;
  }
}


// ════════════════════════════════════════════════════════════════
// 3. SANTE & STATS
// ════════════════════════════════════════════════════════════════

/**
 * Vérifie la connexion MongoDB et met à jour l'indicateur sidebar.
 */
async function verifierSante() {
  const dot  = document.getElementById("statusDot");
  const text = document.getElementById("statusText");

  try {
    const res  = await fetch(`${API}/health`);
    const data = await res.json();

    if (data.mongodb === "connecte") {
      dot.className    = "status-dot ok";
      text.textContent = "MongoDB connecté";
    } else {
      dot.className    = "status-dot error";
      text.textContent = "MongoDB déconnecté";
    }
  } catch {
    dot.className    = "status-dot error";
    text.textContent = "Hors ligne";
  }
}

/**
 * Charge les statistiques globales et les affiche dans les stat-cards.
 */
async function chargerStats() {
  try {
    const res  = await fetch(`${API}/stats`);
    const data = await res.json();

    const mapping = {
      "stat-regions":         "regions",
      "stat-departements":    "departements",
      "stat-arrondissements": "arrondissements",
      "stat-communes":        "communes",
      "stat-villages":        "villages",
      "stat-lieux":           "lieux",
      "stat-chefferies":      "chefferies",
      "stat-marches":         "marches",
      "stat-ethnies":         "ethnies",
      "stat-cooperatives":    "cooperatives",
      "stat-exercices":       "exercices",
    };

    Object.entries(mapping).forEach(([id, cle]) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = data[cle] ?? "0";
        el.closest(".stat-card")?.classList.remove("loading");
      }
    });

  } catch {
    document.querySelectorAll(".stat-value").forEach(el => {
      el.textContent = "—";
    });
  }
}

/**
 * Charge le dashboard : stats + aperçu des communes.
 */
async function chargerDashboard() {
  chargerStats();

  try {
    const res  = await fetch(`${API}/communes`);
    const data = await res.json();
    const container = document.getElementById("dashboardCommunes");

    if (!data.communes || data.communes.length === 0) {
      container.innerHTML = vueVide("home", "Aucune commune", "Importez un fichier CSV pour commencer.");
      return;
    }

    container.innerHTML = data.communes.slice(0, 8).map(item => `
      <div class="commune-preview-card"
           onclick="ouvrirModal('${item.commune._id}')">
        <div class="commune-preview-nom">${item.commune.nom}</div>
        <div class="commune-preview-loc">
          ${item.region || "—"} · ${item.departement || "—"}
        </div>
      </div>
    `).join("");

  } catch {
    document.getElementById("dashboardCommunes").innerHTML =
      vueVide("alert-circle", "Erreur", "Impossible de charger les communes.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 4. IMPORT CSV
// ════════════════════════════════════════════════════════════════

/**
 * Gère le drop de fichier.
 * @param {DragEvent} event
 */
function handleDrop(event) {
  event.preventDefault();
  document.getElementById("dropZone").classList.remove("drag-over");
  const fichier = event.dataTransfer.files[0];
  if (fichier) selectionnerFichier(fichier);
}

/**
 * Gère la sélection via le bouton Parcourir.
 * @param {Event} event
 */
function handleFileSelect(event) {
  const fichier = event.target.files[0];
  if (fichier) selectionnerFichier(fichier);
}

/**
 * Enregistre le fichier sélectionné et affiche ses informations.
 * @param {File} fichier
 */
function selectionnerFichier(fichier) {
  if (!fichier.name.endsWith(".csv")) {
    alert("Le fichier doit être au format .csv");
    return;
  }

  fichierSelectionne = fichier;

  document.getElementById("dropZone").style.display     = "none";
  document.getElementById("fileSelected").style.display = "flex";
  document.getElementById("importRapport").style.display = "none";
  document.getElementById("fileName").textContent = fichier.name;
  document.getElementById("fileSize").textContent =
    `${(fichier.size / 1024).toFixed(1)} Ko`;

  feather.replace();
}

/**
 * Annule la sélection du fichier.
 */
function annulerFichier() {
  fichierSelectionne = null;
  document.getElementById("dropZone").style.display      = "block";
  document.getElementById("fileSelected").style.display  = "none";
  document.getElementById("importProgress").style.display = "none";
  document.getElementById("importRapport").style.display  = "none";
  document.getElementById("csvInput").value = "";
  feather.replace();
}

/**
 * Lance l'import du fichier CSV vers l'API.
 */
async function lancerImport() {
  if (!fichierSelectionne) return;

  document.getElementById("fileSelected").style.display   = "none";
  document.getElementById("importProgress").style.display = "flex";
  document.getElementById("importRapport").style.display  = "none";

  const formData = new FormData();
  formData.append("fichier", fichierSelectionne);

  try {
    const res  = await fetch(`${API}/import`, { method: "POST", body: formData });
    const data = await res.json();

    document.getElementById("importProgress").style.display = "none";
    afficherRapport(data, res.ok);

    fichierSelectionne = null;
    document.getElementById("csvInput").value = "";

  } catch (erreur) {
    document.getElementById("importProgress").style.display = "none";
    afficherRapport({ message: erreur.message }, false);
  }

  feather.replace();
}

/**
 * Affiche le rapport d'import.
 * @param {object}  data   - Données retournées par l'API
 * @param {boolean} succes - True si la requête a réussi
 */
function afficherRapport(data, succes) {
  const el = document.getElementById("importRapport");
  el.style.display = "block";

  if (!succes || data.detail) {
    el.className = "import-rapport rapport-erreur";
    el.innerHTML = `
      <div class="rapport-title" style="color:var(--red-light)">
        Erreur d'import
      </div>
      <div class="rapport-stat">
        <span>Message</span>
        <span>${data.detail || data.message || "Erreur inconnue"}</span>
      </div>
    `;
    return;
  }

  el.className = "import-rapport rapport-succes";
  el.innerHTML = `
    <div class="rapport-title" style="color:var(--green-light)">
      Import terminé
    </div>
    <div class="rapport-stat">
      <span>Communes traitées</span><span>${data.total}</span>
    </div>
    <div class="rapport-stat">
      <span>Succès</span><span>${data.succes}</span>
    </div>
    <div class="rapport-stat">
      <span>Erreurs</span><span>${data.erreurs}</span>
    </div>
    ${(data.details || []).filter(d => d.statut === "erreur").map(d => `
      <div class="rapport-stat" style="color:var(--red-light)">
        <span>${d.commune}</span><span>${d.message}</span>
      </div>
    `).join("")}
  `;

  chargerStats();
}


// ════════════════════════════════════════════════════════════════
// 5. REGIONS
// ════════════════════════════════════════════════════════════════

/**
 * Charge et affiche toutes les régions.
 */
async function chargerRegions() {
  const container = document.getElementById("regionsContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/regions`);
    const data = await res.json();

    if (!data.regions || data.regions.length === 0) {
      container.innerHTML = vueVide("map", "Aucune région", "Importez un fichier CSV pour commencer.");
      feather.replace();
      return;
    }

    container.innerHTML = `<div class="regions-grid">` +
      data.regions.map(region => `
        <div class="region-card" onclick="ouvrirRegion('${region._id}')">
          <div class="region-nom">${region.nom}</div>
          <div class="region-meta">
            <i data-feather="flag"></i>
            ${region.nb_departements} département${region.nb_departements > 1 ? "s" : ""}
          </div>
          <span class="region-badge">
            <i data-feather="arrow-right"></i> Voir les détails
          </span>
        </div>
      `).join("") + `</div>`;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les régions.");
  }

  feather.replace();
}

/**
 * Ouvre le détail d'une région dans la modal.
 * @param {string} idRegion
 */
async function ouvrirRegion(idRegion) {
  const modal = document.getElementById("modalContent");
  modal.innerHTML = chargementHTML();
  document.getElementById("modalOverlay").classList.add("open");

  try {
    const res  = await fetch(`${API}/regions/${idRegion}`);
    const data = await res.json();
    const r    = data.region;

    modal.innerHTML = `
      <div class="modal-commune-header">
        <div class="modal-commune-nom">${r.nom}</div>
        <div class="modal-commune-loc">Région</div>
      </div>
      <div class="modal-section">
        <div class="modal-section-title">
          <i data-feather="flag"></i> Départements (${data.departements.length})
        </div>
        <ul class="modal-list">
          ${data.departements.map(d => `
            <li>
              <span>${d.nom}</span>
              <span style="margin-left:auto;color:var(--text-3);font-size:0.7rem">
                ${d.nb_arrondissements} arrondissement${d.nb_arrondissements > 1 ? "s" : ""}
              </span>
            </li>
          `).join("") || "<li>Aucun département</li>"}
        </ul>
      </div>
    `;

  } catch {
    modal.innerHTML = `<p style="color:var(--red-light);text-align:center;padding:2rem">Erreur de chargement.</p>`;
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 6. COMMUNES
// ════════════════════════════════════════════════════════════════

/**
 * Charge toutes les communes et les affiche dans un tableau.
 */
async function chargerCommunes() {
  const container = document.getElementById("communesContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/communes`);
    const data = await res.json();

    toutesLesCommunes = data.communes || [];
    afficherTableauCommunes(toutesLesCommunes);

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les communes.");
    feather.replace();
  }
}

/**
 * Affiche les communes dans un tableau HTML.
 * @param {Array} communes
 */
function afficherTableauCommunes(communes) {
  const container = document.getElementById("communesContent");

  if (communes.length === 0) {
    container.innerHTML = vueVide("home", "Aucun résultat", "Essayez d'autres filtres.");
    feather.replace();
    return;
  }

  container.innerHTML = `
    <div class="data-table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Commune</th>
            <th>Région</th>
            <th>Département</th>
            <th>Arrondissement</th>
            <th>Connectivité</th>
            <th>Langues</th>
          </tr>
        </thead>
        <tbody>
          ${communes.map(item => `
            <tr onclick="ouvrirModal('${item.commune._id}')">
              <td class="cell-primary">${item.commune.nom}</td>
              <td>${item.region || "—"}</td>
              <td>${item.departement || "—"}</td>
              <td>${item.arrondissement || "—"}</td>
              <td>
                <span class="badge ${item.commune.connectivite_constante ? 'badge-green' : 'badge-red'}">
                  ${item.commune.connectivite_constante ? "Oui" : "Non"}
                </span>
              </td>
              <td>${(item.commune.langues_locales || []).slice(0, 2).join(", ") || "—"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;

  feather.replace();
}

/**
 * Filtre les communes localement (sans appel API).
 */
function filtrerCommunes() {
  const region = document.getElementById("filtreRegion").value.toLowerCase().trim();
  const dept   = document.getElementById("filtreDept").value.toLowerCase().trim();

  const filtrees = toutesLesCommunes.filter(item => {
    const matchRegion = !region || (item.region || "").toLowerCase().includes(region);
    const matchDept   = !dept   || (item.departement || "").toLowerCase().includes(dept);
    return matchRegion && matchDept;
  });

  afficherTableauCommunes(filtrees);
}

/**
 * Réinitialise les filtres communes.
 */
function reinitialiserFiltres() {
  document.getElementById("filtreRegion").value = "";
  document.getElementById("filtreDept").value   = "";
  afficherTableauCommunes(toutesLesCommunes);
}


// ════════════════════════════════════════════════════════════════
// 7. VILLAGES & QUARTIERS
// ════════════════════════════════════════════════════════════════

/**
 * Charge tous les villages et quartiers avec filtre optionnel par type.
 */
async function chargerVillages() {
  const container = document.getElementById("villagesContent");
  container.innerHTML = chargementHTML();

  const type = document.getElementById("filtreTypeVillage")?.value || "";

  try {
    const res  = await fetch(`${API}/villages`);
    const data = await res.json();

    tousLesVillages = data.villages || [];

    const filtres = type
      ? tousLesVillages.filter(v => v.type === type)
      : tousLesVillages;

    if (filtres.length === 0) {
      container.innerHTML = vueVide("map-pin", "Aucun résultat", "Aucun village ou quartier trouvé.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Type</th>
              <th>Chef</th>
              <th>Population</th>
              <th>Superficie (km²)</th>
            </tr>
          </thead>
          <tbody>
            ${filtres.map(v => `
              <tr>
                <td class="cell-primary">${v.nom}</td>
                <td>
                  <span class="badge badge-${v.type || 'grey'}">
                    ${capitaliser(v.type || "—")}
                  </span>
                </td>
                <td>${v.chef || "—"}</td>
                <td>${v.population ?? "—"}</td>
                <td>${v.superficie ?? "—"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les villages.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 8. LIEUX
// ════════════════════════════════════════════════════════════════

/**
 * Charge tous les lieux avec filtre optionnel par type.
 */
async function chargerLieux() {
  const container = document.getElementById("lieuxContent");
  container.innerHTML = chargementHTML();

  const type = document.getElementById("filtreTypeLieu")?.value || "";
  const url  = type ? `${API}/lieux?type_lieu=${encodeURIComponent(type)}` : `${API}/lieux`;

  try {
    const res  = await fetch(url);
    const data = await res.json();

    const lieux = data.lieux || [];

    if (lieux.length === 0) {
      container.innerHTML = vueVide("layers", "Aucun lieu", "Aucun lieu trouvé pour ce type.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Type</th>
              <th>Latitude</th>
              <th>Longitude</th>
              <th>Contact</th>
            </tr>
          </thead>
          <tbody>
            ${lieux.map(l => `
              <tr>
                <td class="cell-primary">${l.nom}</td>
                <td>
                  <span class="badge badge-${l.type_nom || 'grey'}">
                    ${capitaliser(l.type_nom || "—")}
                  </span>
                </td>
                <td class="cell-mono">
                  ${l.coordonnees?.latitude ?? "—"}
                </td>
                <td class="cell-mono">
                  ${l.coordonnees?.longitude ?? "—"}
                </td>
                <td>${l.contact || "—"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les lieux.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 9. CHEFFERIES
// ════════════════════════════════════════════════════════════════

/**
 * Charge toutes les chefferies.
 */
async function chargerChefferies() {
  const container = document.getElementById("chefferiesContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/chefferies`);
    const data = await res.json();

    const chefferies = data.chefferies || [];

    if (chefferies.length === 0) {
      container.innerHTML = vueVide("shield", "Aucune chefferie", "Aucune chefferie enregistrée.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Latitude</th>
              <th>Longitude</th>
              <th>Altitude (m)</th>
              <th>Précision GPS</th>
            </tr>
          </thead>
          <tbody>
            ${chefferies.map(c => `
              <tr>
                <td class="cell-primary">${c.nom}</td>
                <td class="cell-mono">${c.latitude  ?? "—"}</td>
                <td class="cell-mono">${c.longitude ?? "—"}</td>
                <td class="cell-mono">${c.altitude  ?? "—"}</td>
                <td class="cell-mono">${c.precision ?? "—"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les chefferies.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 10. MARCHES
// ════════════════════════════════════════════════════════════════

/**
 * Charge tous les marchés.
 */
async function chargerMarches() {
  const container = document.getElementById("marchesContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/marches`);
    const data = await res.json();

    const marches = data.marches || [];

    if (marches.length === 0) {
      container.innerHTML = vueVide("shopping-bag", "Aucun marché", "Aucun marché enregistré.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Jour</th>
              <th>Ouverture</th>
              <th>Fermeture</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            ${marches.map(m => `
              <tr>
                <td class="cell-primary">${m.nom}</td>
                <td>
                  <span class="badge badge-yellow">${m.jour || "—"}</span>
                </td>
                <td>${m.heure_debut || "—"}</td>
                <td>${m.heure_fin   || "—"}</td>
                <td>${m.description || "—"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les marchés.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 11. ETHNIES
// ════════════════════════════════════════════════════════════════

/**
 * Charge toutes les ethnies.
 */
async function chargerEthnies() {
  const container = document.getElementById("ethniesContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/ethnies`);
    const data = await res.json();

    const ethnies = data.ethnies || [];

    if (ethnies.length === 0) {
      container.innerHTML = vueVide("users", "Aucune ethnie", "Aucune ethnie enregistrée.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Ethnie</th>
              <th>Salutations locales</th>
            </tr>
          </thead>
          <tbody>
            ${ethnies.map(e => `
              <tr>
                <td class="cell-primary">${e.nom}</td>
                <td>${e.salutations || "—"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les ethnies.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 12. COOPERATIVES
// ════════════════════════════════════════════════════════════════

/**
 * Charge toutes les coopératives et GIC.
 */
async function chargerCooperatives() {
  const container = document.getElementById("cooperativesContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/cooperatives`);
    const data = await res.json();

    const cooperatives = data.cooperatives || [];

    if (cooperatives.length === 0) {
      container.innerHTML = vueVide("briefcase", "Aucune coopérative", "Aucune coopérative enregistrée.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Commune (ID)</th>
            </tr>
          </thead>
          <tbody>
            ${cooperatives.map(c => `
              <tr>
                <td class="cell-primary">${c.nom}</td>
                <td class="cell-mono">${c.id_commune}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les coopératives.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 13. EXERCICES
// ════════════════════════════════════════════════════════════════

/**
 * Charge tous les exercices annuels.
 */
async function chargerExercices() {
  const container = document.getElementById("exercicesContent");
  container.innerHTML = chargementHTML();

  try {
    const res  = await fetch(`${API}/exercices`);
    const data = await res.json();

    const exercices = data.exercices || [];

    if (exercices.length === 0) {
      container.innerHTML = vueVide("bar-chart-2", "Aucun exercice", "Aucun exercice enregistré.");
      feather.replace();
      return;
    }

    container.innerHTML = `
      <div class="data-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Année</th>
              <th>Habitants</th>
              <th>Électrification</th>
              <th>Connectivité</th>
              <th>Besoins technologiques</th>
            </tr>
          </thead>
          <tbody>
            ${exercices.map(e => `
              <tr>
                <td class="cell-primary">${e.annee || "—"}</td>
                <td>${e.nombre_habitants?.toLocaleString("fr-FR") ?? "—"}</td>
                <td>
                  <span class="badge ${e.taux_electrification === 100 ? 'badge-green' : 'badge-yellow'}">
                    ${e.taux_electrification !== null && e.taux_electrification !== undefined
                      ? e.taux_electrification + "%"
                      : "—"}
                  </span>
                </td>
                <td>
                  ${e.taux_connectivite !== null && e.taux_connectivite !== undefined
                    ? `<span class="badge badge-green">${e.taux_connectivite}%</span>`
                    : "—"}
                </td>
                <td>
                  ${(e.besoins_technologiques || []).slice(0, 2).join(", ") || "—"}
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

  } catch {
    container.innerHTML = vueVide("alert-circle", "Erreur", "Impossible de charger les exercices.");
  }

  feather.replace();
}


// ════════════════════════════════════════════════════════════════
// 14. EXPORT
// ════════════════════════════════════════════════════════════════

/**
 * Déclenche le téléchargement de l'export CSV ou Excel.
 * @param {string} format - 'csv' ou 'excel'
 */
function exporter(format) {
  const region = document.getElementById("exportRegion").value.trim();
  let url = `${API}/export?format=${format}`;
  if (region) url += `&region=${encodeURIComponent(region)}`;

  const lien = document.createElement("a");
  lien.href = url;
  lien.download = format === "csv" ? "communes_export.csv" : "communes_export.xlsx";
  document.body.appendChild(lien);
  lien.click();
  document.body.removeChild(lien);
}


// ════════════════════════════════════════════════════════════════
// 15. MODAL COMMUNE
// ════════════════════════════════════════════════════════════════

/**
 * Ouvre la modal avec les détails complets d'une commune.
 * @param {string} idCommune - ID MongoDB de la commune
 */
async function ouvrirModal(idCommune) {
  const modal = document.getElementById("modalContent");
  modal.innerHTML = chargementHTML();
  document.getElementById("modalOverlay").classList.add("open");

  try {
    const res  = await fetch(`${API}/communes/${idCommune}`);
    const data = await res.json();

    const c   = data.commune;
    const h   = data.hierarchie;
    const cm  = c.contact_mairie || {};
    const cr  = c.contact_personne_ressource || {};
    const gps = c.coordonnees || {};

    modal.innerHTML = `

      <div class="modal-commune-header">
        <div class="modal-commune-nom">${c.nom}</div>
        <div class="modal-commune-loc">
          <i data-feather="map-pin"></i>
          ${h.region?.nom || "—"} · ${h.departement?.nom || "—"} · ${h.arrondissement?.nom || "—"}
        </div>
      </div>

      <!-- Contacts -->
      <div class="modal-section">
        <div class="modal-section-title">
          <i data-feather="phone"></i> Contacts
        </div>
        <div class="modal-grid">
          <div class="modal-field">
            <div class="modal-field-label">Mairie — Téléphone(s)</div>
            <div class="modal-field-value">
              ${(cm.telephones || []).join(", ") || "—"}
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Mairie — Mail(s)</div>
            <div class="modal-field-value">
              ${(cm.mails || []).join(", ") || "—"}
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Mairie — Code postal</div>
            <div class="modal-field-value">${cm.code_postal || "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Personne ressource</div>
            <div class="modal-field-value">
              ${cr.nom || "—"}
              ${cr.role
                ? `<span style="color:var(--text-3);font-size:0.72rem"> · ${cr.role}</span>`
                : ""}
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Ressource — Téléphone</div>
            <div class="modal-field-value">
              ${(cr.telephones || []).join(", ") || "—"}
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Ressource — Mail</div>
            <div class="modal-field-value">
              ${(cr.mails || []).join(", ") || "—"}
            </div>
          </div>
        </div>
      </div>

      <!-- GPS -->
      <div class="modal-section">
        <div class="modal-section-title">
          <i data-feather="crosshair"></i> Coordonnées GPS
        </div>
        <div class="modal-grid">
          <div class="modal-field">
            <div class="modal-field-label">Latitude</div>
            <div class="modal-field-value cell-mono">${gps.latitude ?? "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Longitude</div>
            <div class="modal-field-value cell-mono">${gps.longitude ?? "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Altitude (m)</div>
            <div class="modal-field-value cell-mono">${gps.altitude ?? "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Précision</div>
            <div class="modal-field-value cell-mono">${gps.precision ?? "—"}</div>
          </div>
        </div>
      </div>

      <!-- Connectivité -->
      <div class="modal-section">
        <div class="modal-section-title">
          <i data-feather="wifi"></i> Connectivité & Électrification
        </div>
        <div class="modal-grid">
          <div class="modal-field">
            <div class="modal-field-label">Internet constant</div>
            <div class="modal-field-value">
              <span class="badge ${c.connectivite_constante ? 'badge-green' : 'badge-red'}">
                ${c.connectivite_constante ? "Oui" : "Non"}
              </span>
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Lien international</div>
            <div class="modal-field-value">
              ${c.lien_etranger
                ? `<span class="badge badge-yellow">${(c.pays_etrangers || []).join(", ") || "Oui"}</span>`
                : '<span class="badge badge-grey">Non</span>'}
            </div>
          </div>
        </div>
        ${(c.villages_non_connectes || []).length > 0 ? `
          <div style="margin-top:0.6rem">
            <div class="modal-field-label" style="margin-bottom:0.35rem">
              Villages non connectés
            </div>
            <div class="modal-tags">
              ${c.villages_non_connectes.map(v =>
                `<span class="modal-tag">${v}</span>`).join("")}
            </div>
          </div>
        ` : ""}
      </div>

      <!-- Langues & Ethnies -->
      <div class="modal-section">
        <div class="modal-section-title">
          <i data-feather="users"></i> Langues & Ethnies
        </div>
        <div class="modal-field" style="margin-bottom:0.6rem">
          <div class="modal-field-label">Langues locales</div>
          <div class="modal-tags" style="margin-top:0.3rem">
            ${(c.langues_locales || []).map(l =>
              `<span class="modal-tag">${l}</span>`).join("") || "—"}
          </div>
        </div>
        <div class="modal-field">
          <div class="modal-field-label">Ethnies</div>
          <div class="modal-tags" style="margin-top:0.3rem">
            ${(data.ethnies || []).map(e =>
              `<span class="modal-tag">${e.nom}</span>`).join("") || "—"}
          </div>
        </div>
      </div>

      <!-- Villages & Quartiers -->
      ${data.villages?.length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="map-pin"></i>
            Villages & Quartiers (${data.villages.length})
          </div>
          <div class="modal-tags">
            ${data.villages.map(v => `
              <span class="modal-tag badge-${v.type}">
                ${v.type === "village" ? "🌿" : "🏙"} ${v.nom}
              </span>
            `).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Chefferies -->
      ${data.chefferies?.length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="shield"></i>
            Chefferies (${data.chefferies.length})
          </div>
          <ul class="modal-list">
            ${data.chefferies.map(ch => `
              <li>
                <span>${ch.nom}</span>
                ${ch.latitude
                  ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.7rem;font-family:monospace">
                       ${ch.latitude}, ${ch.longitude}
                     </span>`
                  : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      ` : ""}

      <!-- Marchés -->
      ${data.marches?.length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="shopping-bag"></i>
            Marchés (${data.marches.length})
          </div>
          <ul class="modal-list">
            ${data.marches.map(m => `
              <li>
                <span>${m.nom}</span>
                ${m.jour
                  ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.7rem">
                       ${m.jour} · ${m.heure_debut || ""}–${m.heure_fin || ""}
                     </span>`
                  : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      ` : ""}

      <!-- Lieux par type -->
      ${afficherLieuxParType(data.lieux || [])}

      <!-- Coopératives -->
      ${data.cooperatives?.length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="briefcase"></i>
            Coopératives & GIC (${data.cooperatives.length})
          </div>
          <div class="modal-tags">
            ${data.cooperatives.map(co =>
              `<span class="modal-tag">${co.nom}</span>`).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Agriculture -->
      ${(c.agriculture_artisanat || []).length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="sun"></i> Agriculture & Artisanat
          </div>
          <div class="modal-tags">
            ${c.agriculture_artisanat.map(a =>
              `<span class="modal-tag">${a}</span>`).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Délégations -->
      ${(c.delegations_ministeres || []).length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="briefcase"></i> Délégations ministérielles
          </div>
          <div class="modal-tags">
            ${c.delegations_ministeres.map(d =>
              `<span class="modal-tag badge-grey">${d}</span>`).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Gares -->
      ${(c.gare_voyageurs || []).length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="navigation"></i> Gares voyageurs
          </div>
          <ul class="modal-list">
            ${c.gare_voyageurs.map(g => `
              <li>
                <span>${g.nom}</span>
                ${g.latitude
                  ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.7rem;font-family:monospace">
                       ${g.latitude}, ${g.longitude}
                     </span>`
                  : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      ` : ""}

      <!-- Autres infos -->
      ${c.autres_informations ? `
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="info"></i> Autres informations
          </div>
          <div style="font-size:0.8rem;color:var(--text-2);line-height:1.6">
            ${c.autres_informations}
          </div>
        </div>
      ` : ""}

      <hr class="modal-divider" />

      <!-- Traçabilité -->
      <div class="modal-section">
        <div class="modal-section-title">
          <i data-feather="clock"></i> Traçabilité KoboCollect
        </div>
        <div class="modal-grid">
          <div class="modal-field">
            <div class="modal-field-label">Soumis par</div>
            <div class="modal-field-value">${c.submitted_by || "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Date de soumission</div>
            <div class="modal-field-value">
              ${c.submission_time
                ? new Date(c.submission_time).toLocaleString("fr-FR")
                : "—"}
            </div>
          </div>
          <div class="modal-field" style="grid-column:1/-1">
            <div class="modal-field-label">UUID KoboCollect</div>
            <div class="modal-field-value cell-mono" style="font-size:0.72rem;color:var(--text-3)">
              ${c.kobocollect_uuid || "—"}
            </div>
          </div>
        </div>
      </div>
    `;

  } catch {
    modal.innerHTML = `
      <p style="color:var(--red-light);text-align:center;padding:2rem">
        Erreur de chargement de la commune.
      </p>
    `;
  }

  feather.replace();
}

/**
 * Groupe les lieux par type et génère le HTML.
 * @param {Array} lieux
 * @returns {string}
 */
function afficherLieuxParType(lieux) {
  if (!lieux || lieux.length === 0) return "";

  const icones = {
    scolaire:    "book-open",
    urgence:     "activity",
    touristique: "camera",
    religieux:   "sun",
    eau:         "droplet",
    sportif:     "award",
    reference:   "navigation",
  };

  const groupes = {};
  lieux.forEach(lieu => {
    const type = lieu.type_nom || "autre";
    if (!groupes[type]) groupes[type] = [];
    groupes[type].push(lieu);
  });

  return Object.entries(groupes).map(([type, liste]) => `
    <div class="modal-section">
      <div class="modal-section-title">
        <i data-feather="${icones[type] || 'map-pin'}"></i>
        ${capitaliser(type)} (${liste.length})
      </div>
      <ul class="modal-list">
        ${liste.map(lieu => `
          <li>
            <span>${lieu.nom}</span>
            ${lieu.coordonnees?.latitude
              ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.7rem;font-family:monospace">
                   ${lieu.coordonnees.latitude}, ${lieu.coordonnees.longitude}
                 </span>`
              : ""}
          </li>
        `).join("")}
      </ul>
    </div>
  `).join("");
}

/**
 * Ferme la modal.
 */
function fermerModal() {
  document.getElementById("modalOverlay").classList.remove("open");
}


// ════════════════════════════════════════════════════════════════
// 16. UTILITAIRES
// ════════════════════════════════════════════════════════════════

/**
 * Génère le HTML d'un état vide.
 * @param {string} icone - Nom d'icône Feather
 * @param {string} titre
 * @param {string} sous
 * @returns {string}
 */
function vueVide(icone, titre, sous) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">
        <i data-feather="${icone}"></i>
      </div>
      <div class="empty-state-title">${titre}</div>
      <div class="empty-state-sub">${sous}</div>
    </div>
  `;
}

/**
 * Génère le HTML d'un indicateur de chargement.
 * @returns {string}
 */
function chargementHTML() {
  return `
    <div class="empty-state">
      <div class="progress-spinner" style="margin:0 auto"></div>
    </div>
  `;
}

/**
 * Met la première lettre en majuscule.
 * @param {string} str
 * @returns {string}
 */
function capitaliser(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}


// ════════════════════════════════════════════════════════════════
// 17. INITIALISATION
// ════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  verifierSante();
  chargerDashboard();
});