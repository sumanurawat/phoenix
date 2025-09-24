"""
OpenAI Model Constants and Configuration
=======================================

This module contains all available OpenAI model configurations with detailed information
about each model's capabilities, performance characteristics, pricing, and use cases.

Model Categories:
- GPT_4_MODELS: Latest GPT-4 generation models (best performance)
- GPT_3_5_MODELS: GPT-3.5 models (cost-effective)
- SPECIALTY_MODELS: Models with specific capabilities (vision, etc.)

Pricing Information (as of 2025):
- GPT-4o Mini: $0.15/1M input, $0.60/1M output (Ultra-budget)
- GPT-4o: $5.00/1M input, $15.00/1M output (Mid-range)
- GPT-4 Turbo: $10.00/1M input, $30.00/1M output (Premium)

Usage:
    from config.openai_models import OPENAI_MODELS, get_openai_model_info
    
    # Get default model
    default_model = OPENAI_MODELS.PRIMARY
    
    # Get model information including pricing
    model_info = get_openai_model_info(OPENAI_MODELS.PRIMARY)
"""

class OpenAIModels:
    """
    OpenAI Model Constants with detailed information about each model.
    """
    
    # === GPT-4 MODELS (Latest Generation) ===
    
    # Most cost-effective GPT-4 model
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"
    
    # Standard GPT-4 model
    GPT_4O = "gpt-4o"
    GPT_4O_2024_11_20 = "gpt-4o-2024-11-20"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    
    # GPT-4 Turbo models
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4_TURBO_2024_04_09 = "gpt-4-turbo-2024-04-09"
    GPT_4_TURBO_PREVIEW = "gpt-4-turbo-preview"
    
    # Legacy GPT-4 models
    GPT_4 = "gpt-4"
    GPT_4_0613 = "gpt-4-0613"
    
    # === GPT-3.5 MODELS ===
    
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    
    # === GPT-5 MODELS (Latest Generation) ===
    
    # GPT-5 models with reasoning capabilities
    GPT_5_NANO = "gpt-5-nano-2025-08-07"
    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GPT_5 = "gpt-5-2025-08-07"
    
    # === RECOMMENDED CONFIGURATIONS ===
    
    # Primary model for production (cheapest GPT-5 model)
    PRIMARY = GPT_5_NANO
    
    # Fallback model
    FALLBACK = GPT_4O_MINI
    
    # High performance model
    HIGH_PERFORMANCE = GPT_5_MINI
    
    # Ultra high performance model
    ULTRA_HIGH_PERFORMANCE = GPT_5

