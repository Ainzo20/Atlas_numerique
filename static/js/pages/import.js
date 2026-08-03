import { postImport } from "../core/api.js";

function afficherPageImport() {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Importer un fichier CSV</h1>
        <p class="page-sub">Fichier exporte depuis KoboCollect</p>
      </div>
    </div>
    <div class="import-container">
      <div class="drop-zone" id="dropZone">
        <div class="drop-icon"><i data-feather="upload-cloud"></i></div>
        <div class="drop-title">Glisser le fichier CSV ici</div>
        <div class="drop-sub">ou</div>
        <label class="btn-primary" for="csvInput"><i data-feather="folder"></i> Parcourir</label>
        <input type="file" id="csvInput" accept=".csv" style="display:none" />
        <div class="drop-hint">Separateur ; · Encodage UTF-8 · Format KoboCollect</div>
      </div>
      <div id="importRapport" style="display:none" class="import-rapport"></div>
    </div>
  `;
  if (typeof feather !== "undefined") feather.replace();

  document.getElementById("csvInput").addEventListener("change", async (e) => {
    const fichier = e.target.files[0];
    if (!fichier) return;
    const rapportEl = document.getElementById("importRapport");
    rapportEl.style.display = "block";
    rapportEl.innerHTML = `<div class="progress-spinner" style="margin:0 auto"></div>`;

    try {
      const data = await postImport(fichier);
      rapportEl.className = "import-rapport rapport-succes";
      rapportEl.innerHTML = `
        <div class="rapport-title">Import termine</div>
        <div class="rapport-stat"><span>Succes</span><span>${data.succes}</span></div>
        <div class="rapport-stat"><span>Erreurs</span><span>${data.erreurs}</span></div>
      `;
    } catch (erreur) {
      rapportEl.className = "import-rapport rapport-erreur";
      rapportEl.innerHTML = `<div class="rapport-title">Erreur</div><p>${erreur.message}</p>`;
    }
  });
}

export { afficherPageImport };