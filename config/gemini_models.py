"""
Gemini Model Constants and Configuration
========================================

This module contains all available Gemini model configurations with detailed information
about each model's capabilities, performance characteristics, pricing, and use cases.

Model Categories:
- GEMINI_2_MODELS: Latest 2.x generation models (best performance)
- GEMINI_1_5_MODELS: Stable 1.5 generation models (balanced performance/cost)
- GEMINI_1_MODELS: Legacy 1.x models (deprecated)
- SPECIALIZED_MODELS: Models with specific capabilities

Pricing Information:
Each model includes detailed pricing information with:
- Input cost per 1M tokens
- Output cost per 1M tokens
- Cost tier (Ultra-budget, Budget-friendly, Mid-range, Premium)
- Monthly cost estimates for moderate usage

Usage:
    from config.gemini_models import GEMINI_MODELS, get_model_info
    
    # Get default model
    default_model = GEMINI_MODELS.PRIMARY
    
    # Get model information including pricing
    model_info = get_model_info(GEMINI_MODELS.PRIMARY)
    pricing = model_info.get('pricing', {})
    
Cost Comparison (as of 2025):
- Ultra-budget: Gemini 1.5 Flash 8B (~$0.38-1.50/month)
- Budget-friendly: Gemini 1.5/2.5 Flash (~$0.75-3.00/month)
- Premium: Gemini 1.5/2.5 Pro (~$35-105/month)
"""

class GeminiModels:
    """
    Gemini Model Constants with detailed information about each model.
    """
    
    # === GEMINI 2.X MODELS (Latest Generation) ===
    
    # Best overall model - highest capability, most expensive
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_PRO_PREVIEW = "gemini-2.5-pro-preview-05-06"
    GEMINI_2_5_PRO_EXPERIMENTAL = "gemini-2.5-pro-exp-03-25"  # Experimental version
    
    # Fast and efficient - good balance of speed and capability
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_PREVIEW = "gemini-2.5-flash-preview-05-20"
    
    # Advanced 2.0 models
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"
    GEMINI_2_0_PRO_EXP = "gemini-2.0-pro-exp"
    
    # Thinking models (reasoning-optimized)
    GEMINI_2_0_FLASH_THINKING = "gemini-2.0-flash-thinking-exp"
    GEMINI_2_5_FLASH_THINKING = "gemini-2.5-flash-preview-04-17-thinking"
    
    # === GEMINI 1.5 MODELS (Stable, Production-Ready) ===
    
    # Most capable 1.5 model
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_PRO_LATEST = "gemini-1.5-pro-latest"
    GEMINI_1_5_PRO_002 = "gemini-1.5-pro-002"
    
    # Fast and cost-effective - recommended for most use cases
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_FLASH_LATEST = "gemini-1.5-flash-latest"
    GEMINI_1_5_FLASH_002 = "gemini-1.5-flash-002"
    
    # Ultra-fast, lightweight models
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b"
    GEMINI_1_5_FLASH_8B_LATEST = "gemini-1.5-flash-8b-latest"
    
    # === SPECIALIZED MODELS ===
    
    # Learning-optimized model
    LEARNLM_2_0_FLASH = "learnlm-2.0-flash-experimental"
    
    # Text-to-Speech capable models
    GEMINI_2_5_FLASH_TTS = "gemini-2.5-flash-preview-tts"
    GEMINI_2_5_PRO_TTS = "gemini-2.5-pro-preview-tts"
    
    # Image generation models
    GEMINI_2_0_FLASH_IMAGE_GEN = "gemini-2.0-flash-exp-image-generation"
    
    # === GEMMA MODELS (Smaller, Efficient) ===
    
    GEMMA_3_27B = "gemma-3-27b-it"  # Largest Gemma model
    GEMMA_3_12B = "gemma-3-12b-it"  # Medium Gemma model
    GEMMA_3_4B = "gemma-3-4b-it"   # Small Gemma model
    GEMMA_3_1B = "gemma-3-1b-it"   # Tiny Gemma model
    
    # === RECOMMENDED CONFIGURATIONS ===
    
    # Primary model for production (cheapest available model)
    PRIMARY = GEMINI_1_5_FLASH_8B
    
    # Fallback model if primary fails or hits quota
    FALLBACK = GEMINI_1_5_FLASH
    
    # Final fallback (most reliable, always available)
    FINAL_FALLBACK = GEMINI_1_5_FLASH_002
    
    # High-performance model for complex tasks
    HIGH_PERFORMANCE = GEMINI_2_5_PRO
    
    # Ultra-fast model for simple tasks
    ULTRA_FAST = GEMINI_1_5_FLASH_8B


