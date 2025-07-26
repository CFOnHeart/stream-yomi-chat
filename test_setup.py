"""
Test script to verify the conversation agent setup.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")
    
    try:
        from utils.logger import setup_logger
        print("✓ Utils module imported successfully")
        
        from database.chat_history_database import get_database
        print("✓ Database module imported successfully")
        
        from agent.tools.math_tools import get_math_tools
        print("✓ Tools module imported successfully")
        
        from agent.models.loader import ModelLoader
        print("✓ Models module imported successfully")
        
        print("\n✓ All core modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_database():
    """Test database functionality."""
    print("\nTesting database...")
    
    try:
        from database.chat_history_database import get_database
        
        db = get_database()
        
        # Test message operations
        test_message = {
            "type": "human",
            "content": "Test message",
            "metadata": {"test": True}
        }
        
        db.save_message("test_session", test_message)
        messages = db.get_chat_history("test_session")
        
        if messages and len(messages) > 0:
            print("✓ Database operations working")
            
            # Clean up
            db.delete_session("test_session")
            print("✓ Database cleanup successful")
            return True
        else:
            print("✗ Database save/retrieve failed")
            return False
            
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def test_tools():
    """Test math tools."""
    print("\nTesting tools...")
    
    try:
        from agent.tools.math_tools import add, subtract, multiply, divide
        
        # Test each tool
        assert add.invoke({"a": 5, "b": 3}) == 8
        assert subtract.invoke({"a": 10, "b": 4}) == 6
        assert multiply.invoke({"a": 3, "b": 4}) == 12
        assert divide.invoke({"a": 15, "b": 3}) == 5
        
        print("✓ All math tools working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Tools error: {e}")
        return False

def test_logging():
    """Test logging system."""
    print("\nTesting logging...")
    
    try:
        from utils.logger import setup_logger, get_logger
        
        logger = setup_logger("test_logger")
        logger.info("Test log message")
        
        logger2 = get_logger("test_logger2")
        print("✓ Logging system working")
        return True
        
    except Exception as e:
        print(f"✗ Logging error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("Conversation Agent - System Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_database,
        test_tools,
        test_logging
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed! The system is ready.")
        print("\nTo start the server, run: python main.py")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
