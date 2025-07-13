#!/usr/bin/env python3
"""
Quick setup script for Kaggle credentials.
Helps you set up the Dataset Discovery feature credentials.
"""
import os
import json
from pathlib import Path

def main():
    print("🔧 Kaggle Credentials Setup for Dataset Discovery")
    print("=" * 55)
    
    # Check if .env file exists
    env_file = Path(".env")
    env_exists = env_file.exists()
    
    print(f"📁 .env file: {'Found' if env_exists else 'Not found'}")
    
    # Check current environment variables
    current_username = os.getenv('KAGGLE_USERNAME')
    current_key = os.getenv('KAGGLE_KEY')
    
    if current_username and current_key:
        print(f"✅ Kaggle credentials already set:")
        print(f"   Username: {current_username}")
        print(f"   Key: {current_key[:8]}..." if len(current_key) > 8 else "   Key: (short)")
        
        response = input("\n🤔 Do you want to update them? (y/N): ").lower().strip()
        if response not in ['y', 'yes']:
            print("✅ Keeping existing credentials")
            return
    
    # Check for kaggle.json file
    kaggle_json_path = Path.home() / '.kaggle' / 'kaggle.json'
    
    if kaggle_json_path.exists():
        print(f"\n📄 Found kaggle.json at: {kaggle_json_path}")
        
        try:
            with open(kaggle_json_path, 'r') as f:
                credentials = json.load(f)
                
            username = credentials.get('username')
            key = credentials.get('key')
            
            if username and key:
                print(f"   Username: {username}")
                print(f"   Key: {key[:8]}..." if len(key) > 8 else "   Key: (found)")
                
                response = input("\n🤔 Use these credentials from kaggle.json? (Y/n): ").lower().strip()
                if response not in ['n', 'no']:
                    setup_credentials(username, key, env_file)
                    return
        except Exception as e:
            print(f"❌ Error reading kaggle.json: {e}")
    
    # Manual input
    print("\n📝 Please enter your Kaggle credentials:")
    print("   (Get them from https://www.kaggle.com/account → API → Create New Token)")
    
    username = input("\n🧑 Kaggle Username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return
    
    key = input("🔑 Kaggle API Key: ").strip()
    if not key:
        print("❌ API key cannot be empty")
        return
    
    setup_credentials(username, key, env_file)

def setup_credentials(username: str, key: str, env_file: Path):
    """Set up credentials in .env file."""
    print(f"\n💾 Setting up credentials...")
    
    # Read existing .env content
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Remove existing KAGGLE entries
    lines = env_content.split('\n')
    filtered_lines = [line for line in lines if not line.startswith(('KAGGLE_USERNAME=', 'KAGGLE_KEY='))]
    
    # Add new credentials
    filtered_lines.append(f"KAGGLE_USERNAME={username}")
    filtered_lines.append(f"KAGGLE_KEY={key}")
    
    # Remove empty lines at the end
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.write('\n'.join(filtered_lines) + '\n')
    
    print(f"✅ Credentials saved to {env_file}")
    print(f"   KAGGLE_USERNAME={username}")
    print(f"   KAGGLE_KEY={key[:8]}...")
    
    # Test the credentials
    print(f"\n🧪 Testing credentials...")
    
    try:
        # Set environment variables for testing
        os.environ['KAGGLE_USERNAME'] = username
        os.environ['KAGGLE_KEY'] = key
        
        # Import and test
        from services.dataset_discovery.config import DatasetConfig
        
        config = DatasetConfig()
        print("✅ Credentials validated successfully!")
        
        print(f"\n🎉 Setup complete! You can now:")
        print(f"   1. Restart Phoenix: ./start_local.sh")
        print(f"   2. Visit: http://localhost:8080/datasets")
        print(f"   3. Test search: 'machine learning'")
        
    except Exception as e:
        print(f"❌ Credential test failed: {e}")
        print(f"   Please check your username and API key")
        print(f"   Get new credentials from: https://www.kaggle.com/account")

if __name__ == "__main__":
    main()