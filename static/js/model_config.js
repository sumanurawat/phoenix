/**
 * Centralized Model Configuration for Phoenix AI Platform
 * Used by all apps: Derplexity, Doogle, etc.
 */

const PHOENIX_MODELS = {
    // OpenAI Models (Default provider - cheapest overall)
    openai: {
        name: 'OpenAI',
        icon: 'fab fa-openai',
        color: '#10a37f',
        models: [
            {
                id: 'gpt-4o-mini',
                name: 'GPT-4o Mini',
                description: 'Ultra-budget, perfect for most tasks',
                cost: 'Very Low',
                costIcon: '¢',
                speed: 'Fast',
                quality: 'Good',
                prodAllowed: true,
                recommended: true, // This is the cheapest overall
                tags: ['budget', 'fast', 'recommended']
            },
            {
                id: 'gpt-3.5-turbo',
                name: 'GPT-3.5 Turbo',
                description: 'Classic budget option',
                cost: 'Low',
                costIcon: '$',
                speed: 'Fast',
                quality: 'Good',
                prodAllowed: true,
                tags: ['budget', 'fast']
            },
            {
                id: 'gpt-4o',
                name: 'GPT-4o',
                description: 'Flagship model, best balance',
                cost: 'Medium',
                costIcon: '$$',
                speed: 'Medium',
                quality: 'Excellent',
                prodAllowed: true,
                tags: ['flagship', 'balanced']
            },
            {
                id: 'gpt-4-turbo',
                name: 'GPT-4 Turbo',
                description: 'Premium performance',
                cost: 'High',
                costIcon: '$$$',
                speed: 'Medium',
                quality: 'Excellent',
                prodAllowed: true,
                tags: ['premium', 'high-quality']
            },
            // --- GPT-5 Models (Official OpenAI Release) ---
            {
                id: 'gpt-5-nano-2025-08-07',
                name: 'GPT-5 Nano',
                description: 'Fastest, cheapest GPT-5 for summarization and classification',
                cost: 'Low',
                costIcon: '$',
                speed: 'Very Fast',
                quality: 'Very Good',
                prodAllowed: true,
                requiresAccess: false,
                tags: ['fast', 'budget', 'reasoning', 'vision']
            },
            {
                id: 'gpt-5-mini-2025-08-07',
                name: 'GPT-5 Mini',
                description: 'Faster, cheaper GPT-5 for well-defined tasks',
                cost: 'Medium',
                costIcon: '$$',
                speed: 'Fast',
                quality: 'Excellent',
                prodAllowed: true,
                requiresAccess: false,
                tags: ['balanced', 'reasoning', 'vision', 'tools']
            },
            {
                id: 'gpt-5-2025-08-07',
                name: 'GPT-5',
                description: 'Best model for coding and agentic tasks across industries',
                cost: 'High',
                costIcon: '$$$',
                speed: 'Medium',
                quality: 'Outstanding',
                prodAllowed: true,
                requiresAccess: false,
                tags: ['premium', 'reasoning', 'coding', 'agents', 'vision']
            }
        ]
    },

    // Google Gemini Models
    gemini: {
        name: 'Google Gemini',
        icon: 'fas fa-star',
        color: '#4285f4',
        models: [
            {
                id: 'gemini-1.5-flash-8b',
                name: 'Gemini 1.5 Flash 8B',
                description: 'Ultra-fast, lightweight model',
                cost: 'Very Low',
                costIcon: '¢',
                speed: 'Ultra Fast',
                quality: 'Good',
                prodAllowed: true,
                tags: ['fast', 'lightweight', 'budget']
            },
            {
                id: 'gemini-2.5-flash',
                name: 'Gemini 2.5 Flash',
                description: 'Latest fast model',
                cost: 'Low',
                costIcon: '$',
                speed: 'Fast',
                quality: 'Very Good',
                prodAllowed: true,
                tags: ['latest', 'fast']
            },
            {
                id: 'gemini-1.5-pro',
                name: 'Gemini 1.5 Pro',
                description: 'Professional grade',
                cost: 'Medium',
                costIcon: '$$',
                speed: 'Medium',
                quality: 'Excellent',
                prodAllowed: true,
                tags: ['professional', 'balanced']
            },
            {
                id: 'gemini-2.5-pro',
                name: 'Gemini 2.5 Pro',
                description: 'Highest quality available',
                cost: 'High',
                costIcon: '$$$',
                speed: 'Medium',
                quality: 'Outstanding',
                prodAllowed: true,
                tags: ['premium', 'highest-quality']
            }
        ]
    },

    // Anthropic Claude Models
    claude: {
        name: 'Anthropic Claude',
        icon: 'fas fa-brain',
        color: '#cc785c',
        models: [
            {
                id: 'claude-3-5-haiku-20241022',
                name: 'Claude 3.5 Haiku',
                description: 'Fast and affordable',
                cost: 'Low',
                costIcon: '$',
                speed: 'Fast',
                quality: 'Very Good',
                prodAllowed: true,
                tags: ['fast', 'affordable']
            },
            {
                id: 'claude-3-5-sonnet-20241022',
                name: 'Claude 3.5 Sonnet',
                description: 'High quality, great balance',
                cost: 'Medium',
                costIcon: '$$',
                speed: 'Medium',
                quality: 'Excellent',
                prodAllowed: true,
                tags: ['balanced', 'high-quality']
            },
            {
                id: 'claude-sonnet-4-20250514',
                name: 'Claude 4 Sonnet',
                description: 'Latest and best balance',
                cost: 'High',
                costIcon: '$$$',
                speed: 'Medium',
                quality: 'Outstanding',
                prodAllowed: true,
                tags: ['latest', 'premium']
            },
            {
                id: 'claude-opus-4-20250514',
                name: 'Claude 4 Opus',
                description: 'World\'s best coding model',
                cost: 'Very High',
                costIcon: '$$$$',
                speed: 'Slow',
                quality: 'World-Class',
                prodAllowed: true,
                tags: ['coding', 'world-class', 'premium']
            }
        ]
    },

    // xAI Grok Models
    grok: {
        name: 'xAI Grok',
        icon: 'fas fa-rocket',
        color: '#1d9bf0',
        models: [
            {
                id: 'grok-2-1212',
                name: 'Grok 2-1212',
                description: 'Production stable model',
                cost: 'Medium',
                costIcon: '$$',
                speed: 'Fast',
                quality: 'Very Good',
                prodAllowed: true,
                tags: ['stable', 'production']
            },
            {
                id: 'grok-2-vision-1212',
                name: 'Grok 2 Vision-1212',
                description: 'With vision capabilities',
                cost: 'Medium',
                costIcon: '$$',
                speed: 'Fast',
                quality: 'Very Good',
                prodAllowed: true,
                tags: ['vision', 'multimodal']
            },
            {
                id: 'grok-beta',
                name: 'Grok Beta',
                description: 'Latest experimental features',
                cost: 'High',
                costIcon: '$$$',
                speed: 'Medium',
                quality: 'Excellent',
                prodAllowed: true,
                tags: ['beta', 'experimental']
            },
            {
                id: 'grok-4',
                name: 'Grok 4',
                description: 'Real-time search integration',
                cost: 'High',
                costIcon: '$$$',
                speed: 'Medium',
                quality: 'Excellent',
                prodAllowed: true,
                tags: ['real-time', 'search', 'premium']
            }
        ]
    }
};

// Default selections (cheapest models for each provider)
const DEFAULT_MODELS = {
    openai: 'gpt-5-nano-2025-08-07',      // GPT-5 Nano is now the cheapest OpenAI model
    gemini: 'gemini-1.5-flash-8b',
    claude: 'claude-3-5-haiku-20241022',
    grok: 'grok-2-1212'
};

// Recommended provider order (cheapest first)
const PROVIDER_ORDER = ['openai', 'gemini', 'claude', 'grok'];

// Cost level definitions
const COST_LEVELS = {
    'Very Low': { color: '#22c55e', priority: 1 },
    'Low': { color: '#84cc16', priority: 2 },
    'Medium': { color: '#f59e0b', priority: 3 },
    'High': { color: '#ef4444', priority: 4 },
    'Very High': { color: '#dc2626', priority: 5 }
};

// Export for use in components
window.PHOENIX_MODELS = PHOENIX_MODELS;
window.DEFAULT_MODELS = DEFAULT_MODELS;
window.PROVIDER_ORDER = PROVIDER_ORDER;
window.COST_LEVELS = COST_LEVELS;