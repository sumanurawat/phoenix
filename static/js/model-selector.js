/**
 * Reusable Model Selection Component
 * Provides consistent model selection across all Phoenix AI pages
 */

class ModelSelector {
    constructor(options = {}) {
        this.providerSelectId = options.providerSelectId || 'modelProvider';
        this.modelSelectId = options.modelSelectId || 'modelName';
        // Thinking mode removed for simplicity - will be re-implemented later
        this.onModelChange = options.onModelChange || null;
        
        // Available models configuration
        this.availableModels = {
            gemini: [
                {id: 'gemini-1.5-flash-8b', name: 'Gemini 1.5 Flash 8B (Fast & Cost-Effective)', cost: 'Very Low', prodAllowed: true},
                {id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro (Highest Quality, $$$)', cost: 'High', prodAllowed: true},
                {id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash (High Quality, $)', cost: 'Low', prodAllowed: true},
                {id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro (Good Quality, $$)', cost: 'Medium', prodAllowed: true},
                {id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash (Good Quality, $)', cost: 'Low', prodAllowed: true}
            ],
            claude: [
                {id: 'claude-opus-4-20250514', name: 'Claude 4 Opus (World\'s Best Coding Model, $$$$)', cost: 'Very High', prodAllowed: true},
                {id: 'claude-sonnet-4-20250514', name: 'Claude 4 Sonnet (Latest & Best Balance, $$$)', cost: 'High', prodAllowed: true},
                {id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet (High Quality, $$)', cost: 'Medium', prodAllowed: true},
                {id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku (Fast & Affordable, $)', cost: 'Low', prodAllowed: true},
                {id: 'claude-3-opus-20240229', name: 'Claude 3 Opus (Premium, $$$)', cost: 'High', prodAllowed: true}
            ],
            grok: [
                {id: 'grok-4', name: 'Grok 4 (Real-time Search, $$$)', cost: 'High', prodAllowed: true},
                {id: 'grok-2-1212', name: 'Grok 2-1212 (Production Model, $$)', cost: 'Medium', prodAllowed: true},
                {id: 'grok-2-vision-1212', name: 'Grok 2 Vision-1212 (Vision Support, $$)', cost: 'Medium', prodAllowed: true},
                {id: 'grok-beta', name: 'Grok Beta (Latest Features, $$$)', cost: 'High', prodAllowed: true},
                {id: 'grok-vision-beta', name: 'Grok Vision Beta (Vision Beta, $$$)', cost: 'High', prodAllowed: true}
            ]
        };
        
        this.isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.isDev = window.location.hostname.includes('dev') || window.location.hostname.includes('staging');
        this.isDevOrLocal = this.isLocalhost || this.isDev;
        
        this.init();
    }
    
    init() {
        // Set up event listeners
        const providerSelect = document.getElementById(this.providerSelectId);
        const modelSelect = document.getElementById(this.modelSelectId);
        
        if (providerSelect) {
            providerSelect.addEventListener('change', () => this.updateAvailableModels());
        }
        
        // Model selection change handler removed - thinking mode disabled
        
        // Initial setup
        this.updateAvailableModels();
    }
    
    updateAvailableModels() {
        const providerSelect = document.getElementById(this.providerSelectId);
        const modelSelect = document.getElementById(this.modelSelectId);
        
        if (!providerSelect || !modelSelect) {
            console.warn('ModelSelector: Required elements not found');
            return;
        }
        
        const provider = providerSelect.value;
        const models = this.availableModels[provider] || [];
        
        // Debug: console.log('ModelSelector: Updating models for provider:', provider);
        
        modelSelect.innerHTML = '';
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            
            // For localhost/dev, show all models enabled
            // For production, show premium models as disabled
            if (!this.isDevOrLocal && !model.prodAllowed) {
                option.textContent = `${model.name} (Premium - Contact Admin)`;
                option.disabled = true;
                option.style.color = '#9ca3af';
                option.style.fontStyle = 'italic';
            } else {
                option.textContent = model.name;
            }
            
            modelSelect.appendChild(option);
        });
        
        // Select appropriate default model
        this.selectDefaultModel(provider, modelSelect);
        
        // Thinking mode visibility update removed
        
        // Call custom callback if provided
        if (this.onModelChange) {
            this.onModelChange(provider, modelSelect.value);
        }
    }
    
    selectDefaultModel(provider, modelSelect) {
        let defaultModel;
        
        switch (provider) {
            case 'gemini':
                defaultModel = 'gemini-1.5-flash-8b';  // Most cost-effective
                break;
            case 'claude':
                defaultModel = 'claude-sonnet-4-20250514';  // Latest Claude 4 Sonnet
                break;
            case 'grok':
                defaultModel = 'grok-2-1212';  // Production model
                break;
            default:
                defaultModel = null;
        }
        
        if (defaultModel && Array.from(modelSelect.options).some(opt => opt.value === defaultModel)) {
            modelSelect.value = defaultModel;
        }
    }
    
    // updateThinkingVisibility() removed - thinking mode disabled for simplicity
    
    getCurrentProvider() {
        const providerSelect = document.getElementById(this.providerSelectId);
        return providerSelect ? providerSelect.value : null;
    }
    
    getCurrentModel() {
        const modelSelect = document.getElementById(this.modelSelectId);
        return modelSelect ? modelSelect.value : null;
    }
    
    getCurrentConfig() {
        const provider = this.getCurrentProvider();
        const model = this.getCurrentModel();
        
        return {
            provider: provider,
            model: model
            // Thinking mode parameters removed for simplicity
        };
    }
    
    setModel(provider, model) {
        const providerSelect = document.getElementById(this.providerSelectId);
        const modelSelect = document.getElementById(this.modelSelectId);
        
        if (providerSelect && provider) {
            providerSelect.value = provider;
            this.updateAvailableModels();
        }
        
        if (modelSelect && model) {
            // Wait a tick for the models to be populated
            setTimeout(() => {
                if (Array.from(modelSelect.options).some(opt => opt.value === model)) {
                    modelSelect.value = model;
                    // Thinking visibility update removed
                }
            }, 0);
        }
    }
    
    getModelInfo(provider, modelId) {
        const models = this.availableModels[provider] || [];
        return models.find(m => m.id === modelId);
    }
    
    getAllModels() {
        return this.availableModels;
    }
    
    // Calculate cost for a model
    calculateCost(provider, model, inputTokens, outputTokens) {
        // Pricing per 1M tokens (USD)
        const modelCosts = {
            // Gemini models
            'gemini-2.5-pro': { input: 3.5, output: 10.5 },
            'gemini-2.5-flash': { input: 0.075, output: 0.30 },
            'gemini-1.5-pro': { input: 3.5, output: 10.5 },
            'gemini-1.5-flash': { input: 0.075, output: 0.30 },
            'gemini-1.5-flash-8b': { input: 0.0375, output: 0.15 },
            
            // Claude models
            'claude-opus-4-20250514': { input: 15.0, output: 75.0 },
            'claude-sonnet-4-20250514': { input: 3.0, output: 15.0 },
            'claude-3-5-sonnet-20241022': { input: 3.0, output: 15.0 },
            'claude-3-5-haiku-20241022': { input: 0.25, output: 1.25 },
            'claude-3-opus-20240229': { input: 15.0, output: 75.0 },
            
            // Grok models
            'grok-4': { input: 3.0, output: 15.0 },
            'grok-2-1212': { input: 2.0, output: 10.0 },
            'grok-2-vision-1212': { input: 2.0, output: 10.0 },
            'grok-beta': { input: 5.0, output: 15.0 },
            'grok-vision-beta': { input: 5.0, output: 15.0 }
        };
        
        const rates = modelCosts[model] || { input: 2.0, output: 10.0 }; // Default fallback
        
        return (
            (inputTokens / 1_000_000) * rates.input +
            (outputTokens / 1_000_000) * rates.output
        );
    }
}

// Global instance for backward compatibility
let globalModelSelector = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if model selector elements exist
    const providerSelect = document.getElementById('modelProvider');
    const modelSelect = document.getElementById('modelName');
    
    if (providerSelect && modelSelect) {
        try {
            globalModelSelector = new ModelSelector({
                onModelChange: function(provider, model) {
                    // Call updateCostEstimate if it exists (for dataset analysis page)
                    if (typeof updateCostEstimate === 'function') {
                        updateCostEstimate();
                    }
                }
            });
            
            // Expose global functions for backward compatibility
            window.updateAvailableModels = () => globalModelSelector.updateAvailableModels();
            window.getCurrentModelConfig = () => globalModelSelector.getCurrentConfig();
            // updateThinkingVisibility removed - thinking mode disabled
            window.calculateModelCost = (provider, model, input, output) => 
                globalModelSelector.calculateCost(provider, model, input, output);
                
        } catch (error) {
            console.error('ModelSelector: Initialization failed:', error);
        }
    }
});