# Model information with pricing and capabilities
OPENAI_MODEL_INFO = {
    # GPT-4o Mini models
    OpenAIModels.GPT_4O_MINI: {
        "name": "GPT-4o Mini",
        "description": "Most cost-effective GPT-4 model with excellent performance",
        "context_length": 128000,
        "max_output": 16384,
        "pricing": {
            "input_per_1m": 0.15,
            "output_per_1m": 0.60,
            "cost_tier": "Ultra-budget",
            "monthly_estimate_moderate": "$0.50-2.00"
        },
        "performance": "Very High",
        "speed": "Very Fast",
        "cost": "Ultra-budget",
        "capabilities": ["text", "vision", "json_mode", "function_calling"],
        "recommended_for": "General use, cost-sensitive applications"
    },
    
    # GPT-4o models
    OpenAIModels.GPT_4O: {
        "name": "GPT-4o",
        "description": "Flagship GPT-4 model with multimodal capabilities",
        "context_length": 128000,
        "max_output": 16384,
        "pricing": {
            "input_per_1m": 5.00,
            "output_per_1m": 15.00,
            "cost_tier": "Mid-range",
            "monthly_estimate_moderate": "$15-45"
        },
        "performance": "Excellent",
        "speed": "Fast",
        "cost": "Mid-range",
        "capabilities": ["text", "vision", "json_mode", "function_calling"],
        "recommended_for": "High-quality tasks, multimodal applications"
    },
    
    # GPT-4 Turbo models
    OpenAIModels.GPT_4_TURBO: {
        "name": "GPT-4 Turbo",
        "description": "Most capable GPT-4 model with largest context window",
        "context_length": 128000,
        "max_output": 4096,
        "pricing": {
            "input_per_1m": 10.00,
            "output_per_1m": 30.00,
            "cost_tier": "Premium",
            "monthly_estimate_moderate": "$30-90"
        },
        "performance": "Exceptional",
        "speed": "Moderate",
        "cost": "Premium",
        "capabilities": ["text", "vision", "json_mode", "function_calling"],
        "recommended_for": "Complex reasoning, large context tasks"
    },
    
    # GPT-3.5 Turbo models
    OpenAIModels.GPT_3_5_TURBO: {
        "name": "GPT-3.5 Turbo",
        "description": "Fast and cost-effective model for simple tasks",
        "context_length": 16385,
        "max_output": 4096,
        "pricing": {
            "input_per_1m": 0.50,
            "output_per_1m": 1.50,
            "cost_tier": "Budget-friendly",
            "monthly_estimate_moderate": "$1.50-4.50"
        },
        "performance": "Good",
        "speed": "Very Fast",
        "cost": "Budget-friendly",
        "capabilities": ["text", "json_mode", "function_calling"],
        "recommended_for": "Simple tasks, high-volume applications"
    },
    
    # GPT-5 Models (Latest Generation with Reasoning)
    OpenAIModels.GPT_5_NANO: {
        "name": "GPT-5 Nano",
        "description": "Fastest, cheapest GPT-5 for summarization and classification",
        "context_length": 400000,
        "max_output": 128000,
        "pricing": {
            "input_per_1m": 0.05,
            "output_per_1m": 0.40,
            "cost_tier": "Ultra-budget",
            "monthly_estimate_moderate": "$0.25-1.00"
        },
        "performance": "Very Good",
        "speed": "Very Fast",
        "cost": "Ultra-budget",
        "capabilities": ["text", "vision", "reasoning", "json_mode", "function_calling", "built_in_tools"],
        "recommended_for": "Summarization, classification, high-volume tasks"
    },
    
    OpenAIModels.GPT_5_MINI: {
        "name": "GPT-5 Mini",
        "description": "Faster, cheaper GPT-5 for well-defined tasks",
        "context_length": 400000,
        "max_output": 128000,
        "pricing": {
            "input_per_1m": 0.25,
            "output_per_1m": 2.00,
            "cost_tier": "Budget-friendly",
            "monthly_estimate_moderate": "$1.00-5.00"
        },
        "performance": "Excellent",
        "speed": "Fast",
        "cost": "Budget-friendly",
        "capabilities": ["text", "vision", "reasoning", "json_mode", "function_calling", "built_in_tools"],
        "recommended_for": "Well-defined tasks, balanced performance and cost"
    },
    
    OpenAIModels.GPT_5: {
        "name": "GPT-5",
        "description": "Best model for coding and agentic tasks across industries",
        "context_length": 400000,
        "max_output": 128000,
        "pricing": {
            "input_per_1m": 1.25,
            "output_per_1m": 10.00,
            "cost_tier": "Premium",
            "monthly_estimate_moderate": "$10-30"
        },
        "performance": "Outstanding",
        "speed": "Medium",
        "cost": "Premium",
        "capabilities": ["text", "vision", "reasoning", "json_mode", "function_calling", "built_in_tools", "agentic_tasks"],
        "recommended_for": "Complex coding, agentic tasks, multi-step reasoning"
    }
}

def get_openai_model_info(model_name: str) -> dict:
    """
    Get detailed information about a specific OpenAI model.
    
    Args:
        model_name: The model identifier (e.g., 'gpt-4o-mini')
        
    Returns:
        Dictionary containing model information including pricing and capabilities
    """
    return OPENAI_MODEL_INFO.get(model_name, {
        "name": "Unknown Model",
        "description": "Model information not available",
        "performance": "Unknown",
        "speed": "Unknown", 
        "cost": "Unknown",
        "capabilities": [],
        "pricing": {}
    })

def get_all_openai_models() -> list:
    """Get list of all available OpenAI models."""
    return list(OPENAI_MODEL_INFO.keys())

def get_openai_models_by_cost_tier(tier: str) -> list:
    """
    Get OpenAI models filtered by cost tier.
    
    Args:
        tier: Cost tier ('Ultra-budget', 'Budget-friendly', 'Mid-range', 'Premium')
        
    Returns:
        List of model names matching the cost tier
    """
    return [
        model for model, info in OPENAI_MODEL_INFO.items()
        if info.get('pricing', {}).get('cost_tier') == tier
    ]