#!/usr/bin/env python3
"""
Quick test script for the Unified LLM Service

Run this to verify your LLM service is working correctly.
"""

import os
import sys
from pathlib import Path

# Add services directory to path
sys.path.append(str(Path(__file__).parent / "services"))

try:
    from unified_llm_service import UnifiedLLMService, LLMConfig
    from llm_migration_guide import LLMMigrationTester
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the phoenix project root directory")
    sys.exit(1)


def quick_test():
    """Quick test of the unified LLM service."""
    print("🚀 Quick Test: Unified LLM Service")
    print("=" * 40)
    
    # Check environment
    has_gemini_gcp = bool(os.getenv('GCP_PROJECT_ID'))
    has_gemini_api = bool(os.getenv('GEMINI_API_KEY'))
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))
    
    print("🔧 Configuration Check:")
    print(f"  Gemini GCP: {'✅' if has_gemini_gcp else '❌'} {os.getenv('GCP_PROJECT_ID', 'Not configured')}")
    print(f"  Gemini API: {'✅' if has_gemini_api else '❌'} {'Configured' if has_gemini_api else 'Not configured'}")
    print(f"  OpenAI:     {'✅' if has_openai else '❌'} {'Configured' if has_openai else 'Not configured'}")
    print(f"  Anthropic:  {'✅' if has_anthropic else '❌'} {'Configured' if has_anthropic else 'Not configured'}")
    
    if not any([has_gemini_gcp, has_gemini_api, has_openai, has_anthropic]):
        print("\n❌ No API keys configured!")
        print("Please set at least one of the following environment variables:")
        print("  - GCP_PROJECT_ID (for Gemini via GCP)")
        print("  - GEMINI_API_KEY (for Gemini via AI Studio)")
        print("  - OPENAI_API_KEY (for OpenAI models)")
        print("  - ANTHROPIC_API_KEY (for Claude models)")
        print("\nSee .env.llm.example for configuration details.")
        return False
    
    # Initialize service
    try:
        service = UnifiedLLMService()
        print(f"\n📋 Available Models:")
        
        available_models = service.list_available_models()
        if not available_models:
            print("❌ No models available - check your configuration")
            return False
        
        for provider, models in available_models.items():
            print(f"  {provider}: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}")
        
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return False
    
    # Test basic generation
    print(f"\n🧪 Testing Generation:")
    
    # Try Gemini first (most likely to be configured)
    test_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gpt-4", "claude-3-sonnet"]
    
    for model in test_models:
        try:
            print(f"  Testing {model}... ", end="")
            response = service.generate(
                prompt="Say 'Hello from unified LLM service!' in exactly that phrase.",
                model=model,
                max_tokens=20
            )
            print(f"✅ Success")
            print(f"    Response: {response.content[:50]}{'...' if len(response.content) > 50 else ''}")
            print(f"    Provider: {response.provider}")
            print(f"    Latency: {response.latency:.2f}s")
            
            # Test streaming with this model
            print(f"  Testing streaming with {model}... ", end="")
            chunks = []
            for chunk in service.stream(
                prompt="Count: 1, 2, 3",
                model=model,
                max_tokens=15
            ):
                chunks.append(chunk)
            print(f"✅ Success ({len(chunks)} chunks)")
            
            # Show usage stats
            stats = service.get_usage_stats()
            print(f"    Usage: {stats['total_requests']} requests, {stats['total_tokens']} tokens")
            
            return True  # Success with at least one model
            
        except Exception as e:
            print(f"❌ {str(e)[:50]}{'...' if len(str(e)) > 50 else ''}")
            continue
    
    print("❌ All models failed")
    return False


def comprehensive_test():
    """Run comprehensive tests."""
    print("\n🔬 Running Comprehensive Tests...")
    tester = LLMMigrationTester()
    results = tester.run_comprehensive_test()
    return all(results.values())


def interactive_demo():
    """Interactive demo of the LLM service."""
    print("\n🎮 Interactive Demo")
    print("Type prompts to test the LLM service. Type 'quit' to exit.")
    
    service = UnifiedLLMService()
    available_models = service.list_available_models()
    
    if not available_models:
        print("❌ No models available for demo")
        return
    
    # Get first available model
    first_provider = list(available_models.keys())[0]
    default_model = available_models[first_provider][0]
    
    print(f"Using model: {default_model}")
    print("Commands:")
    print("  !models - list available models")
    print("  !model <name> - switch model")
    print("  !stream <prompt> - stream response")
    print("  !stats - show usage statistics")
    print("-" * 40)
    
    current_model = default_model
    
    while True:
        try:
            user_input = input(f"\n[{current_model}] > ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input == '!models':
                for provider, models in available_models.items():
                    print(f"  {provider}: {', '.join(models)}")
            elif user_input.startswith('!model '):
                new_model = user_input[7:].strip()
                # Check if model is available
                model_found = False
                for provider, models in available_models.items():
                    if new_model in models:
                        current_model = new_model
                        model_found = True
                        print(f"Switched to {new_model}")
                        break
                if not model_found:
                    print(f"Model {new_model} not available")
            elif user_input.startswith('!stream '):
                prompt = user_input[8:].strip()
                print("Streaming response:")
                for chunk in service.stream(prompt, current_model):
                    print(chunk, end="", flush=True)
                print()
            elif user_input == '!stats':
                stats = service.get_usage_stats()
                print(f"Usage statistics: {stats}")
            elif user_input:
                response = service.generate(user_input, current_model)
                print(f"\n{response.content}")
                if response.latency:
                    print(f"({response.latency:.2f}s)")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main function."""
    print("🌟 Unified LLM Service Test Suite")
    print("=" * 50)
    
    # Quick test first
    success = quick_test()
    
    if not success:
        print("\n❌ Quick test failed. Please check your configuration.")
        return
    
    print("\n🎉 Quick test passed!")
    
    # Ask what to do next
    while True:
        print("\nWhat would you like to do?")
        print("1. Run comprehensive tests")
        print("2. Interactive demo")
        print("3. Exit")
        
        choice = input("\nChoice (1-3): ").strip()
        
        if choice == '1':
            comprehensive_test()
        elif choice == '2':
            interactive_demo()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()