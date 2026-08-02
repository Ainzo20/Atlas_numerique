/**
 * carte-page.js — Page d'accueil : affiche la carte interactive.
 */

import { initCarte } from "../components/carte.js";

/**
 * Affiche la page carte dans le conteneur #app.
 */
function afficherPageCarte() {
    const app = document.getElementById("app");
    app.innerHTML = `<div id="carteConteneur" class="carte-plein-ecran"></div>`;
    initCarte("carteConteneur");
  }

export { afficherPageCarte };