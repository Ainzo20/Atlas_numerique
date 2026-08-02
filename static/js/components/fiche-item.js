/**
 * fiche-item.js — Genere une carte visuelle reutilisable pour les listes
 * (villages, lieux, chefferies, marches, ethnies, cooperatives...).
 */

/**
 * Construit le HTML d'une carte visuelle generique.
 * @param {object} options
 * @param {string} options.titre
 * @param {string} [options.sousTitre]
 * @param {string} [options.badge] - texte du badge (ex: type)
 * @param {string} [options.badgeClasse] - classe CSS du badge (ex: "badge-green")
 * @param {string} [options.icone] - nom icone feather
 * @param {() => void} [options.onClick]
 * @returns {string} HTML de la carte
 */
function construireFicheItem({ titre, sousTitre = "", badge = "", badgeClasse = "badge-grey", icone = "map-pin" }) {
    return `
      <div class="fiche-item">
        <div class="fiche-item-icone"><i data-feather="${icone}"></i></div>
        <div class="fiche-item-corps">
          <div class="fiche-item-titre">${titre}</div>
          ${sousTitre ? `<div class="fiche-item-sous">${sousTitre}</div>` : ""}
          ${badge ? `<span class="badge ${badgeClasse}">${badge}</span>` : ""}
        </div>
      </div>
    `;
  }
  
  /**
   * Genere la grille complete a partir d'une liste d'items.
   * @param {Array<object>} items - donnees brutes
   * @param {(item: object) => object} mapper - transforme un item en {titre, sousTitre, badge, badgeClasse, icone}
   * @returns {string} HTML de la grille
   */
  function construireGrilleFiches(items, mapper) {
    if (!items || items.length === 0) return "";
    return `<div class="fiches-grille">${items.map(item => construireFicheItem(mapper(item))).join("")}</div>`;
  }
  
  export { construireFicheItem, construireGrilleFiches };