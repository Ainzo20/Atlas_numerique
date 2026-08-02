/**
 * carte.js — Initialisation de la carte Leaflet + couches GeoJSON de base.
 * Pas d'interactivite pour l'instant (popups/clics geres a l'etape 7).
 */

import { getCommunes,getLieux, getCommuneDetail } from "../core/api.js";
import { ouvrirPanneau, definirContenuPanneau } from "./panneau-lateral.js";

// Centre approximatif du Cameroun
const CENTRE_CAMEROUN = [7.3697, 12.3547];
const ZOOM_INITIAL = 6;
let donneesRegionsGeoJSON = null;
let carte = null;

function activerAccordeon() {
    document.querySelectorAll("#panneauContenu .modal-section.repliable .modal-section-title").forEach(titre => {
      titre.addEventListener("click", () => {
        titre.closest(".modal-section").classList.toggle("ouvert");
      });
    });
  }
/**
 * Initialise la carte Leaflet dans le conteneur donne.
 * @param {string} idConteneur - id de l'element HTML qui accueille la carte
 * @returns {L.Map}
 */
function initCarte(idConteneur) {
  carte = L.map(idConteneur).setView(CENTRE_CAMEROUN, ZOOM_INITIAL);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(carte);

  chargerCoucheRegions();
  chargerMarqueursCommunes();

  return carte;
}

/**
 * Charge et affiche les polygones des regions.
 */
/**
 * Charge et affiche les polygones des regions avec tooltip au survol.
 */
async function chargerCoucheRegions() {
    try {
      const res = await fetch("/static/geojson/regions.geojson");
      const donnees = await res.json();

      donneesRegionsGeoJSON = donnees;
      L.geoJSON(donnees, {
        style: {
          color: "#00a07a",
          weight: 1.5,
          fillColor: "#00a07a",
          fillOpacity: 0.08,
        },
        onEachFeature: (feature, couche) => {
          const props = feature.properties;
          const nom = props.region || props.NAME || "Region inconnue";
          const population = props.population
            ? Number(props.population).toLocaleString("fr-FR")
            : null;
  
          couche.bindTooltip(`
            <div class="tooltip-region">
              <strong>${nom}</strong>
              ${population ? `<br><span class="tooltip-meta">${population} habitants</span>` : ""}
            </div>
          `, { sticky: true, className: "leaflet-tooltip-custom" });
  
          // Effet visuel au survol : accentue le polygone survole
          couche.on("mouseover", () => {
            couche.setStyle({ fillOpacity: 0.25, weight: 2.5 });
          });
          couche.on("mouseout", () => {
            couche.setStyle({ fillOpacity: 0.08, weight: 1.5 });
          });
        },
      }).addTo(carte);
    } catch (erreur) {
      console.error("Erreur chargement GeoJSON regions :", erreur);
    }
  }
/**
 * Charge et affiche les marqueurs des communes (donnees GPS existantes en base).
 */
/**
 * Charge et affiche les marqueurs des communes avec tooltip "bulle" au survol.
 */
async function chargerMarqueursCommunes() {
    try {
      const data = await getCommunes();
      const communes = data.communes || [];
  
      communes.forEach(item => {
        const coords = item.commune?.coordonnees;
        if (!coords?.latitude || !coords?.longitude) return;
  
        const marqueur = L.circleMarker([coords.latitude, coords.longitude], {
          radius: 6,
          color: "#FCD116",
          fillColor: "#FCD116",
          fillOpacity: 0.85,
          weight: 1.5,
        }).addTo(carte);
  
        const idCommune = item.commune._id;
        const nom = item.commune.nom;
        const localisation = [item.region, item.departement].filter(Boolean).join(" · ");
  
        marqueur.bindTooltip(`
          <div class="tooltip-commune">
            <strong>${nom}</strong>
            ${localisation ? `<div class="tooltip-meta">${localisation}</div>` : ""}
            <div class="tooltip-lien" data-id-commune="${idCommune}">
              Voir details →
            </div>
          </div>
        `, {
          sticky: true,
          direction: "top",
          offset: [0, -8],
          className: "leaflet-tooltip-custom leaflet-tooltip-commune",
        });
  
        // Clic sur le marqueur (ou sur le lien "Voir details" dans le tooltip)
        marqueur.on("click", () => afficherDetailCommune(idCommune));
      });
    } catch (erreur) {
      console.error("Erreur chargement communes :", erreur);
    }
  }

  export { initCarte, afficherDetailCommune as afficherDetailCommuneExterne };

/**
 * Affiche soit l'image de la commune, soit un mini-apercu du polygone
 * de sa region en fallback.
 * @param {object} c - donnees commune
 * @param {string} nomRegion
 */
