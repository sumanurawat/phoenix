"""
LLM Service Migration Guide and Compatibility Layer

This module provides:
1. Drop-in replacement for the existing LLM service
2. Migration utilities to transition to the unified service
3. Backward compatibility wrappers
4. Testing and validation tools
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List

from unified_llm_service import UnifiedLLMService, LLMConfig


class LegacyLLMServiceWrapper:
    """
    Drop-in replacement for the existing LLM service.
    Maintains API compatibility while using the new unified service underneath.
    """
    
    def __init__(self):
        """Initialize with same interface as original LLM service."""
        self.unified_service = UnifiedLLMService()
        self.logger = logging.getLogger(__name__)
        
        # Maintain same fallback models as original service
        self.models = [
            "gemini-2.5-pro-exp-03-25",
            "gemini-2.0-flash", 
            "gemini-1.5-flash"
        ]
        self.current_model_index = 0
    
    def generate_content(
        self, 
        prompt: str, 
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate content - maintains same interface as original service.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text content
        """
        for attempt in range(len(self.models)):
            try:
                model = self.models[self.current_model_index]
                self.logger.info(f"Generating with model: {model}")
                
                response = self.unified_service.generate(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return response.content
                
            except Exception as e:
                self.logger.warning(f"Model {model} failed: {e}")
                self.current_model_index = (self.current_model_index + 1) % len(self.models)
                
                if attempt == len(self.models) - 1:
                    self.logger.error("All models failed")
                    raise e
                
                time.sleep(1)  # Brief pause before retry
    
    def get_current_model(self) -> str:
        """Get the currently active model."""
        return self.models[self.current_model_index]
    
    def reset_model(self):
        """Reset to the primary model."""
        self.current_model_index = 0


class LLMMigrationTester:
    """Test and validate the LLM service migration."""
    
    def __init__(self):
        self.unified_service = UnifiedLLMService()
        self.legacy_wrapper = LegacyLLMServiceWrapper()
        self.test_results = {}
    
    def test_provider_availability(self) -> Dict[str, bool]:
        """Test which providers are available."""
        results = {}
        available_models = self.unified_service.list_available_models()
        
        for provider, models in available_models.items():
            try:
                if models:
                    # Test with first available model
                    test_model = models[0]
                    response = self.unified_service.generate(
                        "Hello", 
                        model=test_model,
                        max_tokens=10
                    )
                    results[provider] = True
                    print(f"✅ {provider}: Working (tested {test_model})")
                else:
                    results[provider] = False
                    print(f"❌ {provider}: No models available")
            except Exception as e:
                results[provider] = False
                print(f"❌ {provider}: Error - {e}")
        
        return results
    
    def test_backward_compatibility(self) -> bool:
        """Test that the legacy wrapper works correctly."""
        try:
            # Test legacy interface
            response = self.legacy_wrapper.generate_content(
                "Say hello in one word",
                temperature=0.1,
                max_tokens=10
            )
            
            if response and len(response) > 0:
                print(f"✅ Legacy compatibility: Working")
                print(f"   Response: {response}")
                print(f"   Current model: {self.legacy_wrapper.get_current_model()}")
                return True
            else:
                print(f"❌ Legacy compatibility: Empty response")
                return False
                
        except Exception as e:
            print(f"❌ Legacy compatibility: Error - {e}")
            return False
    
    def test_model_switching(self) -> bool:
        """Test switching between different models."""
        test_models = ["gemini-2.0-flash", "gpt-4", "claude-3-sonnet"]
        successful_models = []
        
        for model in test_models:
            try:
                response = self.unified_service.generate(
                    "Hello",
                    model=model,
                    max_tokens=10
                )
                successful_models.append(model)
                print(f"✅ Model {model}: Working")
            except Exception as e:
                print(f"❌ Model {model}: {e}")
        
        return len(successful_models) > 0
    
    def test_streaming(self) -> bool:
        """Test streaming functionality."""
        try:
            print("🔄 Testing streaming...")
            chunks = []
            for chunk in self.unified_service.stream(
                "Count to 3",
                model="gemini-2.0-flash",
                max_tokens=20
            ):
                chunks.append(chunk)
                print(chunk, end="")
            
            print()
            if chunks:
                print(f"✅ Streaming: Working ({len(chunks)} chunks)")
                return True
            else:
                print(f"❌ Streaming: No chunks received")
                return False
                
        except Exception as e:
            print(f"❌ Streaming: Error - {e}")
            return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and return results."""
        print("🚀 Running LLM Service Migration Tests")
        print("=" * 50)
        
        results = {
            "provider_availability": self.test_provider_availability(),
            "backward_compatibility": self.test_backward_compatibility(),
            "model_switching": self.test_model_switching(),
            "streaming": self.test_streaming()
        }
        
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Migration ready.")
        else:
            print("⚠️  Some tests failed. Check configuration.")
        
        return results


def migration_checklist():
    """Print migration checklist for users."""
    print("""
🔄 LLM Service Migration Checklist

□ 1. Install new dependencies:
     pip install -r requirements_llm.txt

□ 2. Configure API keys:
     - Copy .env.llm.example to your .env file
     - Add your API keys for desired providers
     - At minimum, ensure Gemini GCP or Gemini API is configured

□ 3. Test the new service:
     python -c "from services.llm_migration_guide import LLMMigrationTester; LLMMigrationTester().run_comprehensive_test()"

□ 4. Update your code:
     Option A (Drop-in replacement):
     - Replace: from services.llm_service import LLMService
     - With: from services.llm_migration_guide import LegacyLLMServiceWrapper as LLMService
     
     Option B (New unified interface):
     - from services.unified_llm_service import UnifiedLLMService
     - service = UnifiedLLMService()
     - response = service.generate("prompt", "model-name")

□ 5. Update chat_service.py:
     - Replace LLM service import with unified service
     - Models can now be specified as strings (e.g., "gpt-4", "claude-3-sonnet")

□ 6. Test your existing functionality:
     - Chat endpoints should work unchanged with Option A
     - Robin routes should work unchanged with Option A

□ 7. Explore new capabilities:
     - Try different models: service.generate("prompt", "gpt-4")
     - Use streaming: for chunk in service.stream("prompt", "model"): ...
     - Check usage stats: service.get_usage_stats()

🎯 Benefits After Migration:
✅ Support for OpenAI, Anthropic, Grok models
✅ Automatic provider selection based on model name
✅ Streaming support across all providers
✅ Usage tracking and cost monitoring
✅ Better error handling and fallbacks
✅ Single configuration for all LLM providers
    """)


def create_example_usage():
    """Create example usage file."""
    example_code = '''
"""
Example usage of the Unified LLM Service
"""

from services.unified_llm_service import UnifiedLLMService

# Initialize service (loads config from environment)
llm = UnifiedLLMService()

# List available models
print("Available models:")
for provider, models in llm.list_available_models().items():
    print(f"  {provider}: {models}")

# Generate with different models
models_to_try = ["gemini-2.0-flash", "gpt-4", "claude-3-sonnet"]

for model in models_to_try:
    try:
        print(f"\\n--- Testing {model} ---")
        
        # Standard generation
        response = llm.generate(
            prompt="Explain quantum computing in one sentence",
            model=model,
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"Response: {response.content}")
        print(f"Provider: {response.provider}")
        print(f"Latency: {response.latency:.2f}s")
        if response.usage:
            print(f"Tokens: {response.usage}")
        
        # Streaming example
        print(f"\\nStreaming from {model}:")
        for chunk in llm.stream(
            prompt="Count from 1 to 5",
            model=model,
            max_tokens=50
        ):
            print(chunk, end="", flush=True)
        print("\\n")
        
    except Exception as e:
        print(f"Error with {model}: {e}")

# Show usage statistics
print(f"\\nUsage Stats: {llm.get_usage_stats()}")

# Example: Drop-in replacement for existing code
from services.llm_migration_guide import LegacyLLMServiceWrapper

legacy_llm = LegacyLLMServiceWrapper()
legacy_response = legacy_llm.generate_content(
    "Hello world",
    temperature=0.1,
    max_tokens=50
)
print(f"\\nLegacy interface response: {legacy_response}")
'''
    
    with open("/Users/sumanurawat/Documents/GitHub/phoenix/llm_usage_examples.py", "w") as f:
        f.write(example_code)
    
    print("📝 Created llm_usage_examples.py with example code")


if __name__ == "__main__":
    print("🔧 LLM Service Migration Utility")
    print("=" * 40)
    
    # Show migration checklist
    migration_checklist()
    
    # Create example usage file
    create_example_usage()
    
    # Run tests
    tester = LLMMigrationTester()
    results = tester.run_comprehensive_test()
    
    print("\n🎯 Next Steps:")
    if all(results.values()):
        print("1. Update your imports to use the new unified service")
        print("2. Enjoy multi-provider LLM support!")
    else:
        print("1. Check your API key configuration in .env")
        print("2. Install missing dependencies: pip install -r requirements_llm.txt")
        print("3. Re-run this test script")