# Model information dictionary
MODEL_INFO = {
    # Gemini 2.5 Models
    GeminiModels.GEMINI_2_5_PRO: {
        "name": "Gemini 2.5 Pro",
        "description": "Most capable model with advanced reasoning, mathematics, and code generation",
        "generation": "2.5",
        "performance": "Highest",
        "cost": "High",
        "speed": "Medium",
        "context_length": "2M tokens",
        "pricing": {
            "input": "$3.50 per 1M tokens",
            "output": "$10.50 per 1M tokens",
            "monthly_cost_estimate": "$35-105 for moderate use",
            "cost_tier": "Premium"
        },
        "capabilities": ["Text", "Code", "Math", "Reasoning", "Multimodal"],
        "use_cases": ["Complex reasoning", "Advanced coding", "Research", "Analysis"],
        "recommended_for": "Complex tasks requiring highest quality output"
    },
    
    GeminiModels.GEMINI_2_5_FLASH: {
        "name": "Gemini 2.5 Flash",
        "description": "Fast and efficient model with excellent performance",
        "generation": "2.5",
        "performance": "High",
        "cost": "Low",
        "speed": "Fast",
        "context_length": "1M tokens",
        "pricing": {
            "input": "$0.075 per 1M tokens",
            "output": "$0.30 per 1M tokens",
            "monthly_cost_estimate": "$0.75-3.00 for moderate use",
            "cost_tier": "Budget-friendly"
        },
        "capabilities": ["Text", "Code", "Multimodal", "Fast reasoning"],
        "use_cases": ["Chat", "Content generation", "Coding assistance", "General tasks"],
        "recommended_for": "Most production applications requiring speed and quality"
    },
    
    GeminiModels.GEMINI_2_0_FLASH: {
        "name": "Gemini 2.0 Flash",
        "description": "Advanced 2.0 model with fast response times",
        "generation": "2.0",
        "performance": "High",
        "cost": "Low",
        "speed": "Fast",
        "context_length": "1M tokens",
        "pricing": {
            "input": "$0.075 per 1M tokens",
            "output": "$0.30 per 1M tokens",
            "monthly_cost_estimate": "$0.75-3.00 for moderate use",
            "cost_tier": "Budget-friendly"
        },
        "capabilities": ["Text", "Code", "Multimodal"],
        "use_cases": ["Chat", "Content creation", "Code generation"],
        "recommended_for": "High-performance applications"
    },
    
    # Gemini 1.5 Models
    GeminiModels.GEMINI_1_5_PRO: {
        "name": "Gemini 1.5 Pro",
        "description": "Most capable 1.5 model with excellent reasoning and large context",
        "generation": "1.5",
        "performance": "High",
        "cost": "Medium-High",
        "speed": "Medium",
        "context_length": "2M tokens",
        "pricing": {
            "input": "$3.50 per 1M tokens",
            "output": "$10.50 per 1M tokens",
            "monthly_cost_estimate": "$35-105 for moderate use",
            "cost_tier": "Premium"
        },
        "capabilities": ["Text", "Code", "Documents", "Long context"],
        "use_cases": ["Document analysis", "Long conversations", "Complex reasoning"],
        "recommended_for": "Tasks requiring large context windows"
    },
    
    GeminiModels.GEMINI_1_5_FLASH: {
        "name": "Gemini 1.5 Flash",
        "description": "Fast, efficient, and cost-effective model for most use cases",
        "generation": "1.5",
        "performance": "Good",
        "cost": "Low",
        "speed": "Fast",
        "context_length": "1M tokens",
        "pricing": {
            "input": "$0.075 per 1M tokens",
            "output": "$0.30 per 1M tokens",
            "monthly_cost_estimate": "$0.75-3.00 for moderate use",
            "cost_tier": "Budget-friendly"
        },
        "capabilities": ["Text", "Code", "Chat", "General tasks"],
        "use_cases": ["Chat applications", "Content generation", "Code assistance"],
        "recommended_for": "Production chat applications and general AI tasks"
    },
    
    GeminiModels.GEMINI_1_5_FLASH_8B: {
        "name": "Gemini 1.5 Flash 8B",
        "description": "Ultra-fast, lightweight model for simple tasks",
        "generation": "1.5",
        "performance": "Medium",
        "cost": "Very Low",
        "speed": "Ultra Fast",
        "context_length": "1M tokens",
        "pricing": {
            "input": "$0.0375 per 1M tokens",
            "output": "$0.15 per 1M tokens",
            "monthly_cost_estimate": "$0.38-1.50 for moderate use",
            "cost_tier": "Ultra-budget"
        },
        "capabilities": ["Text", "Simple chat", "Basic tasks"],
        "use_cases": ["Simple chat", "Quick responses", "High-volume applications"],
        "recommended_for": "High-frequency, simple interactions"
    },
    
    # Specialized Models
    GeminiModels.LEARNLM_2_0_FLASH: {
        "name": "LearnLM 2.0 Flash",
        "description": "Specialized model optimized for educational and learning tasks",
        "generation": "2.0",
        "performance": "High",
        "cost": "Low",
        "speed": "Fast",
        "context_length": "1M tokens",
        "pricing": {
            "input": "$0.075 per 1M tokens",
            "output": "$0.30 per 1M tokens",
            "monthly_cost_estimate": "$0.75-3.00 for moderate use",
            "cost_tier": "Budget-friendly"
        },
        "capabilities": ["Education", "Tutoring", "Explanations", "Learning"],
        "use_cases": ["Educational content", "Tutoring", "Explanations"],
        "recommended_for": "Educational applications and learning platforms"
    },
}


