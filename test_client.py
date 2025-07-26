"""
Simple test client for the Conversation Agent API.
Demonstrates how to interact with the streaming chat endpoint.
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if the service is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is running!")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to service: {e}")
        print("💡 Make sure the server is running on http://localhost:8000")
        return False

def test_tools():
    """Test the tools endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/tools")
        if response.status_code == 200:
            tools = response.json()
            print(f"✅ Available tools: {len(tools['tools'])}")
            for tool in tools['tools']:
                print(f"   - {tool['name']}: {tool['description']}")
            return True
        else:
            print(f"❌ Tools endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Tools test error: {e}")
        return False

def test_chat_complete():
    """Test the complete chat endpoint."""
    print("\n🧮 Testing math calculation...")
    
    payload = {
        "message": "What is 15 * 8?",
        "session_id": "test_session_1"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response: {result['response']}")
            print(f"📝 Session ID: {result['session_id']}")
            if result.get('tool_calls'):
                print(f"🔧 Tool calls made: {len(result['tool_calls'])}")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat test error: {e}")
        return False

def test_chat_stream():
    """Test the streaming chat endpoint."""
    print("\n🌊 Testing streaming chat...")
    
    payload = {
        "message": "Calculate 25 + 17 and then divide by 3",
        "session_id": "test_session_2",
        "stream": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/stream", 
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Streaming response:")
            print("📟 ", end="", flush=True)
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get("type") == "message":
                            print(chunk.get("content", ""), end="", flush=True)
                        elif chunk.get("type") == "tool_call":
                            print(f"\n🔧 Tool: {chunk.get('name')} with args {chunk.get('args')}")
                        elif chunk.get("type") == "tool_result":
                            print(f"🔧 Result: {chunk.get('result')}")
                        elif chunk.get("type") == "complete":
                            print(f"\n✅ Completed for session: {chunk.get('session_id')}")
                        elif chunk.get("type") == "stream_end":
                            break
                    except json.JSONDecodeError:
                        continue
            
            print("\n✅ Streaming test completed!")
            return True
        else:
            print(f"❌ Streaming failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Streaming test error: {e}")
        return False

def test_session_info():
    """Test session information endpoint."""
    print("\n📊 Testing session info...")
    
    try:
        response = requests.get(f"{BASE_URL}/session/test_session_1")
        if response.status_code == 200:
            info = response.json()
            print(f"✅ Session info:")
            print(f"   - Total characters: {info.get('total_characters', 0)}")
            print(f"   - Message count: {info.get('message_count', 0)}")
            print(f"   - Needs compression: {info.get('needs_compression', False)}")
            return True
        else:
            print(f"❌ Session info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session info error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Conversation Agent API Test Client")
    print("=" * 50)
    
    # Check if service is running
    if not test_health():
        sys.exit(1)
    
    print("\n🔍 Testing API endpoints...")
    
    tests = [
        ("Tools Endpoint", test_tools),
        ("Complete Chat", test_chat_complete),
        ("Streaming Chat", test_chat_stream),
        ("Session Info", test_session_info),
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"\n📋 {name}:")
        try:
            if test_func():
                passed += 1
        except KeyboardInterrupt:
            print("\n⏹️ Tests interrupted by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error in {name}: {e}")
    
    print(f"\n📊 Test Results: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The API is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the server logs for details.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
