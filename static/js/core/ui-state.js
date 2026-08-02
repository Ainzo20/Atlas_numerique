/**
 * ui-state.js — Point d'entree unique pour l'affichage conditionnel
 * selon l'etat de connexion (admin / visiteur).
 * Injecte dynamiquement le contenu de la topbar.
 */

function updateUIForAuthState(session) {
    const estAdmin = !!session?.est_admin;
    const zone = document.getElementById("topbarActions");
    if (!zone) return;
  
    zone.innerHTML = estAdmin
      ? `
        <a class="topbar-link" id="btnImport" href="#"><i data-feather="upload"></i> Importer</a>
        <a class="topbar-link" id="btnLogout" href="#"><i data-feather="log-out"></i> Deconnexion</a>
      `
      : `<a class="topbar-link" id="btnLogin" href="/login"><i data-feather="log-in"></i> Connexion</a>`;
  
    if (estAdmin) {
      document.getElementById("btnImport").addEventListener("click", (e) => {
        e.preventDefault();
        import("../router.js").then(() => window.location.hash); // placeholder, cf. note plus bas
        window.dispatchEvent(new CustomEvent("naviguer-import"));
      });
      document.getElementById("btnLogout").addEventListener("click", async (e) => {
        e.preventDefault();
        await AtlasAuth.logout();
        window.location.href = "/";
      });
    }
  
    if (typeof feather !== "undefined") feather.replace();
  }
  
  export { updateUIForAuthState };