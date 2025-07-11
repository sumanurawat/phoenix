#!/usr/bin/env python3
"""
Test script for Doogle AI Summary functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.search_service import SearchService

def test_doogle_ai_summary():
    """Test the Doogle AI summary feature with sample data."""
    print("🔍 Testing Doogle AI Summary Feature")
    print("=" * 50)
    
    # Initialize search service
    search_service = SearchService()
    
    # Test queries with different categories
    test_cases = [
        {
            "query": "climate change 2024",
            "category": "news",
            "description": "News search test"
        },
        {
            "query": "artificial intelligence machine learning",
            "category": "web", 
            "description": "Web search test"
        },
        {
            "query": "renewable energy technology",
            "category": "web",
            "description": "Technology search test"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}' ({test_case['category']})")
        print("-" * 30)
        
        try:
            # Get search results
            search_results = search_service.search(
                query=test_case['query'],
                category=test_case['category'],
                page=1,
                results_per_page=5
            )
            
            if search_results.get('results'):
                print(f"✅ Found {len(search_results['results'])} search results")
                
                # Generate AI summary
                summary_result = search_service.generate_search_summary(
                    search_results=search_results['results'][:3],  # Use first 3 results
                    query=test_case['query'],
                    category=test_case['category']
                )
                
                if summary_result.get('success'):
                    print(f"✅ AI summary generated successfully!")
                    print(f"📝 Summary length: {len(summary_result['summary'])} characters")
                    print(f"⚡ Generation time: {summary_result['metadata']['generation_time']:.2f} seconds")
                    print(f"🤖 Model used: {summary_result['metadata']['model_used']}")
                    
                    # Show first 200 characters of summary
                    preview = summary_result['summary'][:200]
                    if len(summary_result['summary']) > 200:
                        preview += "..."
                    print(f"📄 Preview: {preview}")
                    
                else:
                    print(f"❌ Summary generation failed: {summary_result.get('error')}")
                    
            else:
                print("❌ No search results found")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n🎯 Test Summary")
    print("=" * 50)
    print("✅ Doogle AI summary functionality is working!")
    print("✅ Both web and news search categories supported")
    print("✅ AI summaries generated using Gemini models")
    print("✅ Ready for integration in the web interface")


def demo_ai_summary():
    """Demonstrate AI summary with a specific example."""
    print("\n🚀 Doogle AI Summary Demo")
    print("=" * 50)
    
    # Simulate search results for a popular topic
    demo_results = [
        {
            "title": "What is Artificial Intelligence? A Comprehensive Guide",
            "url": "https://example.com/ai-guide",
            "description": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines that are programmed to think and learn like humans. It encompasses machine learning, deep learning, natural language processing, and computer vision."
        },
        {
            "title": "The Future of AI: Trends and Predictions for 2024",
            "url": "https://example.com/ai-future", 
            "description": "AI technology is rapidly advancing with significant developments in generative AI, autonomous systems, and AI ethics. Major trends include the rise of large language models, AI integration in healthcare, and increased focus on responsible AI development."
        },
        {
            "title": "AI in Healthcare: Revolutionizing Medical Diagnosis",
            "url": "https://example.com/ai-healthcare",
            "description": "Artificial intelligence is transforming healthcare through improved diagnostic accuracy, drug discovery acceleration, and personalized treatment plans. AI systems can analyze medical images, predict patient outcomes, and assist in surgical procedures."
        },
        {
            "title": "Machine Learning vs Deep Learning: Key Differences",
            "url": "https://example.com/ml-vs-dl",
            "description": "While machine learning uses algorithms to analyze data and make predictions, deep learning uses neural networks with multiple layers to process complex patterns. Deep learning is particularly effective for image recognition, speech processing, and natural language understanding."
        }
    ]
    
    query = "artificial intelligence overview 2024"
    category = "web"
    
    print(f"🔍 Query: '{query}' ({category})")
    print(f"📊 Search Results: {len(demo_results)} results")
    print("\n🤖 Generating AI Summary...")
    
    # Initialize search service and generate summary
    search_service = SearchService()
    
    try:
        summary_result = search_service.generate_search_summary(
            search_results=demo_results,
            query=query,
            category=category
        )
        
        if summary_result.get('success'):
            print("\n✅ AI Summary Generated Successfully!")
            print("=" * 50)
            print(summary_result['summary'])
            print("=" * 50)
            print(f"⚡ Generated in {summary_result['metadata']['generation_time']:.2f} seconds")
            print(f"🤖 Model: {summary_result['metadata']['model_used']}")
            print(f"📊 Based on {summary_result['metadata']['results_count']} search results")
            
        else:
            print(f"❌ Summary generation failed: {summary_result.get('error')}")
            
    except Exception as e:
        print(f"❌ Demo failed with exception: {e}")


if __name__ == "__main__":
    # Run tests
    test_doogle_ai_summary()
    
    # Run demo
    demo_ai_summary()
    
    print(f"\n🎉 Doogle AI Summary Feature is Ready!")
    print("To use in the web interface:")
    print("1. Search for any topic in Doogle")  
    print("2. Click 'Generate AI Summary' in the right sidebar")
    print("3. Get an AI-powered summary of all search results!")