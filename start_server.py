#!/usr/bin/env python3
"""
Quick start script for the Conversation Agent.
"""
import os
import sys
from pathlib import Path

def check_config():
    """Check if configuration files exist and are properly set up."""
    config_path = Path("agent/config/llm_config.yaml")
    
    if not config_path.exists():
        print("❌ Configuration file not found!")
        print(f"Please create {config_path} or copy from config_example.yaml")
        return False
    
    # Read config and check for placeholder API keys
    with open(config_path, 'r') as f:
        content = f.read()
    
    if "YOUR_" in content:
        print("⚠️  Configuration contains placeholder values!")
        print("Please update agent/config/llm_config.yaml with your actual API keys")
        return False
    
    print("✅ Configuration looks good!")
    return True

def main():
    """Main startup function."""
    print("🚀 Conversation Agent - Quick Start")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Check configuration
    if not check_config():
        print("\n📝 Setup steps:")
        print("1. Copy agent/config/config_example.yaml to agent/config/llm_config.yaml")
        print("2. Edit the file and add your API keys")
        print("3. Run this script again")
        sys.exit(1)
    
    print("\n🔄 Starting the server...")
    print("📡 The API will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("\n⏹️  Press Ctrl+C to stop the server")
    print("=" * 40)
    
    # Import and run
    try:
        import uvicorn
        uvicorn.run(
            "api.routes:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
