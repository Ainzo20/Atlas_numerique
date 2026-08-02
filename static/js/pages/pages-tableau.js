/**
 * pages-tableau.js — Pages de consultation en grille de fiches visuelles.
 * Regroupe : regions, communes, villages, lieux, chefferies, marches,
 * ethnies, cooperatives, exercices.
 */

import {
    getRegions, getCommunes, getVillages, getLieux,
    getChefferies, getMarches, getEthnies, getCooperatives, getExercices,
  } from "../core/api.js";
  import { construireGrilleFiches } from "../components/fiche-item.js";
  import { ouvrirPanneau, definirContenuPanneau } from "../components/panneau-lateral.js";
  
  /**
   * Squelette commun a toutes les pages de cette famille.
   * @param {string} titre
   * @param {string} sousTitre
   * @returns {string}
   */
  function enTetePage(titre, sousTitre) {
    return `
      <div class="page-header">
        <div>
          <h1 class="page-title">${titre}</h1>
          <p class="page-sub">${sousTitre}</p>
        </div>
      </div>
    `;
  }
  
  function etatChargement() {
    return `<div class="empty-state"><div class="progress-spinner" style="margin:0 auto"></div></div>`;
  }
  
  function etatVide(icone, titre, sous) {
    return `
      <div class="empty-state">
        <div class="empty-state-icon"><i data-feather="${icone}"></i></div>
        <div class="empty-state-title">${titre}</div>
        <div class="empty-state-sub">${sous}</div>
      </div>
    `;
  }
  
  // ── REGIONS ────────────────────────────────────────────────────
  async function afficherPageRegions() {
    const app = document.getElementById("app");
    app.innerHTML = enTetePage("Regions", "Hierarchie administrative") + `<div id="contenu">${etatChargement()}</div>`;
  
    const data = await getRegions();
    const contenu = document.getElementById("contenu");
    if (!data.regions?.length) {
      contenu.innerHTML = etatVide("map", "Aucune region", "Importez un fichier CSV pour commencer.");
    } else {
      contenu.innerHTML = construireGrilleFiches(data.regions, r => ({
        titre: r.nom,
        sousTitre: `${r.nb_departements} departement${r.nb_departements > 1 ? "s" : ""}`,
        icone: "map",
      }));
    }
    if (typeof feather !== "undefined") feather.replace();
  }
  
  // ── COMMUNES ───────────────────────────────────────────────────
  async function afficherPageCommunes() {
    const app = document.getElementById("app");
    app.innerHTML = enTetePage("Communes", "Toutes les communes enregistrees") + `<div id="contenu">${etatChargement()}</div>`;
  
    const data = await getCommunes();
    const contenu = document.getElementById("contenu");
    if (!data.communes?.length) {
      contenu.innerHTML = etatVide("home", "Aucune commune", "Importez un fichier CSV pour commencer.");
    } else {
      contenu.innerHTML = construireGrilleFiches(data.communes, item => ({
        titre: item.commune.nom,
        sousTitre: [item.region, item.departement].filter(Boolean).join(" · "),
        badge: item.commune.connectivite_constante ? "Connecte" : "Non connecte",
        badgeClasse: item.commune.connectivite_constante ? "badge-green" : "badge-red",
        icone: "home",
      }));
      // Clic → panneau lateral (reutilise le meme composant que la carte)
      document.querySelectorAll("#contenu .fiche-item").forEach((el, i) => {
        el.addEventListener("click", () => {
          import("../components/carte.js").then(m => m.afficherDetailCommuneExterne?.(data.communes[i].commune._id));
        });
      });
    }
    if (typeof feather !== "undefined") feather.replace();
  }
  
  // ── Fonction generique pour les sous-collections simples ────────
  function creerPageSimple({ titre, sousTitre, fetcher, cleListe, icone, mapper, iconeVide, titreVide, sousVide }) {
    return async function () {
      const app = document.getElementById("app");
      app.innerHTML = enTetePage(titre, sousTitre) + `<div id="contenu">${etatChargement()}</div>`;
  
      const data = await fetcher();
      const items = data[cleListe] || data.data || [];
      const contenu = document.getElementById("contenu");
  
      if (!items.length) {
        contenu.innerHTML = etatVide(iconeVide, titreVide, sousVide);
      } else {
        contenu.innerHTML = construireGrilleFiches(items, mapper);
      }
      if (typeof feather !== "undefined") feather.replace();
    };
  }
  
  const afficherPageVillages = creerPageSimple({
    titre: "Villages & Quartiers", sousTitre: "Toutes les localites enregistrees",
    fetcher: getVillages, cleListe: "villages", iconeVide: "map-pin",
    titreVide: "Aucun resultat", sousVide: "Aucun village ou quartier trouve.",
    mapper: v => ({
      titre: v.nom,
      sousTitre: v.chef ? `Chef : ${v.chef}` : "",
      badge: v.type === "village" ? "Village" : "Quartier",
      badgeClasse: v.type === "village" ? "badge-village" : "badge-quartier",
      icone: "map-pin",
    }),
  });
  
  const afficherPageLieux = creerPageSimple({
    titre: "Lieux", sousTitre: "Ecoles, urgences, sites touristiques et plus",
    fetcher: getLieux, cleListe: "data", iconeVide: "layers",
    titreVide: "Aucun lieu", sousVide: "Aucun lieu trouve.",
    mapper: l => ({
      titre: l.nom,
      sousTitre: l.contact || "",
      badge: l.type_nom || "",
      badgeClasse: `badge-${l.type_nom || "grey"}`,
      icone: "layers",
    }),
  });
  
  const afficherPageChefferies = creerPageSimple({
    titre: "Chefferies", sousTitre: "Chefferies et coordonnees GPS",
    fetcher: getChefferies, cleListe: "chefferies", iconeVide: "shield",
    titreVide: "Aucune chefferie", sousVide: "Aucune chefferie enregistree.",
    mapper: c => ({
      titre: c.nom,
      sousTitre: c.latitude ? `${c.latitude}, ${c.longitude}` : "",
      icone: "shield",
    }),
  });
  
  const afficherPageMarches = creerPageSimple({
    titre: "Marches", sousTitre: "Marches et jours de marche",
    fetcher: getMarches, cleListe: "marches", iconeVide: "shopping-bag",
    titreVide: "Aucun marche", sousVide: "Aucun marche enregistre.",
    mapper: m => ({
      titre: m.nom,
      sousTitre: [m.jour, m.heure_debut, m.heure_fin].filter(Boolean).join(" · "),
      icone: "shopping-bag",
    }),
  });
  
  const afficherPageEthnies = creerPageSimple({
    titre: "Ethnies", sousTitre: "Groupes ethniques repertories",
    fetcher: getEthnies, cleListe: "ethnies", iconeVide: "users",
    titreVide: "Aucune ethnie", sousVide: "Aucune ethnie enregistree.",
    mapper: e => ({ titre: e.nom, sousTitre: e.salutations || "", icone: "users" }),
  });
  
  const afficherPageCooperatives = creerPageSimple({
    titre: "Cooperatives & GIC", sousTitre: "Organisations economiques",
    fetcher: getCooperatives, cleListe: "cooperatives", iconeVide: "briefcase",
    titreVide: "Aucune cooperative", sousVide: "Aucune cooperative enregistree.",
    mapper: c => ({ titre: c.nom, icone: "briefcase" }),
  });
  
  const afficherPageExercices = creerPageSimple({
    titre: "Exercices annuels", sousTitre: "Donnees annuelles par commune",
    fetcher: getExercices, cleListe: "exercices", iconeVide: "bar-chart-2",
    titreVide: "Aucun exercice", sousVide: "Aucun exercice enregistre.",
    mapper: e => ({
      titre: e.annee || "—",
      sousTitre: e.nombre_habitants ? `${e.nombre_habitants.toLocaleString("fr-FR")} habitants` : "",
      badge: e.taux_electrification != null ? `${e.taux_electrification}% electrifie` : "",
      badgeClasse: "badge-yellow",
      icone: "bar-chart-2",
    }),
  });
  
  export {
    afficherPageRegions, afficherPageCommunes, afficherPageVillages, afficherPageLieux,
    afficherPageChefferies, afficherPageMarches, afficherPageEthnies,
    afficherPageCooperatives, afficherPageExercices,
  };