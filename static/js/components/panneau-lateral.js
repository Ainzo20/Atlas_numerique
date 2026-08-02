/**
 * panneau-lateral.js — Panneau escamotable affichant les details
 * d'un element clique sur la carte (commune, region, lieu...).
 */

let panneauInitialise = false;

/**
 * Cree le panneau dans le DOM s'il n'existe pas deja.
 * Appele une seule fois, au premier usage.
 */
function assurerPanneauExiste() {
  if (panneauInitialise) return;

  const panneau = document.createElement("div");
  panneau.id = "panneauLateral";
  panneau.className = "panneau-lateral";
  panneau.innerHTML = `
    <button class="panneau-fermer" id="panneauFermer">
      <i data-feather="x"></i>
    </button>
    <div class="panneau-contenu" id="panneauContenu">
      <div class="empty-state">
        <div class="progress-spinner" style="margin:0 auto"></div>
      </div>
    </div>
  `;
  document.body.appendChild(panneau);

  document.getElementById("panneauFermer").addEventListener("click", fermerPanneau);

  panneauInitialise = true;
}

/**
 * Ouvre le panneau avec une animation de glissement.
 */
function ouvrirPanneau() {
  assurerPanneauExiste();
  const panneau = document.getElementById("panneauLateral");
  // Force un reflow avant d'ajouter la classe, pour garantir que la transition CSS joue
  requestAnimationFrame(() => panneau.classList.add("ouvert"));
}

/**
 * Ferme le panneau.
 */
function fermerPanneau() {
  const panneau = document.getElementById("panneauLateral");
  if (panneau) panneau.classList.remove("ouvert");
}

/**
 * Remplace le contenu du panneau (loading, erreur, ou donnees).
 * @param {string} html
 */
function definirContenuPanneau(html) {
  const contenu = document.getElementById("panneauContenu");
  if (contenu) contenu.innerHTML = html;
  if (typeof feather !== "undefined") feather.replace();
}

export { ouvrirPanneau, fermerPanneau, definirContenuPanneau };