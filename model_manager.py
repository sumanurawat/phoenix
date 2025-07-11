#!/usr/bin/env python3
"""
Model Management Utility
========================

This script helps you manage and test different Gemini models.
You can list available models, get model information, test models, and update configurations.

Usage:
    python model_manager.py list                    # List all available models
    python model_manager.py info <model_name>       # Get model information
    python model_manager.py test <model_name>       # Test a specific model
    python model_manager.py recommendations         # Get model recommendations
    python model_manager.py current                 # Show current model configuration
"""

import os
import sys
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.gemini_models import (
    GEMINI_MODELS, 
    get_model_info, 
    list_models_by_category, 
    get_recommended_model_for_use_case
)
from services.llm_service import LLMService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_model_info(model_name: str, info: Dict[str, Any]):
    """Print formatted model information."""
    print(f"\n🤖 {info.get('name', model_name)}")
    print(f"   Model ID: {model_name}")
    print(f"   Generation: {info.get('generation', 'Unknown')}")
    print(f"   Description: {info.get('description', 'No description available')}")
    print(f"   Performance: {info.get('performance', 'Unknown')} | Speed: {info.get('speed', 'Unknown')} | Cost: {info.get('cost', 'Unknown')}")
    print(f"   Context Length: {info.get('context_length', 'Unknown')}")
    
    # Display pricing information if available
    pricing = info.get('pricing', {})
    if pricing:
        print(f"   💰 Pricing:")
        print(f"      Input: {pricing.get('input', 'N/A')}")
        print(f"      Output: {pricing.get('output', 'N/A')}")
        print(f"      Cost Tier: {pricing.get('cost_tier', 'N/A')}")
        print(f"      Monthly Estimate: {pricing.get('monthly_cost_estimate', 'N/A')}")
    
    print(f"   Capabilities: {', '.join(info.get('capabilities', []))}")
    print(f"   Use Cases: {', '.join(info.get('use_cases', []))}")
    print(f"   💡 {info.get('recommended_for', 'General use')}")


def list_all_models():
    """List all available models organized by category."""
    print_header("All Available Gemini Models")
    
    categories = list_models_by_category()
    
    for category, models in categories.items():
        print(f"\n📁 {category.replace('_', ' ').title()}:")
        for model in models:
            info = get_model_info(model)
            print(f"   • {model} - {info.get('name', 'Unknown')}")
    
    print(f"\n📋 Total unique models: {len(set([m for models in categories.values() for m in models]))}")


def show_model_info(model_name: str):
    """Show detailed information about a specific model."""
    print_header(f"Model Information: {model_name}")
    
    info = get_model_info(model_name)
    print_model_info(model_name, info)


def test_model(model_name: str):
    """Test a specific model."""
    print_header(f"Testing Model: {model_name}")
    
    try:
        # Temporarily set the model for testing
        original_default = os.environ.get('DEFAULT_MODEL')
        os.environ['DEFAULT_MODEL'] = model_name
        
        # Initialize LLM service with the test model
        llm_service = LLMService()
        
        print(f"🧪 Testing model: {model_name}")
        
        # Test text generation
        result = llm_service.generate_text("Hello! Please respond with 'Test successful' and tell me which model you are.")
        
        if result.get("success"):
            print(f"✅ Test SUCCESSFUL!")
            print(f"📝 Response: {result.get('text', 'No response')}")
            print(f"🏷️ Model used: {result.get('model_used', 'Unknown')}")
            print(f"⏱️ Response time: {result.get('response_time', 0):.2f} seconds")
            
            model_info = result.get('model_info', {})
            if model_info:
                print(f"📊 Model: {model_info.get('name', 'Unknown')} ({model_info.get('generation', 'Unknown')} gen)")
        else:
            print(f"❌ Test FAILED!")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        # Restore original environment
        if original_default:
            os.environ['DEFAULT_MODEL'] = original_default
        elif 'DEFAULT_MODEL' in os.environ:
            del os.environ['DEFAULT_MODEL']
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")


def show_recommendations():
    """Show model recommendations for different use cases."""
    print_header("Model Recommendations by Use Case")
    
    use_cases = [
        ("chat", "General chat applications"),
        ("coding", "Code generation and programming assistance"),
        ("analysis", "Complex analysis and reasoning tasks"),
        ("simple", "Simple, fast responses"),
        ("complex", "Complex, high-quality responses"),
        ("education", "Educational and learning content"),
        ("document", "Document processing and analysis"),
        ("production", "Production applications"),
        ("research", "Research and academic work")
    ]
    
    for use_case, description in use_cases:
        recommended = get_recommended_model_for_use_case(use_case)
        info = get_model_info(recommended)
        print(f"\n🎯 {description}")
        print(f"   → {recommended} ({info.get('name', 'Unknown')})")
        print(f"   💡 {info.get('recommended_for', 'General use')}")


