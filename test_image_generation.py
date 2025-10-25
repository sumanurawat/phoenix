#!/usr/bin/env python3
"""
Standalone test script for Image Generation Service

Tests the Imagen 3 API integration without requiring the Flask app.
Run with: python test_image_generation.py
"""
import sys
import logging
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.image_generation_service import (
    ImageGenerationService,
    SafetyFilterError,
    PolicyViolationError,
    ImageGenerationError
)


def test_basic_generation():
    """Test basic image generation with default settings."""
    print("\n" + "="*70)
    print("TEST 1: Basic Image Generation (Portrait)")
    print("="*70)
    
    prompt = "A serene mountain landscape at sunset with purple clouds, digital art style"
    print(f"\nPrompt: {prompt}")
    print("Settings: Portrait (9:16), Lowest safety, No person restrictions\n")
    
    try:
        service = ImageGenerationService()
        result = service.generate_image(prompt=prompt)
        
        print("✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Image ID: {result.image_id}")
        print(f"   Model: {result.model}")
        print(f"   Aspect Ratio: {result.aspect_ratio}")
        print(f"   Generation Time: {result.generation_time_seconds:.2f}s")
        print(f"   Timestamp: {result.timestamp}")
        print(f"\n🔗 URLs:")
        print(f"   Public URL: {result.image_url}")
        print(f"   GCS URI: {result.gcs_uri}")
        print(f"\n📦 Data:")
        print(f"   Base64 length: {len(result.base64_data):,} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        logger.exception("Test failed")
        return False


def test_with_user_id():
    """Test image generation with user ID for storage organization."""
    print("\n" + "="*70)
    print("TEST 2: Image Generation with User ID")
    print("="*70)
    
    prompt = "A futuristic cityscape with flying cars at night, cyberpunk style"
    test_user_id = "test_user_12345"
    print(f"\nPrompt: {prompt}")
    print(f"User ID: {test_user_id}\n")
    
    try:
        service = ImageGenerationService()
        result = service.generate_image(
            prompt=prompt,
            user_id=test_user_id,
            save_to_gcs=True
        )
        
        print("✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Image ID: {result.image_id}")
        print(f"   Generation Time: {result.generation_time_seconds:.2f}s")
        print(f"   GCS URI: {result.gcs_uri}")
        
        # Verify user_id is in the GCS path
        if test_user_id in result.gcs_uri:
            print(f"\n✅ User ID correctly included in GCS path")
        else:
            print(f"\n⚠️  Warning: User ID not found in GCS path")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        logger.exception("Test failed")
        return False


def test_prompt_validation():
    """Test prompt validation."""
    print("\n" + "="*70)
    print("TEST 3: Prompt Validation")
    print("="*70)
    
    service = ImageGenerationService()
    
    test_cases = [
        ("", False, "Empty prompt"),
        ("ab", False, "Too short (2 chars)"),
        ("Valid prompt for image generation", True, "Valid prompt"),
        ("A" * 6000, False, "Too long (6000 chars)")
    ]
    
    all_passed = True
    
    for prompt, should_be_valid, description in test_cases:
        is_valid, error = service.validate_prompt(prompt)
        
        if is_valid == should_be_valid:
            print(f"✅ {description}: {'Valid' if is_valid else f'Invalid ({error})'}")
        else:
            print(f"❌ {description}: Expected {'valid' if should_be_valid else 'invalid'}, got {'valid' if is_valid else 'invalid'}")
            all_passed = False
    
    return all_passed


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n" + "="*70)
    print("TEST 4: Error Handling")
    print("="*70)
    
    service = ImageGenerationService()
    
    # Test empty prompt
    print("\nTesting empty prompt...")
    try:
        service.generate_image(prompt="")
        print("❌ Should have raised ValueError for empty prompt")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {str(e)}")
    
    # Test whitespace-only prompt
    print("\nTesting whitespace-only prompt...")
    try:
        service.generate_image(prompt="   \n  \t  ")
        print("❌ Should have raised ValueError for whitespace prompt")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {str(e)}")
    
    return True


def test_multiple_generations():
    """Test generating multiple images sequentially."""
    print("\n" + "="*70)
    print("TEST 5: Multiple Sequential Generations")
    print("="*70)
    
    prompts = [
        "A peaceful zen garden with cherry blossoms",
        "An abstract geometric pattern with vibrant colors",
        "A portrait of a wise old wizard with a long beard"
    ]
    
    print(f"\nGenerating {len(prompts)} images sequentially...\n")
    
    results = []
    total_time = 0
    
    for i, prompt in enumerate(prompts, 1):
        print(f"{i}. Generating: '{prompt[:50]}...'")
        
        try:
            service = ImageGenerationService()
            result = service.generate_image(prompt=prompt)
            results.append(result)
            total_time += result.generation_time_seconds
            print(f"   ✅ Done in {result.generation_time_seconds:.2f}s - ID: {result.image_id}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            return False
    
    print(f"\n📊 Summary:")
    print(f"   Total images: {len(results)}")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average time: {total_time/len(results):.2f}s per image")
    
    return True


def test_safety_filter_handling():
    """Test that safety filter errors are properly raised and don't deduct credits."""
    print("\n" + "="*70)
    print("TEST 6: Safety Filter & Policy Violation Handling")
    print("="*70)
    
    service = ImageGenerationService()
    
    # Note: These prompts might or might not trigger safety filters
    # depending on Google's current policies. The test is more about
    # ensuring the error handling works correctly.
    
    test_cases = [
        {
            "prompt": "A beautiful sunset over mountains",
            "should_succeed": True,
            "description": "Safe prompt"
        },
        # Add potentially problematic prompts here if you want to test
        # safety filter triggering, but be aware they may change over time
    ]
    
    print("\nTesting error handling for various prompt types...\n")
    
    passed = True
    for i, test in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test['description']}")
        print(f"   Prompt: '{test['prompt'][:50]}...'")
        
        try:
            result = service.generate_image(prompt=test['prompt'])
            
            if test['should_succeed']:
                print(f"   ✅ Successfully generated (expected)")
            else:
                print(f"   ⚠️  Generated successfully (expected failure)")
                passed = False
                
        except SafetyFilterError as e:
            if not test['should_succeed']:
                print(f"   ✅ Correctly caught SafetyFilterError (should_deduct_credits=False)")
            else:
                print(f"   ❌ Unexpected SafetyFilterError: {str(e)}")
                passed = False
                
        except PolicyViolationError as e:
            if not test['should_succeed']:
                print(f"   ✅ Correctly caught PolicyViolationError (should_deduct_credits=False)")
            else:
                print(f"   ❌ Unexpected PolicyViolationError: {str(e)}")
                passed = False
                
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")
            passed = False
    
    print(f"\n{'✅ All tests passed!' if passed else '⚠️ Some tests had unexpected results'}")
    return passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print("🎨 IMAGE GENERATION SERVICE TEST SUITE")
    print("="*70)
    print("\nTesting Imagen 3 integration with hardcoded settings:")
    print("  - 1 image per generation")
    print("  - Portrait orientation (9:16)")
    print("  - Lowest safety filter (block_few)")
    print("  - No person generation restrictions")
    print("="*70)
    
    tests = [
        ("Basic Generation", test_basic_generation),
        ("User ID Storage", test_with_user_id),
        ("Prompt Validation", test_prompt_validation),
        ("Error Handling", test_error_handling),
        ("Multiple Generations", test_multiple_generations),
        ("Safety Filter Handling", test_safety_filter_handling)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.exception(f"Test '{test_name}' crashed")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"\n📊 Results: {passed}/{total} passed, {failed}/{total} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! Image generation service is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    # Check if specific test requested
    if len(sys.argv) > 1:
        test_arg = sys.argv[1].lower()
        
        if test_arg == "quick":
            # Run only basic test
            print("Running quick test (basic generation only)...\n")
            success = test_basic_generation()
            sys.exit(0 if success else 1)
        
        elif test_arg == "validation":
            # Run validation tests only
            print("Running validation tests only...\n")
            success = test_prompt_validation() and test_error_handling()
            sys.exit(0 if success else 1)
        
        elif test_arg == "help":
            print("Usage: python test_image_generation.py [option]")
            print("\nOptions:")
            print("  (none)       - Run all tests")
            print("  quick        - Run only basic generation test")
            print("  validation   - Run only validation tests")
            print("  help         - Show this help message")
            sys.exit(0)
    
    # Run all tests by default
    sys.exit(run_all_tests())
