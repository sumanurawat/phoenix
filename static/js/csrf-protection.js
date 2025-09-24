/**
 * Universal CSRF Protection for Phoenix AI Platform
 * 
 * This script automatically handles CSRF tokens for all fetch requests
 * and provides utilities for forms and other CSRF-protected operations.
 */

class PhoenixCSRF {
    constructor() {
        this.token = null;
        this.init();
    }

    /**
     * Initialize CSRF protection
     */
    init() {
        this.loadToken();
        this.setupFetchInterceptor();
        this.setupFormHandler();
    }

    /**
     * Load CSRF token from various sources
     */
    loadToken() {
        // Try meta tag first
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            this.token = metaToken.getAttribute('content');
            return;
        }

        // Try response header
        const headerToken = document.querySelector('meta[name="X-CSRF-Token"]');
        if (headerToken) {
            this.token = headerToken.getAttribute('content');
            return;
        }

        // Try to get from a previous request
        this.token = this.getTokenFromStorage();
    }

    /**
     * Get token from localStorage (fallback)
     */
    getTokenFromStorage() {
        try {
            return localStorage.getItem('phoenix_csrf_token');
        } catch (e) {
            return null;
        }
    }

    /**
     * Store token in localStorage
     */
    storeToken(token) {
        try {
            localStorage.setItem('phoenix_csrf_token', token);
            this.token = token;
        } catch (e) {
            // Ignore storage errors
        }
    }

    /**
     * Get current CSRF token
     */
    getToken() {
        return this.token;
    }

    /**
     * Setup fetch interceptor to automatically add CSRF tokens
     */
    setupFetchInterceptor() {
        const originalFetch = window.fetch;
        const csrf = this;

        window.fetch = function(url, options = {}) {
            // Only add CSRF for same-origin requests
            if (csrf.isSameOrigin(url)) {
                options = csrf.addCSRFToRequest(options);
            }

            // Call original fetch and handle CSRF token updates
            return originalFetch.call(this, url, options).then(response => {
                csrf.extractTokenFromResponse(response);
                return response;
            });
        };
    }

    /**
     * Check if URL is same-origin
     */
    isSameOrigin(url) {
        if (typeof url === 'string') {
            return url.startsWith('/') || url.startsWith(window.location.origin);
        }
        return true; // Assume same-origin for non-string URLs
    }

    /**
     * Add CSRF token to request options
     */
    addCSRFToRequest(options) {
        const method = (options.method || 'GET').toUpperCase();
        
        // Only add CSRF for state-changing methods
        if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            return options;
        }

        if (!this.token) {
            console.warn('Phoenix CSRF: No CSRF token available for request');
            return options;
        }

        // Add header
        options.headers = options.headers || {};
        options.headers['X-CSRF-Token'] = this.token;

        // Also add to body if it's JSON
        if (options.body && typeof options.body === 'string') {
            try {
                const data = JSON.parse(options.body);
                data.csrf_token = this.token;
                options.body = JSON.stringify(data);
            } catch (e) {
                // Not JSON, ignore
            }
        } else if (options.body instanceof FormData) {
            options.body.append('csrf_token', this.token);
        }

        return options;
    }

    /**
     * Extract updated CSRF token from response headers
     */
    extractTokenFromResponse(response) {
        const newToken = response.headers.get('X-CSRF-Token');
        if (newToken && newToken !== this.token) {
            this.storeToken(newToken);
            this.updateMetaTags(newToken);
        }
    }

    /**
     * Update meta tags with new token
     */
    updateMetaTags(token) {
        let metaTag = document.querySelector('meta[name="csrf-token"]');
        if (!metaTag) {
            metaTag = document.createElement('meta');
            metaTag.name = 'csrf-token';
            document.head.appendChild(metaTag);
        }
        metaTag.content = token;
    }

    /**
     * Setup form handler to automatically add CSRF tokens
     */
    setupFormHandler() {
        const csrf = this;

        // Handle form submissions
        document.addEventListener('submit', function(event) {
            const form = event.target;
            if (form.tagName !== 'FORM') return;

            // Skip if method is GET
            const method = (form.method || 'get').toLowerCase();
            if (method === 'get') return;

            // Skip if already has CSRF token
            if (form.querySelector('input[name="csrf_token"]')) return;

            // Add CSRF token
            csrf.addCSRFToForm(form);
        });
    }

    /**
     * Add CSRF token to form
     */
    addCSRFToForm(form) {
        if (!this.token) {
            console.warn('Phoenix CSRF: No CSRF token available for form');
            return;
        }

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = this.token;
        form.appendChild(input);
    }

    /**
     * Manually add CSRF token to any element
     */
    addTokenToElement(element, method = 'data') {
        if (!this.token) return false;

        switch (method) {
            case 'data':
                element.dataset.csrfToken = this.token;
                break;
            case 'value':
                if (element.tagName === 'INPUT') {
                    element.value = this.token;
                }
                break;
            case 'content':
                element.textContent = this.token;
                break;
        }
        return true;
    }

    /**
     * Get CSRF parameters for manual use
     */
    getCSRFParams() {
        return {
            'X-CSRF-Token': this.token,
            csrf_token: this.token
        };
    }

    /**
     * Refresh CSRF token from server
     */
    async refreshToken() {
        try {
            const response = await fetch('/api/csrf-token', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (response.ok) {
                this.extractTokenFromResponse(response);
                return true;
            }
        } catch (e) {
            console.error('Phoenix CSRF: Failed to refresh token', e);
        }
        return false;
    }
}

// Initialize global CSRF protection
const phoenixCSRF = new PhoenixCSRF();

// Export for manual usage
window.PhoenixCSRF = PhoenixCSRF;
window.phoenixCSRF = phoenixCSRF;

// jQuery compatibility (if jQuery is loaded)
if (typeof $ !== 'undefined') {
    $(document).ajaxSend(function(event, xhr, settings) {
        if (phoenixCSRF.isSameOrigin(settings.url)) {
            const token = phoenixCSRF.getToken();
            if (token) {
                xhr.setRequestHeader('X-CSRF-Token', token);
            }
        }
    });
}

console.log('🔐 Phoenix CSRF Protection initialized');