def get_model_info(model_name: str) -> dict:
    """
    Get detailed information about a specific model.
    
    Args:
        model_name: The model name (e.g., GeminiModels.GEMINI_1_5_FLASH)
        
    Returns:
        Dictionary with model information, or empty dict if not found
    """
    return MODEL_INFO.get(model_name, {
        "name": model_name,
        "description": "Model information not available",
        "generation": "Unknown",
        "performance": "Unknown",
        "cost": "Unknown",
        "speed": "Unknown",
        "context_length": "Unknown",
        "capabilities": [],
        "use_cases": [],
        "recommended_for": "Check model documentation"
    })


def list_models_by_category() -> dict:
    """
    Get models organized by category.
    
    Returns:
        Dictionary with model categories and their models
    """
    return {
        "production_recommended": [
            GeminiModels.GEMINI_1_5_FLASH,
            GeminiModels.GEMINI_2_5_FLASH,
            GeminiModels.GEMINI_1_5_PRO,
        ],
        "high_performance": [
            GeminiModels.GEMINI_2_5_PRO,
            GeminiModels.GEMINI_2_5_FLASH,
            GeminiModels.GEMINI_2_0_FLASH,
        ],
        "cost_effective": [
            GeminiModels.GEMINI_1_5_FLASH,
            GeminiModels.GEMINI_1_5_FLASH_8B,
            GeminiModels.GEMINI_1_5_FLASH_002,
        ],
        "experimental": [
            GeminiModels.GEMINI_2_5_PRO_EXPERIMENTAL,
            GeminiModels.GEMINI_2_0_FLASH_EXP,
            GeminiModels.GEMINI_2_0_FLASH_THINKING,
        ],
        "specialized": [
            GeminiModels.LEARNLM_2_0_FLASH,
            GeminiModels.GEMINI_2_5_FLASH_TTS,
            GeminiModels.GEMINI_2_0_FLASH_IMAGE_GEN,
        ]
    }


def get_recommended_model_for_use_case(use_case: str) -> str:
    """
    Get the recommended model for a specific use case.
    
    Args:
        use_case: The use case (e.g., "chat", "coding", "analysis", "simple", "complex")
        
    Returns:
        Recommended model name
    """
    recommendations = {
        "chat": GeminiModels.GEMINI_1_5_FLASH,
        "coding": GeminiModels.GEMINI_2_5_FLASH,
        "analysis": GeminiModels.GEMINI_2_5_PRO,
        "simple": GeminiModels.GEMINI_1_5_FLASH_8B,
        "complex": GeminiModels.GEMINI_2_5_PRO,
        "education": GeminiModels.LEARNLM_2_0_FLASH,
        "document": GeminiModels.GEMINI_1_5_PRO,
        "fast": GeminiModels.GEMINI_1_5_FLASH_8B,
        "production": GeminiModels.GEMINI_1_5_FLASH,
        "research": GeminiModels.GEMINI_2_5_PRO,
    }
    
    return recommendations.get(use_case.lower(), GeminiModels.PRIMARY)


# Export the main class for easy importing
GEMINI_MODELS = GeminiModels()
