/**
 * router.js — Routeur cote client base sur history.pushState().
 *
 * Fonctionnement :
 * - On enregistre des routes avec enregistrerRoute(chemin, handler)
 * - naviguerVers(chemin) change l'URL SANS recharger la page et appelle le handler
 * - Le bouton retour du navigateur est gere via popstate
 */

const routes = [];

/**
 * Enregistre une route.
 * @param {string} motif - ex: "/communes/:id" (":id" = parametre dynamique)
 * @param {(params: object) => void} handler - fonction appelee avec les parametres extraits
 */
function enregistrerRoute(motif, handler) {
  const regex = new RegExp(
    "^" + motif.replace(/:[^/]+/g, "([^/]+)") + "$"
  );
  const nomsParams = (motif.match(/:[^/]+/g) || []).map(p => p.slice(1));
  routes.push({ regex, nomsParams, handler });
}

/**
 * Trouve et execute la route correspondant au chemin donne.
 * @param {string} chemin
 */
function resoudreRoute(chemin) {
  for (const route of routes) {
    const match = chemin.match(route.regex);
    if (match) {
      const params = {};
      route.nomsParams.forEach((nom, i) => { params[nom] = match[i + 1]; });
      route.handler(params);
      return;
    }
  }
  console.warn(`Aucune route trouvee pour : ${chemin}`);
}

/**
 * Navigue vers un chemin sans recharger la page.
 * @param {string} chemin
 */
function naviguerVers(chemin) {
    window.history.pushState({}, "", chemin);
    resoudreRoute(chemin);
    window.dispatchEvent(new Event("popstate")); // synchronise la sidebar aussi sur navigation directe
  }

/**
 * Initialise le routeur : gere le chargement initial et le bouton retour.
 */
function initRouter() {
  window.addEventListener("popstate", () => {
    resoudreRoute(window.location.pathname);
  });
  resoudreRoute(window.location.pathname);
}

export { enregistrerRoute, naviguerVers, initRouter };