"""
Simple test script to validate the pipeline components work together.
This fetches a small subset of data and runs basic analysis.
"""

import json
import os
import logging
from data_fetcher import WorldBankAPI

def test_data_fetcher():
    """Test data fetcher with minimal data."""
    print("Testing Data Fetcher...")
    
    api = WorldBankAPI()
    
    # Test 1: Get a few countries
    print("  - Testing countries metadata...")
    countries_data = api._make_request('country', {'page': 1, 'per_page': 10})
    if countries_data and len(countries_data) > 1:
        with open('data/test_countries_small.json', 'w') as f:
            json.dump(countries_data[1][:5], f, indent=2)
        print("    ✓ Countries metadata test passed")
    else:
        print("    ✗ Countries metadata test failed")
        return False
    
    # Test 2: Get population for a few countries
    print("  - Testing population data...")
    pop_data = api._make_request('country/USA;CHN;IND/indicator/SP.POP.TOTL', {
        'date': '2020:2023'
    })
    if pop_data and len(pop_data) > 1:
        with open('data/test_population_small.json', 'w') as f:
            json.dump(pop_data[1][:10], f, indent=2)
        print("    ✓ Population data test passed")
    else:
        print("    ✗ Population data test failed")
        return False
    
    return True

def test_analysis_with_sample_data():
    """Test analysis components with sample data."""
    print("Testing Analysis Components...")
    
    # Create minimal test data
    sample_data = [
        {
            "country": {"id": "USA", "value": "United States"},
            "countryiso3code": "USA",
            "date": "2023",
            "value": 331900000
        },
        {
            "country": {"id": "USA", "value": "United States"},
            "countryiso3code": "USA",
            "date": "2022",
            "value": 329500000
        },
        {
            "country": {"id": "CHN", "value": "China"},
            "countryiso3code": "CHN",
            "date": "2023",
            "value": 1412000000
        },
        {
            "country": {"id": "CHN", "value": "China"},
            "countryiso3code": "CHN",
            "date": "2022",
            "value": 1411000000
        }
    ]
    
    # Save test data
    with open('data/population_timeseries.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    # Also create minimal countries and regional data
    countries_data = [
        {"id": "USA", "name": "United States", "region": {"value": "North America"}},
        {"id": "CHN", "name": "China", "region": {"value": "East Asia & Pacific"}}
    ]
    
    with open('data/countries_metadata.json', 'w') as f:
        json.dump(countries_data, f, indent=2)
    
    regional_data = [
        {
            "country": {"id": "WLD", "value": "World"},
            "countryiso3code": "WLD",
            "date": "2023",
            "value": 8000000000
        }
    ]
    
    with open('data/population_regions.json', 'w') as f:
        json.dump(regional_data, f, indent=2)
    
    print("  ✓ Sample test data created")
    
    # Test analyzer
    try:
        from data_analyzer import PopulationDataAnalyzer
        analyzer = PopulationDataAnalyzer()
        basic_stats = analyzer.calculate_basic_statistics()
        print("  ✓ Data analyzer test passed")
    except Exception as e:
        print(f"  ✗ Data analyzer test failed: {e}")
        return False
    
    # Test profiler
    try:
        from data_profiler import DataQualityProfiler
        profiler = DataQualityProfiler()
        completeness = profiler.analyze_completeness()
        print("  ✓ Data profiler test passed")
    except Exception as e:
        print(f"  ✗ Data profiler test failed: {e}")
        return False
    
    return True

def test_report_generation():
    """Test report generation."""
    print("Testing Report Generation...")
    
    try:
        from report_generator import ReportGenerator
        generator = ReportGenerator()
        
        # Generate a simple report section
        summary = generator.generate_executive_summary()
        
        # Save test report
        with open('outputs/test_report.md', 'w') as f:
            f.write("# Test Report\n\n")
            f.write(summary)
        
        print("  ✓ Report generator test passed")
        return True
        
    except Exception as e:
        print(f"  ✗ Report generator test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running Pipeline Component Tests")
    print("=" * 50)
    
    # Ensure directories exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)
    
    tests = [
        ("Data Fetcher", test_data_fetcher),
        ("Analysis Components", test_analysis_with_sample_data),
        ("Report Generation", test_report_generation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Pipeline is ready to run.")
        print("\nNext steps:")
        print("1. Run: python main.py --phase collection")
        print("2. Run: python main.py --skip-data-collection")
        print("3. Or run: python main.py (for full pipeline)")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
