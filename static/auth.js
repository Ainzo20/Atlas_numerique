// ═══════════════════════════════════════════════════════════════
// auth.js — Gestion de l'authentification par API Key
// Atlas Numérique du Cameroun
// ═══════════════════════════════════════════════════════════════

const AtlasAuth = (function() {
    'use strict';

    // Configuration
    const CONFIG = {
        STORAGE_KEY: 'atlas_api_key',
        LOGIN_URL: '/login',
        API_BASE_URL: '' // URL de base de l'API (vide si même domaine)
    };

    // ═══════════════════════════════════════════════════════════
    // GESTION DE LA CLÉ API
    // ═══════════════════════════════════════════════════════════

    /**
     * Récupère la clé API depuis le stockage local
     * @returns {string|null} La clé API ou null si absente
     */
    function getApiKey() {
        try {
            return localStorage.getItem(CONFIG.STORAGE_KEY);
        } catch (error) {
            console.error('Erreur lors de la lecture de la clé API:', error);
            return null;
        }
    }

    /**
     * Sauvegarde la clé API dans le stockage local
     * @param {string} key - La clé API à sauvegarder
     */
    function setApiKey(key) {
        try {
            if (key && typeof key === 'string') {
                localStorage.setItem(CONFIG.STORAGE_KEY, key);
            }
        } catch (error) {
            console.error('Erreur lors de la sauvegarde de la clé API:', error);
        }
    }

    /**
     * Supprime la clé API (déconnexion)
     */
    function clearApiKey() {
        try {
            localStorage.removeItem(CONFIG.STORAGE_KEY);
        } catch (error) {
            console.error('Erreur lors de la suppression de la clé API:', error);
        }
    }

    /**
     * Vérifie si l'utilisateur est authentifié
     * @returns {boolean} True si une clé API est présente
     */
    function isAuthenticated() {
        const key = getApiKey();
        return key !== null && key.length > 0;
    }

    // ═══════════════════════════════════════════════════════════
    // INTERCEPTION DES REQUÊTES FETCH
    // ═══════════════════════════════════════════════════════════

    // Sauvegarde de la fonction fetch originale
    const originalFetch = window.fetch;

    /**
     * Redéfinit la fonction fetch pour ajouter automatiquement le header X-API-Key
     * et gérer les erreurs d'authentification
     */
    window.fetch = async function(url, options = {}) {
        // Initialiser les headers si absents
        if (!options.headers) {
            options.headers = {};
        }

        // Convertir Headers en objet si nécessaire
        if (options.headers instanceof Headers) {
            const headersObj = {};
            options.headers.forEach((value, key) => {
                headersObj[key] = value;
            });
            options.headers = headersObj;
        }

        // Ajouter la clé API si elle existe et si le header n'est pas déjà défini
        const apiKey = getApiKey();
        if (apiKey && !options.headers['X-API-Key']) {
            options.headers['X-API-Key'] = apiKey;
        }

        try {
            const response = await originalFetch(url, options);

            // Si 401 ou 403, rediriger vers la page de connexion
            if (response.status === 401 || response.status === 403) {
                console.warn('Authentification requise ou échouée. Redirection vers /login');
                clearApiKey();
                
                // Ne pas rediriger si on est déjà sur la page de login
                if (window.location.pathname !== CONFIG.LOGIN_URL) {
                    // Afficher un message avant la redirection
                    const message = response.status === 401 
                        ? 'Session expirée. Veuillez vous reconnecter.'
                        : 'Accès refusé. Veuillez vérifier vos permissions.';
                    
                    // Stocker le message pour l'afficher après redirection
                    sessionStorage.setItem('login_message', JSON.stringify({
                        type: 'error',
                        text: message
                    }));
                    
                    window.location.href = CONFIG.LOGIN_URL;
                }
            }

            return response;
        } catch (error) {
            console.error('Erreur réseau:', error);
            throw error;
        }
    };

    // ═══════════════════════════════════════════════════════════
    // PROTECTION DES PAGES
    // ═══════════════════════════════════════════════════════════

    /**
     * Vérifie l'authentification au chargement de la page
     * À appeler au début de chaque page protégée
     * @returns {boolean} True si authentifié, sinon redirige vers /login
     */
    function requireAuth() {
        if (!isAuthenticated()) {
            console.log('Non authentifié. Redirection vers /login');
            window.location.href = CONFIG.LOGIN_URL;
            return false;
        }
        return true;
    }

    /**
     * Affiche les informations de l'utilisateur connecté
     * Cherche un élément avec l'id 'user-info' et y affiche le préfixe de la clé
     */
    function displayUserInfo() {
        const apiKey = getApiKey();
        if (apiKey) {
            const prefix = apiKey.substring(0, 20) + '...';
            const userInfoElement = document.getElementById('user-info');
            if (userInfoElement) {
                userInfoElement.textContent = `Connecté : ${prefix}`;
            }
        }
    }

    /**
     * Gère la déconnexion
     * Efface la clé et redirige vers la page de connexion
     */
    function logout() {
        if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
            clearApiKey();
            window.location.href = CONFIG.LOGIN_URL;
        }
    }

    /**
     * Affiche un message stocké en session (après redirection depuis une autre page)
     * À appeler sur la page de login
     */
    function displaySessionMessage() {
        const messageData = sessionStorage.getItem('login_message');
        if (messageData) {
            try {
                const { type, text } = JSON.parse(messageData);
                
                // Attendre que le DOM soit prêt
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', () => {
                        showMessage(type, text);
                    });
                } else {
                    showMessage(type, text);
                }
                
                sessionStorage.removeItem('login_message');
            } catch (error) {
                console.error('Erreur lors de l\'affichage du message:', error);
            }
        }
    }

    /**
     * Affiche un message sur la page de login
     * @param {string} type - Type de message ('error', 'success', 'info')
     * @param {string} text - Texte du message
     */
    function showMessage(type, text) {
        const messageDiv = document.getElementById('message');
        if (messageDiv) {
            const icons = {
                error: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
                success: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
                info: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
            };

            messageDiv.className = `login-message ${type} show`;
            messageDiv.innerHTML = `${icons[type] || ''}<span>${text}</span>`;
        }
    }

    // ═══════════════════════════════════════════════════════════
    // API PUBLIQUE
    // ═══════════════════════════════════════════════════════════

    return {
        getApiKey,
        setApiKey,
        clearApiKey,
        isAuthenticated,
        requireAuth,
        displayUserInfo,
        logout,
        displaySessionMessage,
        showMessage
    };

})();

// Afficher les messages de session au chargement de la page de login
if (window.location.pathname === '/login') {
    AtlasAuth.displaySessionMessage();
}