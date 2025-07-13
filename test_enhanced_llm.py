#!/usr/bin/env python3
"""
Test script for Enhanced LLM Service
Tests both Gemini and Claude APIs to ensure they work locally
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.enhanced_llm_service import EnhancedLLMService, ModelProvider

def test_gemini():
    """Test Gemini API."""
    print("🤖 Testing Gemini API...")
    
    try:
        llm = EnhancedLLMService(provider=ModelProvider.GEMINI, model="gemini-1.5-flash")
        response = llm.generate_text("Say 'Hello from Gemini!' and explain what you are in one sentence.")
        
        if response.get("success"):
            print(f"✅ Gemini Success: {response['text'][:100]}...")
            print(f"📊 Model: {response['model']}")
            print(f"⏱️ Time: {response['response_time']:.2f}s")
            return True
        else:
            print(f"❌ Gemini Failed: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Gemini Exception: {e}")
        return False

def test_claude():
    """Test Claude API with latest Claude 4 model."""
    print("\n🤖 Testing Claude 4 API...")
    
    try:
        # Test Claude 4 Sonnet (latest and best balance)
        llm = EnhancedLLMService(provider=ModelProvider.CLAUDE, model="claude-sonnet-4-20250514")
        response = llm.generate_text("Say 'Hello from Claude 4 Sonnet!' and explain what you are in one sentence.")
        
        if response.get("success"):
            print(f"✅ Claude 4 Success: {response['text'][:100]}...")
            print(f"📊 Model: {response['model']}")
            print(f"⏱️ Time: {response['response_time']:.2f}s")
            return True
        else:
            print(f"❌ Claude 4 Failed: {response.get('error')}")
            # Fallback to Claude 3.5 for testing
            print("🔄 Trying fallback to Claude 3.5 Haiku...")
            llm = EnhancedLLMService(provider=ModelProvider.CLAUDE, model="claude-3-5-haiku-20241022")
            response = llm.generate_text("Say 'Hello from Claude 3.5!' and explain what you are in one sentence.")
            if response.get("success"):
                print(f"✅ Claude 3.5 Fallback Success: {response['text'][:100]}...")
                return True
            return False
            
    except Exception as e:
        print(f"❌ Claude Exception: {e}")
        return False

def test_model_switching():
    """Test switching between models."""
    print("\n🔄 Testing Model Switching...")
    
    try:
        # Start with Gemini
        llm = EnhancedLLMService(provider=ModelProvider.GEMINI, model="gemini-1.5-flash")
        
        # Test Gemini
        response1 = llm.generate_text("Say 'Test 1 from Gemini'")
        print(f"Test 1: {response1.get('text', 'Failed')[:50]}...")
        
        # Switch to Claude 4
        llm.switch_model(ModelProvider.CLAUDE, "claude-sonnet-4-20250514")
        
        # Test Claude
        response2 = llm.generate_text("Say 'Test 2 from Claude'")
        print(f"Test 2: {response2.get('text', 'Failed')[:50]}...")
        
        # Both should succeed
        return response1.get("success") and response2.get("success")
        
    except Exception as e:
        print(f"❌ Model Switching Exception: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Enhanced LLM Service Test Suite")
    print("=" * 40)
    
    # Test individual APIs
    gemini_ok = test_gemini()
    claude_ok = test_claude()
    
    # Test model switching
    switching_ok = test_model_switching()
    
    # Cost tracking test
    print("\n💰 Testing Cost Tracking...")
    llm = EnhancedLLMService(provider=ModelProvider.GEMINI, model="gemini-1.5-flash")
    llm.generate_text("Short test")
    cost_summary = llm.get_cost_summary()
    print(f"📊 Cost Summary: {cost_summary}")
    
    # Final results
    print("\n" + "=" * 40)
    print("📋 Test Results:")
    print(f"  Gemini API: {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    print(f"  Claude API: {'✅ PASS' if claude_ok else '❌ FAIL'}")
    print(f"  Model Switching: {'✅ PASS' if switching_ok else '❌ FAIL'}")
    
    if gemini_ok and claude_ok and switching_ok:
        print("\n🎉 All tests passed! Enhanced LLM Service is ready for production.")
        print("\n" + "=" * 50)
        print("💰 COST COMPARISON SUMMARY:")
        print("📊 Budget:     Gemini 2.5 Flash    ($0.01-0.05/analysis)")
        print("⭐ Balance:    Claude 4 Sonnet     ($0.20-0.50/analysis)")  
        print("🏆 Premium:    Claude 4 Opus       ($2.00-10.00/analysis)")
        print("\n💡 For development, use Gemini Flash (40x cheaper!)")
        print("💡 For production, use Claude 4 Sonnet (best balance)")
        print("💡 For complex coding, use Claude 4 Opus (world's best)")
        print("\n📖 See AI_MODEL_PRICING_COMPARISON.md for full details")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check API keys and configuration.")
        return 1

if __name__ == "__main__":
    exit(main())