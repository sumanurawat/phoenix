/**
 * Feature Gating JavaScript Library
 * 
 * Provides client-side feature access control and UI state management
 * based on user subscription tier and feature availability.
 */

class FeatureGatekeeper {
    constructor() {
        this.features = {};
        this.tier = 'free';
        this.models = [];
        this.upgradeUrl = '/subscription';
        this.initialized = false;
        
        // Cache for 5 minutes to avoid excessive API calls
        this.cacheTimeout = 5 * 60 * 1000;
        this.lastFetch = 0;
    }

    /**
     * Initialize the gatekeeper by fetching user feature data
     */
    async init() {
        try {
            await this.fetchUserFeatures();
            this.setupEventListeners();
            this.updateUI();
            this.initialized = true;
            console.log('FeatureGatekeeper initialized successfully');
        } catch (error) {
            console.error('Failed to initialize FeatureGatekeeper:', error);
            // Fallback to restrictive mode
            this.tier = 'free';
            this.features = {};
            this.models = ['gemini-1.0-pro', 'gpt-3.5-turbo'];
        }
    }

    /**
     * Fetch user feature access data from API
     */
    async fetchUserFeatures() {
        const now = Date.now();
        
        // Use cache if recent
        if (this.initialized && (now - this.lastFetch) < this.cacheTimeout) {
            return;
        }

        const response = await fetch('/api/user/features', {
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.success) {
            this.features = data.data.features || {};
            this.tier = data.data.tier || 'free';
            this.models = data.data.models || [];
            this.lastFetch = now;
        } else {
            throw new Error('API returned error');
        }
    }

    /**
     * Check if user can access a feature
     */
    canAccessFeature(featureId) {
        const feature = this.features[featureId];
        return feature && feature.accessible;
    }

    /**
     * Get feature usage status
     */
    getFeatureStatus(featureId) {
        const feature = this.features[featureId];
        if (!feature) {
            return {
                accessible: false,
                reason: 'Feature not found'
            };
        }

        return {
            accessible: feature.accessible,
            reason: feature.reason || null,
            limits: feature.limits || null,
            usage: feature.limits ? {
                current: feature.limits.current || 0,
                limit: feature.limits.limit || -1,
                remaining: feature.limits.remaining || -1
            } : null
        };
    }

    /**
     * Check if user can access a model
     */
    canAccessModel(modelName) {
        return this.models.includes(modelName);
    }

    /**
     * Get available models for user
     */
    getAvailableModels() {
        return [...this.models];
    }

    /**
     * Show upgrade prompt for a feature
     */
    showUpgradePrompt(featureId, customMessage = null) {
        const feature = this.features[featureId];
        const featureName = feature ? feature.name : featureId;
        
        const message = customMessage || 
            `${featureName} requires a premium subscription. Upgrade now to unlock this feature and many more!`;

        // Create modal or use existing notification system
        this.showUpgradeModal(message, featureName);
    }

    /**
     * Show upgrade modal
     */
    showUpgradeModal(message, featureName) {
        // Check if modal already exists
        let modal = document.getElementById('upgrade-modal');
        
        if (!modal) {
            // Create modal
            modal = document.createElement('div');
            modal.id = 'upgrade-modal';
            modal.className = 'feature-gate-modal';
            modal.innerHTML = `
                <div class="modal-backdrop"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🚀 Upgrade Required</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p id="upgrade-message"></p>
                        <div class="upgrade-benefits">
                            <h4>Premium Benefits:</h4>
                            <ul id="upgrade-benefits-list">
                                <li>Unlimited access to all features</li>
                                <li>Premium AI models (GPT-4, Claude)</li>
                                <li>Advanced analytics</li>
                                <li>Priority support</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="upgrade-btn" class="btn btn-primary">Upgrade Now</button>
                        <button id="upgrade-cancel" class="btn btn-secondary">Maybe Later</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Add event listeners
            modal.querySelector('.modal-close').onclick = () => this.hideUpgradeModal();
            modal.querySelector('#upgrade-cancel').onclick = () => this.hideUpgradeModal();
            modal.querySelector('#upgrade-btn').onclick = () => {
                window.location.href = this.upgradeUrl;
            };
            modal.querySelector('.modal-backdrop').onclick = () => this.hideUpgradeModal();
        }

        // Update content
        modal.querySelector('#upgrade-message').textContent = message;
        
        // Show modal
        modal.style.display = 'block';
        document.body.classList.add('modal-open');
    }

    /**
     * Hide upgrade modal
     */
    hideUpgradeModal() {
        const modal = document.getElementById('upgrade-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        }
    }

    /**
     * Disable UI element with upgrade prompt
     */
    disableElement(element, featureId, showTooltip = true) {
        element.disabled = true;
        element.classList.add('feature-gated');
        
        if (showTooltip) {
            const feature = this.features[featureId];
            const message = feature ? 
                `${feature.name} requires premium subscription` : 
                'This feature requires premium subscription';
            
            element.title = message;
            element.setAttribute('data-feature-gate', featureId);
        }

        // Add click handler for upgrade prompt
        element.addEventListener('click', (e) => {
            if (element.disabled) {
                e.preventDefault();
                e.stopPropagation();
                this.showUpgradePrompt(featureId);
            }
        });
    }

    /**
     * Enable UI element
     */
    enableElement(element) {
        element.disabled = false;
        element.classList.remove('feature-gated');
        element.removeAttribute('title');
        element.removeAttribute('data-feature-gate');
    }

    /**
     * Update UI elements based on feature access
     */
    updateUI() {
        // Update elements with data-feature attribute
        document.querySelectorAll('[data-feature]').forEach(element => {
            const featureId = element.getAttribute('data-feature');
            
            if (this.canAccessFeature(featureId)) {
                this.enableElement(element);
                element.classList.add('feature-available');
                element.classList.remove('feature-restricted');
            } else {
                this.disableElement(element, featureId);
                element.classList.add('feature-restricted');
                element.classList.remove('feature-available');
            }
        });

        // Update model selectors
        document.querySelectorAll('[data-model-selector]').forEach(selector => {
            this.updateModelSelector(selector);
        });

        // Update tier indicators
        document.querySelectorAll('[data-tier-indicator]').forEach(indicator => {
            indicator.textContent = this.tier.toUpperCase();
            indicator.className = `tier-indicator tier-${this.tier}`;
        });
    }

    /**
     * Update model selector dropdown
     */
    updateModelSelector(selector) {
        const availableModels = this.getAvailableModels();
        
        // Clear existing options
        selector.innerHTML = '';
        
        // Add available models
        availableModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = this.getModelDisplayName(model);
            selector.appendChild(option);
        });

        // Add premium models as disabled options for free users
        if (this.tier === 'free') {
            const premiumModels = ['gpt-4', 'claude-3-opus', 'gemini-1.5-pro'];
            premiumModels.forEach(model => {
                if (!availableModels.includes(model)) {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = `${this.getModelDisplayName(model)} (Premium)`;
                    option.disabled = true;
                    option.classList.add('premium-option');
                    selector.appendChild(option);
                }
            });
        }
    }

    /**
     * Get display name for model
     */
    getModelDisplayName(model) {
        const displayNames = {
            'gpt-4': 'GPT-4',
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo',
            'claude-3-opus': 'Claude 3 Opus',
            'claude-3-sonnet': 'Claude 3 Sonnet',
            'claude-3-haiku': 'Claude 3 Haiku',
            'gemini-1.5-pro': 'Gemini 1.5 Pro',
            'gemini-1.5-flash': 'Gemini 1.5 Flash',
            'gemini-1.0-pro': 'Gemini 1.0 Pro',
            'grok-beta': 'Grok Beta'
        };
        return displayNames[model] || model;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Listen for feature gate clicks
        document.addEventListener('click', (e) => {
            const element = e.target.closest('[data-feature-gate]');
            if (element && element.disabled) {
                e.preventDefault();
                e.stopPropagation();
                const featureId = element.getAttribute('data-feature-gate');
                this.showUpgradePrompt(featureId);
            }
        });

        // Listen for subscription changes (via custom events)
        document.addEventListener('subscription-updated', () => {
            this.lastFetch = 0; // Force refresh
            this.init();
        });
    }

    /**
     * Refresh feature data
     */
    async refresh() {
        this.lastFetch = 0; // Force refresh
        await this.fetchUserFeatures();
        this.updateUI();
    }
}

// Global instance
window.featureGatekeeper = new FeatureGatekeeper();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.featureGatekeeper.init();
    });
} else {
    window.featureGatekeeper.init();
}

// Utility functions for templates
window.FeatureGate = {
    canAccess: (featureId) => window.featureGatekeeper.canAccessFeature(featureId),
    getStatus: (featureId) => window.featureGatekeeper.getFeatureStatus(featureId),
    showUpgrade: (featureId, message) => window.featureGatekeeper.showUpgradePrompt(featureId, message),
    refresh: () => window.featureGatekeeper.refresh()
};