def show_current_config():
    """Show current model configuration."""
    print_header("Current Model Configuration")
    
    try:
        llm_service = LLMService()
        config = llm_service.get_model_info()
        
        print(f"🔧 Current Configuration:")
        print(f"   Primary Model: {config.get('primary_model', 'Unknown')}")
        print(f"   Current Model: {config.get('current_model', 'Unknown')}")
        print(f"   Fallback Models: {', '.join(config.get('fallback_models', []))}")
        
        current_info = config.get('current_model_info', {})
        if current_info:
            print(f"\n📊 Current Model Details:")
            print_model_info(config.get('current_model', 'Unknown'), current_info)
        
        # Show available alternatives
        print(f"\n🎛️ Available Alternatives:")
        alternatives = config.get('available_models', {})
        for category, models in alternatives.items():
            print(f"   {category.replace('_', ' ').title()}: {', '.join(models)}")
        
    except Exception as e:
        print(f"❌ Failed to get current configuration: {e}")


def print_usage():
    """Print usage information."""
    print_header("Model Manager - Usage")
    print("""
Available commands:

  list                    List all available models by category
  info <model_name>       Show detailed information about a specific model
  test <model_name>       Test a specific model with a sample request
  recommendations         Show recommended models for different use cases
  pricing                 Compare pricing of all available models
  current                 Show current model configuration
  
Examples:
  python model_manager.py list
  python model_manager.py info gemini-1.5-flash
  python model_manager.py test gemini-2.5-pro
  python model_manager.py recommendations
  python model_manager.py pricing
  python model_manager.py current

Available Models (quick reference):
  - gemini-1.5-flash      (Fast, cost-effective, production-ready)
  - gemini-1.5-pro        (High capability, large context)
  - gemini-2.5-flash      (Latest fast model, high performance)
  - gemini-2.5-pro        (Most capable model, highest quality)
  - gemini-1.5-flash-8b   (Ultra-fast, lightweight)
    """)


def show_pricing_comparison():
    """Show pricing comparison of all models."""
    print_header("Model Pricing Comparison")
    
    # Get all models with pricing info
    all_models = []
    categories = list_models_by_category()
    unique_models = set()
    
    for models in categories.values():
        for model in models:
            if model not in unique_models:
                info = get_model_info(model)
                pricing = info.get('pricing', {})
                if pricing:  # Only include models with pricing info
                    all_models.append({
                        'name': model,
                        'display_name': info.get('name', model),
                        'generation': info.get('generation', 'Unknown'),
                        'performance': info.get('performance', 'Unknown'),
                        'input_cost': pricing.get('input', 'N/A'),
                        'output_cost': pricing.get('output', 'N/A'),
                        'cost_tier': pricing.get('cost_tier', 'N/A'),
                        'monthly_estimate': pricing.get('monthly_cost_estimate', 'N/A')
                    })
                unique_models.add(model)
    
    # Sort by cost tier (Budget first, Premium last)
    tier_order = {'Ultra-budget': 1, 'Budget-friendly': 2, 'Mid-range': 3, 'Premium': 4}
    all_models.sort(key=lambda x: (tier_order.get(x['cost_tier'], 5), x['display_name']))
    
    print(f"\n💰 Cost Comparison (sorted by cost tier):")
    print(f"{'Model':<25} {'Generation':<10} {'Input Cost':<15} {'Output Cost':<15} {'Tier':<15} {'Monthly Est.'}")
    print("=" * 100)
    
    for model in all_models:
        print(f"{model['display_name']:<25} {model['generation']:<10} {model['input_cost']:<15} {model['output_cost']:<15} {model['cost_tier']:<15} {model['monthly_estimate']}")
    
    print(f"\n📊 Cost Tiers Explained:")
    print(f"   🟢 Ultra-budget: Lowest cost, basic features")
    print(f"   🟡 Budget-friendly: Low cost, good performance balance")
    print(f"   🟠 Mid-range: Moderate cost, high performance")
    print(f"   🔴 Premium: Highest cost, maximum capabilities")
    
    print(f"\n💡 Cost-saving tips:")
    print(f"   • Use Gemini 1.5 Flash 8B for simple, high-volume tasks")
    print(f"   • Use Gemini 1.5/2.5 Flash for most production applications")
    print(f"   • Reserve Pro models for complex reasoning tasks")
    print(f"   • Monitor your usage and switch models based on task complexity")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_all_models()
    elif command == "info":
        if len(sys.argv) < 3:
            print("❌ Error: Please specify a model name")
            print("Usage: python model_manager.py info <model_name>")
            return
        show_model_info(sys.argv[2])
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Error: Please specify a model name")
            print("Usage: python model_manager.py test <model_name>")
            return
        test_model(sys.argv[2])
    elif command == "recommendations":
        show_recommendations()
    elif command == "pricing":
        show_pricing_comparison()
    elif command == "current":
        show_current_config()
    elif command == "pricing":
        show_pricing_comparison()
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    main()
