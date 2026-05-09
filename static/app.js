/**
 * app.js — Atlas Numérique du Cameroun
 * ------------------------------------
 * Logique frontend : navigation, appels API, rendu des données.
 *
 * Organisation :
 * 1. Configuration
 * 2. Navigation
 * 3. Santé / Stats
 * 4. Import CSV
 * 5. Régions
 * 6. Communes
 * 7. Export
 * 8. Modal commune
 * 9. Utilitaires
 * 10. Initialisation
 */


// ════════════════════════════════════════════════════════════════
// 1. CONFIGURATION
// ════════════════════════════════════════════════════════════════

// URL de base de l'API — vide = même origine (localhost ou Render)
const API = "";

// Fichier CSV sélectionné — stocké globalement pour l'import
let fichierSelectionne = null;

// Cache des communes pour éviter les appels répétés lors du filtrage
let toutesLesCommunes = [];


// ════════════════════════════════════════════════════════════════
// 2. NAVIGATION
// ════════════════════════════════════════════════════════════════

/**
 * Change la page active et charge les données correspondantes.
 *
 * @param {string} page - Identifiant de la page ('dashboard', 'import', etc.)
 */
function naviguer(page) {
  // Masquer toutes les pages
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));

  // Désactiver tous les liens nav
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  // Activer la page cible
  document.getElementById(`page-${page}`).classList.add("active");

  // Activer le lien nav correspondant
  const navItem = document.querySelector(`[data-page="${page}"]`);
  if (navItem) navItem.classList.add("active");

  // Charger les données selon la page
  switch (page) {
    case "dashboard": chargerDashboard(); break;
    case "regions":   chargerRegions();   break;
    case "communes":  chargerCommunes();  break;
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
      dot.className  = "status-dot ok";
      text.textContent = "MongoDB connecté";
    } else {
      dot.className  = "status-dot error";
      text.textContent = "MongoDB déconnecté";
    }
  } catch {
    dot.className  = "status-dot error";
    text.textContent = "Hors ligne";
  }
}

/**
 * Charge les statistiques globales et les affiche dans le dashboard.
 */
async function chargerStats() {
  try {
    const res  = await fetch(`${API}/stats`);
    const data = await res.json();

    // Mapping id HTML → clé dans la réponse API
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
        el.closest(".stat-card").classList.remove("loading");
      }
    });

  } catch {
    document.querySelectorAll(".stat-value").forEach(el => {
      el.textContent = "—";
    });
  }
}

/**
 * Charge le dashboard complet : stats + aperçu des communes.
 */
