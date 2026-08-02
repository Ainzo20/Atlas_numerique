/**
 * api.js — Centralise tous les appels reseau vers le backend FastAPI.
 * Aucune logique d'affichage ici, uniquement fetch + retour de donnees.
 */

const API_BASE = "";

async function getJSON(url) {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`Erreur ${res.status} sur ${url}`);
  return res.json();
}

const getSante   = () => getJSON("/health");
const getStats   = () => getJSON("/stats");

const getRegions       = () => getJSON("/regions");
const getRegionDetail  = (id) => getJSON(`/regions/${id}`);
const getDepartementDetail     = (id) => getJSON(`/departements/${id}`);
const getArrondissementDetail  = (id) => getJSON(`/arrondissements/${id}`);

const getCommunes = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return getJSON(`/communes${query ? `?${query}` : ""}`);
};
const getCommuneDetail = (id) => getJSON(`/communes/${id}`);

const getVillages      = () => getJSON("/villages");
const getChefferies    = () => getJSON("/chefferies");
const getMarches       = () => getJSON("/marches");
const getEthnies       = () => getJSON("/ethnies");
const getCooperatives  = () => getJSON("/cooperatives");
const getExercices     = () => getJSON("/exercices");

const getLieux = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return getJSON(`/lieux${query ? `?${query}` : ""}`);
};
const getLieuxTypes = () => getJSON("/lieux/types");

async function postImport(fichier) {
  const formData = new FormData();
  formData.append("fichier", fichier);
  const res = await fetch(`${API_BASE}/import`, { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) throw Object.assign(new Error(data.detail || "Erreur d'import"), { data });
  return data;
}

function urlExport(format, region = "") {
  let url = `${API_BASE}/export?format=${format}`;
  if (region) url += `&region=${encodeURIComponent(region)}`;
  return url;
}

export {
  getSante, getStats,
  getRegions, getRegionDetail, getDepartementDetail, getArrondissementDetail,
  getCommunes, getCommuneDetail,
  getVillages, getChefferies, getMarches, getEthnies, getCooperatives, getExercices,
  getLieux, getLieuxTypes,
  postImport, urlExport,
};