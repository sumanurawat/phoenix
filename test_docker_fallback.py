#!/usr/bin/env python3
"""
Test script to verify Docker fallback mechanism works correctly
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.dataset_discovery.docker_executor import docker_executor

def test_docker_fallback():
    """Test that Docker executor properly handles unavailable Docker daemon."""
    
    print("🧪 Testing Docker Executor Fallback Mechanism")
    print("=" * 50)
    
    # Test if Docker is available
    is_available = docker_executor.is_available()
    print(f"📋 Docker Available: {is_available}")
    
    # Create some test data files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test_data.csv"
        
        # Create a simple CSV file
        test_file.write_text("name,age,city\nJohn,25,NYC\nJane,30,LA\n")
        
        # Simple test code
        test_code = """
import pandas as pd
print("🚀 Loading test data...")
df = pd.read_csv(main_file)
print(f"✅ Data shape: {df.shape}")
print(f"📊 Data preview:")
print(df.head())
print("🏁 Test completed successfully!")
"""
        
        print(f"\n🔧 Executing test code...")
        print(f"📁 Test file: {test_file}")
        print(f"📝 Code length: {len(test_code)} characters")
        
        # Execute the code
        result = docker_executor.execute_code(test_code, [test_file])
        
        print(f"\n📊 Execution Results:")
        print(f"✅ Success: {result.get('success', False)}")
        print(f"⏱️ Execution time: {result.get('execution_time', 0):.2f}s")
        
        if result.get('success'):
            print(f"📤 Output:")
            print(result.get('output', ''))
        else:
            print(f"❌ Error:")
            print(result.get('error', ''))
            
        print("\n" + "=" * 50)
        
        if not is_available and not result.get('success'):
            print("✅ EXPECTED: Docker unavailable, should fall back to local execution")
            print("ℹ️  This is the expected behavior when Docker daemon is not running")
        elif result.get('success'):
            print("✅ SUCCESS: Code executed successfully!")
        else:
            print("❌ UNEXPECTED: Something went wrong")
            
        return result.get('success', False)

if __name__ == "__main__":
    success = test_docker_fallback()
    sys.exit(0 if success else 1)