async function chargerDashboard() {
  chargerStats();

  try {
    const res  = await fetch(`${API}/communes`);
    const data = await res.json();

    const container = document.getElementById("dashboardCommunes");

    if (!data.communes || data.communes.length === 0) {
      container.innerHTML = vueVide("🏘", "Aucune commune", "Importez un fichier CSV pour commencer.");
      return;
    }

    // Afficher les 8 premières communes
    const preview = data.communes.slice(0, 8);
    container.innerHTML = preview.map(item => `
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
      vueVide("⚠", "Erreur de chargement", "Impossible de récupérer les communes.");
  }
}


// ════════════════════════════════════════════════════════════════
// 4. IMPORT CSV
// ════════════════════════════════════════════════════════════════

/**
 * Gère le drop de fichier sur la zone de dépôt.
 *
 * @param {DragEvent} event - Événement de drop
 */
function handleDrop(event) {
  event.preventDefault();
  document.getElementById("dropZone").classList.remove("drag-over");

  const fichier = event.dataTransfer.files[0];
  if (fichier) selectionnerFichier(fichier);
}

/**
 * Gère la sélection via le bouton Parcourir.
 *
 * @param {Event} event - Événement change de l'input file
 */
function handleFileSelect(event) {
  const fichier = event.target.files[0];
  if (fichier) selectionnerFichier(fichier);
}

/**
 * Enregistre le fichier sélectionné et affiche ses informations.
 *
 * @param {File} fichier - Fichier CSV sélectionné
 */
function selectionnerFichier(fichier) {
  if (!fichier.name.endsWith(".csv")) {
    alert("Le fichier doit être au format .csv");
    return;
  }

  fichierSelectionne = fichier;

  document.getElementById("dropZone").style.display    = "none";
  document.getElementById("fileSelected").style.display = "flex";
  document.getElementById("importRapport").style.display = "none";

  document.getElementById("fileName").textContent =
    fichier.name;
  document.getElementById("fileSize").textContent =
    `${(fichier.size / 1024).toFixed(1)} Ko`;
}

/**
 * Annule la sélection du fichier et revient à la zone de dépôt.
 */
function annulerFichier() {
  fichierSelectionne = null;
  document.getElementById("dropZone").style.display     = "block";
  document.getElementById("fileSelected").style.display = "none";
  document.getElementById("importProgress").style.display = "none";
  document.getElementById("importRapport").style.display  = "none";
  document.getElementById("csvInput").value = "";
}

/**
 * Lance l'import du fichier CSV vers l'API.
 * Affiche la progression puis le rapport d'import.
 */
async function lancerImport() {
  if (!fichierSelectionne) return;

  // Afficher la progression
  document.getElementById("fileSelected").style.display  = "none";
  document.getElementById("importProgress").style.display = "flex";
  document.getElementById("importRapport").style.display  = "none";

  const formData = new FormData();
  formData.append("fichier", fichierSelectionne);

  try {
    const res  = await fetch(`${API}/import`, { method: "POST", body: formData });
    const data = await res.json();

    // Masquer la progression
    document.getElementById("importProgress").style.display = "none";

    afficherRapport(data, res.ok);

    // Réinitialiser pour permettre un nouvel import
    fichierSelectionne = null;
    document.getElementById("csvInput").value = "";

  } catch (erreur) {
    document.getElementById("importProgress").style.display = "none";
    afficherRapport({ message: erreur.message }, false);
  }
}

/**
 * Affiche le rapport d'import après traitement.
 *
 * @param {object} data   - Données retournées par l'API
 * @param {boolean} succes - True si la requête a réussi
 */
function afficherRapport(data, succes) {
  const el = document.getElementById("importRapport");
  el.style.display = "block";

  if (!succes || data.detail) {
    el.className = "import-rapport rapport-erreur";
    el.innerHTML = `
      <div class="rapport-title" style="color: var(--error)">
        ✕ Erreur d'import
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
    <div class="rapport-title" style="color: var(--success)">
      ✓ Import terminé
    </div>
    <div class="rapport-stat">
      <span>Communes traitées</span>
      <span>${data.total}</span>
    </div>
    <div class="rapport-stat">
      <span>Succès</span>
      <span>${data.succes}</span>
    </div>
    <div class="rapport-stat">
      <span>Erreurs</span>
      <span>${data.erreurs}</span>
    </div>
    ${data.details ? data.details.filter(d => d.statut === "erreur").map(d => `
      <div class="rapport-stat" style="color: var(--error)">
        <span>${d.commune}</span>
        <span>${d.message}</span>
      </div>
    `).join("") : ""}
  `;

  // Rafraîchir les stats du dashboard
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
  container.innerHTML = `<div class="empty-state"><div class="progress-spinner" style="margin:auto"></div></div>`;

  try {
    const res  = await fetch(`${API}/regions`);
    const data = await res.json();

    if (!data.regions || data.regions.length === 0) {
      container.innerHTML = vueVide("🗺", "Aucune région", "Importez un fichier CSV pour commencer.");
      return;
    }

    container.innerHTML = data.regions.map(region => `
      <div class="region-card" onclick="ouvrirRegion('${region._id}')">
        <div class="region-nom">${region.nom}</div>
        <div class="region-meta">
          ${region.nb_departements} département${region.nb_departements > 1 ? "s" : ""}
        </div>
        <span class="region-badge">Voir les détails →</span>
      </div>
    `).join("");

  } catch {
    container.innerHTML = vueVide("⚠", "Erreur", "Impossible de charger les régions.");
  }
}

/**
 * Ouvre le détail d'une région dans la modal.
 *
 * @param {string} idRegion - ID MongoDB de la région
 */
async function ouvrirRegion(idRegion) {
  const modal = document.getElementById("modalContent");
  modal.innerHTML = `<div class="empty-state"><div class="progress-spinner" style="margin:auto"></div></div>`;
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
        <div class="modal-section-title">Départements</div>
        <ul class="modal-list">
          ${data.departements.map(d => `
            <li>
              ${d.nom}
              <span style="margin-left:auto; color:var(--text-3); font-size:0.72rem">
                ${d.nb_arrondissements} arrondissement${d.nb_arrondissements > 1 ? "s" : ""}
              </span>
            </li>
          `).join("") || "<li>Aucun département</li>"}
        </ul>
      </div>
    `;

  } catch {
    modal.innerHTML = `<p style="color:var(--error)">Erreur de chargement.</p>`;
  }
}


// ════════════════════════════════════════════════════════════════
// 6. COMMUNES
// ════════════════════════════════════════════════════════════════

/**
 * Charge toutes les communes et les affiche dans le tableau.
 */
async function chargerCommunes() {
  const container = document.getElementById("communesContent");
  container.innerHTML = `<div class="empty-state"><div class="progress-spinner" style="margin:auto"></div></div>`;

  try {
    const res  = await fetch(`${API}/communes`);
    const data = await res.json();

    toutesLesCommunes = data.communes || [];
    afficherTableauCommunes(toutesLesCommunes);

  } catch {
    container.innerHTML = vueVide("⚠", "Erreur", "Impossible de charger les communes.");
  }
}

/**
 * Affiche la liste des communes dans un tableau HTML.
 *
 * @param {Array} communes - Liste des communes à afficher
 */
function afficherTableauCommunes(communes) {
  const container = document.getElementById("communesContent");

  if (communes.length === 0) {
    container.innerHTML = vueVide("🏘", "Aucun résultat", "Essayez d'autres filtres.");
    return;
  }

  container.innerHTML = `
    <table class="communes-table">
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
            <td class="commune-nom-cell">${item.commune.nom}</td>
            <td>${item.region || "—"}</td>
            <td>${item.departement || "—"}</td>
            <td>${item.arrondissement || "—"}</td>
            <td>
              <span class="badge-connecte ${item.commune.connectivite_constante ? 'badge-oui' : 'badge-non'}">
                ${item.commune.connectivite_constante ? "Oui" : "Non"}
              </span>
            </td>
            <td>${(item.commune.langues_locales || []).slice(0, 2).join(", ") || "—"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

/**
 * Filtre les communes selon les valeurs des champs de filtre.
 * Utilise le cache local pour éviter des appels API répétés.
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
 * Réinitialise les filtres et réaffiche toutes les communes.
 */
function reinitialiserFiltres() {
  document.getElementById("filtreRegion").value = "";
  document.getElementById("filtreDept").value   = "";
  afficherTableauCommunes(toutesLesCommunes);
}


// ════════════════════════════════════════════════════════════════
// 7. EXPORT
// ════════════════════════════════════════════════════════════════

/**
 * Déclenche le téléchargement de l'export CSV ou Excel.
 *
 * @param {string} format - 'csv' ou 'excel'
 */
function exporter(format) {
  const region = document.getElementById("exportRegion").value.trim();
  let url = `${API}/export?format=${format}`;
  if (region) url += `&region=${encodeURIComponent(region)}`;

  // On crée un lien invisible et on le clique pour déclencher le téléchargement
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = format === "csv" ? "communes_export.csv" : "communes_export.xlsx";
  document.body.appendChild(lien);
  lien.click();
  document.body.removeChild(lien);
}


// ════════════════════════════════════════════════════════════════
// 8. MODAL COMMUNE
// ════════════════════════════════════════════════════════════════

/**
 * Ouvre la modal et charge les détails complets d'une commune.
 *
 * @param {string} idCommune - ID MongoDB de la commune
 */
async function ouvrirModal(idCommune) {
  const modal = document.getElementById("modalContent");
  modal.innerHTML = `<div class="empty-state"><div class="progress-spinner" style="margin:auto"></div></div>`;
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

      <!-- En-tête -->
      <div class="modal-commune-header">
        <div class="modal-commune-nom">${c.nom}</div>
        <div class="modal-commune-loc">
          ${h.region?.nom || "—"} · ${h.departement?.nom || "—"} · ${h.arrondissement?.nom || "—"}
        </div>
      </div>

      <!-- Contacts -->
      <div class="modal-section">
        <div class="modal-section-title">Contacts</div>
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
            <div class="modal-field-label">Personne ressource</div>
            <div class="modal-field-value">
              ${cr.nom || "—"}${cr.role ? ` · <em style="color:var(--text-3)">${cr.role}</em>` : ""}
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Contact ressource</div>
            <div class="modal-field-value">
              ${(cr.telephones || []).join(", ") || "—"}
            </div>
          </div>
        </div>
      </div>

      <!-- GPS -->
      <div class="modal-section">
        <div class="modal-section-title">Coordonnées GPS</div>
        <div class="modal-grid">
          <div class="modal-field">
            <div class="modal-field-label">Latitude</div>
            <div class="modal-field-value">${gps.latitude ?? "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Longitude</div>
            <div class="modal-field-value">${gps.longitude ?? "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Altitude (m)</div>
            <div class="modal-field-value">${gps.altitude ?? "—"}</div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Précision</div>
            <div class="modal-field-value">${gps.precision ?? "—"}</div>
          </div>
        </div>
      </div>

      <!-- Connectivité -->
      <div class="modal-section">
        <div class="modal-section-title">Connectivité & Électrification</div>
        <div class="modal-grid">
          <div class="modal-field">
            <div class="modal-field-label">Internet constant</div>
            <div class="modal-field-value">
              <span class="badge-connecte ${c.connectivite_constante ? 'badge-oui' : 'badge-non'}">
                ${c.connectivite_constante ? "Oui" : "Non"}
              </span>
            </div>
          </div>
          <div class="modal-field">
            <div class="modal-field-label">Lien international</div>
            <div class="modal-field-value">
              ${c.lien_etranger
                ? (c.pays_etrangers || []).join(", ") || "Oui"
                : "Non"}
            </div>
          </div>
        </div>
        ${(c.villages_non_connectes || []).length > 0 ? `
          <div style="margin-top:0.5rem">
            <div class="modal-field-label" style="margin-bottom:0.4rem">Villages non connectés</div>
            <div class="modal-tags">
              ${c.villages_non_connectes.map(v => `<span class="modal-tag">${v}</span>`).join("")}
            </div>
          </div>
        ` : ""}
      </div>

      <!-- Langues & Ethnies -->
      <div class="modal-section">
        <div class="modal-section-title">Langues & Ethnies</div>
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
            Villages & Quartiers (${data.villages.length})
          </div>
          <div class="modal-tags">
            ${data.villages.map(v =>
              `<span class="modal-tag">${v.type === "village" ? "🌿" : "🏙"} ${v.nom}</span>`
            ).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Chefferies -->
      ${data.chefferies?.length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">Chefferies (${data.chefferies.length})</div>
          <ul class="modal-list">
            ${data.chefferies.map(ch => `
              <li>
                ${ch.nom}
                ${ch.latitude ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.72rem">${ch.latitude}, ${ch.longitude}</span>` : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      ` : ""}

      <!-- Marchés -->
      ${data.marches?.length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">Marchés (${data.marches.length})</div>
          <ul class="modal-list">
            ${data.marches.map(m => `
              <li>
                ${m.nom}
                ${m.jour ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.72rem">${m.jour} ${m.heure_debut || ""}–${m.heure_fin || ""}</span>` : ""}
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
          <div class="modal-section-title">Coopératives & GIC (${data.cooperatives.length})</div>
          <div class="modal-tags">
            ${data.cooperatives.map(co =>
              `<span class="modal-tag">${co.nom}</span>`).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Agriculture -->
      ${(c.agriculture_artisanat || []).length > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">Agriculture & Artisanat</div>
          <div class="modal-tags">
            ${c.agriculture_artisanat.map(a =>
              `<span class="modal-tag">${a}</span>`).join("")}
          </div>
        </div>
      ` : ""}

      <!-- Autres infos -->
      ${c.autres_informations ? `
        <div class="modal-section">
          <div class="modal-section-title">Autres informations</div>
          <div style="font-size:0.82rem; color:var(--text-2); line-height:1.6;">
            ${c.autres_informations}
          </div>
        </div>
      ` : ""}

      <!-- Tracabilité -->
      <div class="modal-section" style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid var(--border)">
        <div class="modal-section-title">Traçabilité KoboCollect</div>
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
          <div class="modal-field" style="grid-column: 1 / -1">
            <div class="modal-field-label">UUID KoboCollect</div>
            <div class="modal-field-value" style="font-family:monospace; font-size:0.75rem; color:var(--text-3)">
              ${c.kobocollect_uuid || "—"}
            </div>
          </div>
        </div>
      </div>
    `;

  } catch (erreur) {
    modal.innerHTML = `
      <p style="color:var(--error); text-align:center; padding:2rem">
        Erreur de chargement de la commune.
      </p>
    `;
  }
}

/**
 * Groupe les lieux par type et génère le HTML correspondant.
 *
 * @param {Array} lieux - Liste des lieux de la commune
 * @returns {string} HTML des sections de lieux groupés par type
 */
function afficherLieuxParType(lieux) {
  if (!lieux || lieux.length === 0) return "";

  // Emojis par type de lieu
  const emojis = {
    scolaire:    "🏫",
    urgence:     "🏥",
    touristique: "🏛",
    religieux:   "⛪",
    eau:         "💧",
    sportif:     "⚽",
    reference:   "📍",
  };

  // Grouper les lieux par type
  const groupes = {};
  lieux.forEach(lieu => {
    const type = lieu.type_nom || "autre";
    if (!groupes[type]) groupes[type] = [];
    groupes[type].push(lieu);
  });

  return Object.entries(groupes).map(([type, liste]) => `
    <div class="modal-section">
      <div class="modal-section-title">
        ${emojis[type] || "📌"} ${capitaliser(type)} (${liste.length})
      </div>
      <ul class="modal-list">
        ${liste.map(lieu => `
          <li>
            ${lieu.nom}
            ${lieu.coordonnees?.latitude
              ? `<span style="margin-left:auto;color:var(--text-3);font-size:0.72rem">
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
// 9. UTILITAIRES
// ════════════════════════════════════════════════════════════════

/**
 * Génère le HTML d'un état vide (aucune donnée).
 *
 * @param {string} icone  - Emoji ou icône
 * @param {string} titre  - Titre de l'état vide
 * @param {string} sous   - Sous-texte explicatif
 * @returns {string} HTML de l'état vide
 */
function vueVide(icone, titre, sous) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">${icone}</div>
      <div class="empty-state-title">${titre}</div>
      <div class="empty-state-sub">${sous}</div>
    </div>
  `;
}

/**
 * Met la première lettre d'une chaîne en majuscule.
 *
 * @param {string} str - Chaîne à capitaliser
 * @returns {string} Chaîne capitalisée
 */
function capitaliser(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}


// ════════════════════════════════════════════════════════════════
// 10. INITIALISATION
// ════════════════════════════════════════════════════════════════

/**
 * Point d'entrée — exécuté au chargement de la page.
 * Lance la vérification de santé et charge le dashboard.
 */
document.addEventListener("DOMContentLoaded", () => {
  verifierSante();
  chargerDashboard();
});