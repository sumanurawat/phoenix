#!/usr/bin/env python3
"""
Quick test to verify Claude 4 Sonnet is working as the new default
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.enhanced_llm_service import EnhancedLLMService, ModelProvider

def test_claude_default():
    """Test that Claude 4 Sonnet works as the new default."""
    print("🧪 Testing Claude 4 Sonnet as new localhost default...")
    
    try:
        # Test default Claude initialization
        llm = EnhancedLLMService(provider=ModelProvider.CLAUDE)
        print(f"✅ Default Claude model: {llm.model}")
        
        # Test simple code generation
        prompt = "Write a simple Python function that takes a list of numbers and returns the average. Include error handling."
        response = llm.generate_text(prompt)
        
        if response.get("success"):
            print("✅ Claude 4 Sonnet code generation successful!")
            print(f"📊 Model used: {response['model']}")
            print(f"⏱️ Response time: {response['response_time']:.2f}s")
            print(f"💰 Cost tracking: {llm.get_cost_summary()}")
            print("\n📝 Generated code sample:")
            print(response['text'][:200] + "..." if len(response['text']) > 200 else response['text'])
            return True
        else:
            print(f"❌ Failed: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🚀 Claude 4 Sonnet Default Test")
    print("=" * 40)
    
    success = test_claude_default()
    
    if success:
        print("\n🎉 Claude 4 Sonnet is ready as the new localhost default!")
        print("💡 Your analysis will now use the world's best coding model")
        print("💰 Expected cost: ~$0.20-0.50 per analysis (5 iterations)")
    else:
        print("\n⚠️ Claude setup needs attention. Check API key and configuration.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())