/**
 * main.js — Point d'entrée unique de l'application Atlas Numérique.
 * Orchestre le routage, la sidebar et les interactions UI de base.
 */

// ═══════════════════════════════════════════════════════════════
// 1. IMPORTS DES MODULES
// ═══════════════════════════════════════════════════════════════

import { enregistrerRoute, initRouter } from "./core/router.js";
import { initSidebar, mettreAJourLienActif } from "./components/sidebar.js";

// Pages (importées une seule fois, exécutées au moment de la navigation)
import { afficherPageCarte } from "./pages/carte-page.js";
import { afficherPageImport } from "./pages/import.js";
import {
  afficherPageRegions, afficherPageCommunes, afficherPageVillages, afficherPageLieux,
  afficherPageChefferies, afficherPageMarches, afficherPageEthnies,
  afficherPageCooperatives, afficherPageExercices,
} from "./pages/pages-tableau.js";

// ═══════════════════════════════════════════════════════════════
// 2. ENREGISTREMENT DES ROUTES
//  ATTENTION : Aucun espace superflu dans les chemins !
// ═══════════════════════════════════════════════════════════════

enregistrerRoute("/", afficherPageCarte);
enregistrerRoute("/regions", afficherPageRegions);
enregistrerRoute("/communes", afficherPageCommunes);
enregistrerRoute("/villages", afficherPageVillages);
enregistrerRoute("/lieux", afficherPageLieux);
enregistrerRoute("/chefferies", afficherPageChefferies);
enregistrerRoute("/marches", afficherPageMarches);
enregistrerRoute("/ethnies", afficherPageEthnies);
enregistrerRoute("/cooperatives", afficherPageCooperatives);
enregistrerRoute("/exercices", afficherPageExercices);
enregistrerRoute("/import", afficherPageImport);

// ═══════════════════════════════════════════════════════════════
// 3. INITIALISATION DE L'APPLICATION
// ═══════════════════════════════════════════════════════════════

// Génère dynamiquement la navigation latérale
initSidebar();

// Active le routeur et charge la page correspondant à l'URL actuelle
initRouter();

// ═══════════════════════════════════════════════════════════════
// 4. INTERACTIONS UI (HAMBURGER & OVERLAY)
// Enveloppé dans DOMContentLoaded pour garantir que le HTML est présent
// ═══════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");

  //  Clic sur le hamburger : ouvre/ferme la sidebar + affiche l'overlay
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      overlay?.classList.toggle("active");
    });
  }

  // Clic sur l'overlay : referme la sidebar
  if (overlay) {
    overlay.addEventListener("click", () => {
      sidebar.classList.remove("open");
      overlay.classList.remove("active");
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// 5. SYNCHRONISATION HISTORIQUE NAVIGATEUR ↔ SIDEBAR
// ═══════════════════════════════════════════════════════════════

// Met à jour le lien actif quand l'utilisateur utilise les boutons Précédent/Suivant
window.addEventListener("popstate", mettreAJourLienActif);