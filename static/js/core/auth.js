// ═══════════════════════════════════════════════════════════════
// auth.js — Gestion de l'authentification par JWT Cookie
// Atlas Numérique du Cameroun
// ═══════════════════════════════════════════════════════════════

const AtlasAuth = (function() {
    'use strict';

    // Configuration
    const CONFIG = {
        API_BASE: '', // Vide = même origine
        ENDPOINTS: {
            LOGIN: '/api/login',
            LOGOUT: '/api/logout',
            ME: '/api/me'
        },
        SELECTORS: {
            ADMIN_MENU: '[data-page="import"]',
            LOGIN_FORM: '#loginForm',
            LOGIN_ERROR: '#loginError'
        }
    };

    // ═══════════════════════════════════════════════════════════
    // ÉTAT D'AUTHENTIFICATION (géré côté serveur via cookie)
    // ═══════════════════════════════════════════════════════════

    /**
     * Vérifie la session active via l'endpoint /api/me
     * @returns {Promise<Object>} { authentifie: bool, est_admin: bool, username?: string }
     */
    async function checkSession() {
        try {
            const res = await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.ME}`, {
                credentials: 'include' // Envoie le cookie atlas_session
            });
            if (!res.ok) return { authentifie: false, est_admin: false };
            return await res.json();
        } catch {
            return { authentifie: false, est_admin: false };
        }
    }

    /**
     * Affiche/masque le menu admin selon le rôle
     * @param {boolean} isAdmin - True si l'utilisateur est admin
     */
    function toggleAdminMenu(isAdmin) {
        // Delegue a ui-state.js qui gere maintenant la topbar dynamiquement
        if (typeof window.updateUIForAuthState === "function") {
            window.updateUIForAuthState({ est_admin: isAdmin });
        }
    }

    // ═══════════════════════════════════════════════════════════
    // LOGIN / LOGOUT
    // ═══════════════════════════════════════════════════════════

    /**
     * Soumet les identifiants vers /api/login
     * @param {string} username 
     * @param {string} password 
     * @returns {Promise<boolean>} True si succès, False sinon
     */
    async function login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const res = await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.LOGIN}`, {
                method: 'POST',
                body: formData,
                credentials: 'include' // Reçoit le cookie atlas_session
            });

            if (res.ok) {
                // Le backend dépose le cookie et retourne 200/302
                return true;
            } else {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Identifiants incorrects');
            }
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Déconnecte l'utilisateur via /api/logout
     * @returns {Promise<void>}
     */
    async function logout() {
        try {
            await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.LOGOUT}`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    // ═══════════════════════════════════════════════════════════
    // INTERCEPTION DES REQUÊTES FETCH
    // ═══════════════════════════════════════════════════════════

    const originalFetch = window.fetch;

    /**
     * Redéfinit fetch pour :
     * 1. Ajouter credentials: 'include' par défaut (pour les cookies)
     * 2. Gérer les erreurs 401/403 sur les routes protégées
     */
    window.fetch = async function(url, options = {}) {
        // Par défaut, inclure les cookies pour les appels API
        if (!options.credentials && url.startsWith('/api')) {
            options.credentials = 'include';
        }

        try {
            const response = await originalFetch(url, options);

            // Si 401/403 sur une route API, déconnecter et afficher un message
            if ((response.status === 401 || response.status === 403) && url.includes('/api/')) {
                console.warn(`Auth error on ${url}: ${response.status}`);
                
                // Ne pas boucler si on est déjà sur /login
                if (window.location.pathname !== '/login') {
                    sessionStorage.setItem('auth_error', JSON.stringify({
                        type: 'error',
                        text: response.status === 401 
                            ? 'Session expirée. Veuillez vous reconnecter.'
                            : 'Accès refusé.'
                    }));
                    // Optionnel : recharger pour masquer le menu admin
                    window.location.href = '/login';
                }
            }

            return response;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    };

    // ═══════════════════════════════════════════════════════════
    // UTILITAIRES D'INTERFACE
    // ═══════════════════════════════════════════════════════════

    /**
     * Affiche un message d'erreur ou de succès sur le formulaire de login
     * @param {string} type - 'error' | 'success' | 'info'
     * @param {string} text - Message à afficher
     */
    function showMessage(type, text) {
        const el = document.querySelector(CONFIG.SELECTORS.LOGIN_ERROR);
        if (el) {
            el.textContent = text;
            el.style.display = type === 'error' ? 'block' : 'none';
            el.className = `login-message ${type}`;
        }
    }

    /**
     * Affiche un message stocké en session après redirection
     */
    function displaySessionMessage() {
        const raw = sessionStorage.getItem('auth_error');
        if (raw) {
            try {
                const { type, text } = JSON.parse(raw);
                showMessage(type, text);
            } catch (e) {
                console.error('Failed to parse session message', e);
            } finally {
                sessionStorage.removeItem('auth_error');
            }
        }
    }

    /**
     * Initialise le gestionnaire de formulaire de login
     */
    function bindLoginForm() {
        const form = document.querySelector(CONFIG.SELECTORS.LOGIN_FORM);
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const username = form.querySelector('[name="username"]')?.value.trim();
            const password = form.querySelector('[name="password"]')?.value;

            if (!username || !password) {
                showMessage('error', 'Veuillez remplir tous les champs');
                return;
            }

            // UI loading state
            if (btn) {
                btn.disabled = true;
                btn.dataset.originalText = btn.textContent;
                btn.textContent = 'Connexion...';
            }
            showMessage('info', '');

            try {
                const success = await login(username, password);
                if (success) {
                    // Redirection vers l'accueil après login réussi
                    window.location.href = '/';
                }
            } catch (error) {
                showMessage('error', error.message || 'Échec de connexion');
            } finally {
                if (btn && btn.dataset.originalText) {
                    btn.disabled = false;
                    btn.textContent = btn.dataset.originalText;
                }
            }
        });
    }

    // ═══════════════════════════════════════════════════════════
    // API PUBLIQUE
    // ═══════════════════════════════════════════════════════════

    return {
        // État
        checkSession,
        toggleAdminMenu,
        
        // Actions
        login,
        logout,
        
        // UI
        showMessage,
        displaySessionMessage,
        bindLoginForm,
        
        // Config (pour débogage ou extension)
        CONFIG
    };

})();

// ═══════════════════════════════════════════════════════════════
// INITIALISATION AUTOMATIQUE
// ═══════════════════════════════════════════════════════════════

// Au chargement de la page de login : afficher les messages session + binder le form
if (window.location.pathname === '/login') {
    document.addEventListener('DOMContentLoaded', () => {
        AtlasAuth.displaySessionMessage();
        AtlasAuth.bindLoginForm();
    });
}

// Sur les autres pages : vérifier la session au chargement pour afficher/masquer le menu admin
if (window.location.pathname !== '/login') {
    document.addEventListener('DOMContentLoaded', async () => {
        const session = await AtlasAuth.checkSession();
        if (typeof window.updateUIForAuthState === "function") {
            window.updateUIForAuthState(session);
        }
    });
}