function construireEnTeteVisuel(c, nomRegion) {
    if (c.image_url) {
      return `<img src="${c.image_url}" alt="${c.nom}" class="panneau-image" />`;
    }
    return `<div id="miniCarteRegion" class="panneau-minicarte"></div>`;
  }
  
  /**
   * Initialise la mini-carte de fallback pour une region donnee.
   * Doit etre appelee APRES que le HTML soit insere dans le DOM.
   * @param {string} nomRegion
   */
  function initMiniCarteRegion(nomRegion) {
    if (!donneesRegionsGeoJSON) return;
  
    const feature = donneesRegionsGeoJSON.features.find(
      f => (f.properties.region || f.properties.NAME) === nomRegion
    );
    if (!feature) return;
  
    const conteneur = document.getElementById("miniCarteRegion");
    if (!conteneur) return;
  
    const miniCarte = L.map("miniCarteRegion", {
      zoomControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      attributionControl: false,
    });
  
    const couche = L.geoJSON(feature, {
      style: { color: "#00a07a", weight: 1.5, fillColor: "#00a07a", fillOpacity: 0.2 },
    }).addTo(miniCarte);
  
    miniCarte.fitBounds(couche.getBounds(), { padding: [10, 10] });
  }
  
/**
 * Charge et affiche les details complets d'une commune dans le panneau lateral.
 * @param {string} idCommune
 */
async function afficherDetailCommune(idCommune) {
    ouvrirPanneau();
    definirContenuPanneau(`
      <div class="empty-state">
        <div class="progress-spinner" style="margin:0 auto"></div>
      </div>
    `);
  
    try {
      const data = await getCommuneDetail(idCommune);
      const c = data.commune;
      const h = data.hierarchie;
      const gps = c.coordonnees || {};
      const nomRegion = h.region?.nom || "";
  
      definirContenuPanneau(`
        <div class="modal-commune-header">
          <div class="modal-commune-nom">${c.nom}</div>
          <div class="modal-commune-loc">
            <i data-feather="map-pin"></i>
            ${h.region?.nom || "—"} · ${h.departement?.nom || "—"} · ${h.arrondissement?.nom || "—"}
          </div>
        </div>
  
        ${construireEnTeteVisuel(c, nomRegion)}
  
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="crosshair"></i> Coordonnees GPS
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
          </div>
        </div>
  
        <div class="modal-section">
          <div class="modal-section-title">
            <i data-feather="wifi"></i> Connectivite
          </div>
          <span class="badge ${c.connectivite_constante ? 'badge-green' : 'badge-red'}">
            ${c.connectivite_constante ? "Oui" : "Non"}
          </span>
        </div>
  
       <div class="modal-section repliable">
        <div class="modal-section-title">
            <i data-feather="phone"></i> Contacts
            <i data-feather="chevron-down"></i>
        </div>
        <div class="modal-section-corps">
            <div class="modal-grid">
            <div class="modal-field">
              <div class="modal-field-label">Mairie — Telephone(s)</div>
              <div class="modal-field-value">${(c.contact_mairie?.telephones || []).join(", ") || "—"}</div>
            </div>
            <div class="modal-field">
              <div class="modal-field-label">Mairie — Mail(s)</div>
              <div class="modal-field-value">${(c.contact_mairie?.mails || []).join(", ") || "—"}</div>
            </div>
            <div class="modal-field">
              <div class="modal-field-label">Personne ressource</div>
              <div class="modal-field-value">${c.contact_personne_ressource?.nom || "—"}</div>
            </div>
            <div class="modal-field">
              <div class="modal-field-label">Ressource — Telephone</div>
              <div class="modal-field-value">${(c.contact_personne_ressource?.telephones || []).join(", ") || "—"}</div>
            </div>
          </div>
        </div>
        ${data.villages?.length > 0 ? `
            <div class="modal-section repliable">
              <div class="modal-section-title">
                <i data-feather="map-pin"></i> Villages & Quartiers (${data.villages.length})
                <i data-feather="chevron-down"></i>
              </div>
              <div class="modal-section-corps">
                <div class="modal-tags">
              ${data.villages.map(v => `<span class="modal-tag">${v.type === "village" ? "🌿" : "🏙"} ${v.nom}</span>`).join("")}
            </div>
          </div>
        ` : ""}
  
        ${data.lieux?.length > 0 ? `
            <div class="modal-section repliable">
              <div class="modal-section-title">
                <i data-feather="layers"></i> Lieux (${data.lieux.length})
                <i data-feather="chevron-down"></i>
              </div>
              <div class="modal-section-corps">
                <ul class="modal-list">
              ${data.lieux.map(l => `<li>${l.nom} <span style="margin-left:auto;color:var(--text-3);font-size:0.7rem">${l.type_nom || ""}</span></li>`).join("")}
            </ul>
          </div>
        ` : ""}
  
        ${(c.langues_locales || []).length > 0 ? `
          <div class="modal-section">
            <div class="modal-section-title">
              <i data-feather="users"></i> Langues locales
            </div>
            <div class="modal-tags">
              ${c.langues_locales.map(l => `<span class="modal-tag">${l}</span>`).join("")}
            </div>
          </div>
        ` : ""}
      `);

      activerAccordeon();
  
      if (!c.image_url) {
        initMiniCarteRegion(nomRegion);
      }
  
    } catch (erreur) {
      definirContenuPanneau(`
        <p style="color:var(--red-light);text-align:center;padding:2rem">
          Erreur de chargement de la commune.
        </p>
      `);
      console.error("Erreur detail commune :", erreur);
    }
  }