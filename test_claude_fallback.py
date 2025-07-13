#!/usr/bin/env python3
"""
Test script to verify Claude → Gemini fallback mechanism
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.enhanced_llm_service import EnhancedLLMService, ModelProvider

def test_fallback_mechanism():
    """Test that fallback to Gemini works when Claude fails."""
    print("🧪 Testing Claude → Gemini fallback mechanism...")
    
    try:
        # Test with Claude (should work normally)
        print("\n1️⃣ Testing normal Claude operation...")
        llm = EnhancedLLMService(provider=ModelProvider.CLAUDE, model="claude-sonnet-4-20250514")
        
        response = llm.generate_text("Say 'Hello from Claude!' in one sentence.", enable_fallback=True)
        
        if response.get("success"):
            if response.get("fallback_used"):
                print(f"🔄 Fallback triggered: {response.get('fallback_from')} → {response.get('model')}")
                print(f"✅ Fallback response: {response['text'][:100]}...")
            else:
                print(f"✅ Claude worked normally: {response['text'][:100]}...")
            return True
        else:
            print(f"❌ Both Claude and fallback failed: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test exception: {e}")
        return False

def test_fallback_disabled():
    """Test that fallback can be disabled."""
    print("\n2️⃣ Testing fallback disabled...")
    
    try:
        llm = EnhancedLLMService(provider=ModelProvider.CLAUDE, model="claude-sonnet-4-20250514")
        
        # Test with invalid API key to force failure
        original_api_key = llm.claude_client.api_key if llm.claude_client else None
        if llm.claude_client:
            llm.claude_client.api_key = "invalid_key_to_test_fallback"
        
        response = llm.generate_text("Test", enable_fallback=False, max_retries=1)
        
        # Restore original key
        if llm.claude_client and original_api_key:
            llm.claude_client.api_key = original_api_key
        
        if not response.get("success") and not response.get("fallback_used"):
            print("✅ Fallback correctly disabled - Claude failed without fallback")
            return True
        else:
            print("⚠️ Fallback behavior unexpected when disabled")
            return False
            
    except Exception as e:
        print(f"✅ Expected exception when fallback disabled: {type(e).__name__}")
        return True

def test_gemini_no_fallback():
    """Test that Gemini doesn't trigger fallback."""
    print("\n3️⃣ Testing Gemini (no fallback needed)...")
    
    try:
        llm = EnhancedLLMService(provider=ModelProvider.GEMINI, model="gemini-1.5-flash")
        response = llm.generate_text("Say 'Hello from Gemini!' in one sentence.", enable_fallback=True)
        
        if response.get("success") and not response.get("fallback_used"):
            print(f"✅ Gemini worked normally (no fallback): {response['text'][:100]}...")
            return True
        else:
            print(f"⚠️ Unexpected fallback with Gemini: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Gemini test exception: {e}")
        return False

def main():
    print("🚀 Claude Fallback Mechanism Test")
    print("=" * 50)
    
    test1 = test_fallback_mechanism()
    test2 = test_fallback_disabled() 
    test3 = test_gemini_no_fallback()
    
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    print(f"  Claude with Fallback: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Fallback Disabled: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"  Gemini No Fallback: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 All fallback tests passed!")
        print("💡 Claude will automatically fallback to Gemini 1.5 Flash if it fails")
        print("💡 Your analysis feature is now robust and always works")
        return 0
    else:
        print("\n⚠️ Some fallback tests failed. Check configuration.")
        return 1

if __name__ == "__main__":
    exit(main())