/**
 * sidebar.js — Genere la navigation laterale.
 */
import { naviguerVers } from "../core/router.js";

const LIENS = [
  { chemin: "/", icone: "map", label: "Carte", exact: true },
  { chemin: "/regions", icone: "flag", label: "Regions" },
  { chemin: "/communes", icone: "home", label: "Communes" },
  { separateur: "Donnees" },
  { chemin: "/villages", icone: "map-pin", label: "Villages & Quartiers" },
  { chemin: "/lieux", icone: "layers", label: "Lieux" },
  { chemin: "/chefferies", icone: "shield", label: "Chefferies" },
  { chemin: "/marches", icone: "shopping-bag", label: "Marches" },
  { chemin: "/ethnies", icone: "users", label: "Ethnies" },
  { chemin: "/cooperatives", icone: "briefcase", label: "Cooperatives" },
  { chemin: "/exercices", icone: "bar-chart-2", label: "Exercices" },
  { separateur: "Outils" },
  { chemin: "/export", icone: "download", label: "Exporter" },
];

/**
 * Construit et injecte la sidebar dans #sidebar.
 */
function initSidebar() {
  const sidebar = document.getElementById("sidebar");

  const html = LIENS.map(item => {
    if (item.separateur) return `<div class="nav-separator">${item.separateur}</div>`;
    return `
      <a class="nav-item" data-chemin="${item.chemin}">
        <i data-feather="${item.icone}"></i> ${item.label}
      </a>
    `;
  }).join("");

  sidebar.innerHTML = `<nav class="sidebar-nav">${html}</nav>`;

  sidebar.querySelectorAll(".nav-item").forEach(lien => {
    lien.addEventListener("click", () => naviguerVers(lien.dataset.chemin));
  });

  if (typeof feather !== "undefined") feather.replace();
  mettreAJourLienActif();
}

/**
 * Met en surbrillance le lien correspondant a l'URL actuelle.
 * A appeler apres chaque navigation.
 */
function mettreAJourLienActif() {
  const chemin = window.location.pathname;
  document.querySelectorAll("#sidebar .nav-item").forEach(lien => {
    lien.classList.toggle("active", lien.dataset.chemin === chemin);
  });
}

export { initSidebar, mettreAJourLienActif };