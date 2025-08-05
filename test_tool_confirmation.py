"""
Interactive test for tool confirmation functionality.
Demonstrates the complete flow: tool detection -> user confirmation -> execution.
"""
import requests
import json
import time
import threading
from typing import Optional

BASE_URL = "http://localhost:8000"

class ToolConfirmationTester:
    def __init__(self):
        self.session_id = "interactive_test_session"
        self.pending_confirmation = None
        
    def test_tool_confirmation_flow(self, message: str):
        """Test the complete tool confirmation flow."""
        print(f"🧪 Testing tool confirmation with: '{message}'")
        print("=" * 60)
        
        payload = {
            "message": message,
            "session_id": self.session_id,
            "stream": True
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/chat/stream", 
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                print("✅ Streaming response started...")
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            chunk = json.loads(data_str)
                            self._handle_chunk(chunk)
                        except json.JSONDecodeError:
                            continue
                        except KeyboardInterrupt:
                            print("\n⏹️ Test interrupted by user")
                            break
                            
            else:
                print(f"❌ Streaming failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test error: {e}")
    
    def _handle_chunk(self, chunk: dict):
        """Handle different types of streaming chunks."""
        chunk_type = chunk.get("type")
        
        if chunk_type == "session_info":
            print(f"📋 Session: {chunk.get('session_id')}")
            
        elif chunk_type == "message":
            content = chunk.get("content", "")
            print(content, end="", flush=True)
            
        elif chunk_type == "tool_detected":
            print(f"\n🔍 Tool Detected: {chunk.get('name')}")
            print(f"   Description: {chunk.get('description')}")
            print(f"   Args Schema: {chunk.get('args_schema')}")
            
        elif chunk_type == "tool_confirmation_required":
            print(f"\n❓ Confirmation Required for: {chunk.get('tool_name')}")
            print(f"   Args: {chunk.get('args')}")
            print(f"   Description: {chunk.get('description')}")
            
            # Store confirmation details
            self.pending_confirmation = chunk
            
            # Start a thread to handle user input
            threading.Thread(target=self._handle_user_confirmation, daemon=True).start()
            
        elif chunk_type == "tool_confirmation_timeout":
            print(f"\n⏰ Confirmation Timeout: {chunk.get('message')}")
            
        elif chunk_type == "tool_confirmation_rejected":
            print(f"\n❌ Tool Rejected: {chunk.get('message')}")
            
        elif chunk_type == "tool_execution_start":
            print(f"\n⚙️ Executing: {chunk.get('tool_name')} with {chunk.get('args')}")
            
        elif chunk_type == "tool_result":
            print(f"\n✅ Tool Result: {chunk.get('result')}")
            
        elif chunk_type == "tool_error":
            print(f"\n❌ Tool Error: {chunk.get('error')}")
            
        elif chunk_type == "complete":
            print(f"\n✅ Completed for session: {chunk.get('session_id')}")
            
        elif chunk_type == "stream_end":
            print(f"\n🏁 Stream ended")
            return False  # Stop processing
            
        return True  # Continue processing
    
    def _handle_user_confirmation(self):
        """Handle user confirmation input in a separate thread."""
        if not self.pending_confirmation:
            return
            
        try:
            print(f"\n{'='*50}")
            print(f"🤔 Do you want to execute this tool?")
            print(f"   Tool: {self.pending_confirmation.get('tool_name')}")
            print(f"   Args: {self.pending_confirmation.get('args')}")
            print(f"   Description: {self.pending_confirmation.get('description')}")
            print(f"{'='*50}")
            print("Type 'y' to confirm, 'n' to reject, or modify args (format: a=5,b=3): ", end="")
            
            user_input = input().strip().lower()
            
            if user_input == 'y':
                confirmed = True
                tool_args = self.pending_confirmation.get('args', {})
            elif user_input == 'n':
                confirmed = False
                tool_args = None
            else:
                # Try to parse custom arguments
                confirmed = True
                tool_args = self._parse_custom_args(user_input)
                if tool_args is None:
                    tool_args = self.pending_confirmation.get('args', {})
            
            # Send confirmation
            self._send_confirmation(confirmed, tool_args)
            
        except Exception as e:
            print(f"\n❌ Error handling confirmation: {e}")
            # Default to rejection on error
            self._send_confirmation(False, None)
    
    def _parse_custom_args(self, input_str: str) -> Optional[dict]:
        """Parse custom arguments from user input."""
        try:
            args = {}
            pairs = input_str.split(',')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Try to convert to number if possible
                    try:
                        args[key] = float(value)
                    except ValueError:
                        args[key] = value
            return args if args else None
        except Exception:
            return None
    
    def _send_confirmation(self, confirmed: bool, tool_args: Optional[dict]):
        """Send confirmation response to the server."""
        payload = {
            "session_id": self.session_id,
            "confirmed": confirmed,
            "tool_args": tool_args
        }
        
        try:
            response = requests.post(f"{BASE_URL}/chat/tool-confirm", json=payload)
            if response.status_code == 200:
                if confirmed:
                    print(f"\n✅ Confirmation sent: Tool approved with args {tool_args}")
                else:
                    print(f"\n❌ Confirmation sent: Tool rejected")
            else:
                print(f"\n❌ Failed to send confirmation: {response.status_code}")
        except Exception as e:
            print(f"\n❌ Error sending confirmation: {e}")

def main():
    """Run interactive tool confirmation tests."""
    print("🧪 Interactive Tool Confirmation Tester")
    print("=" * 60)
    
    tester = ToolConfirmationTester()
    
    # Test different math operations
    test_cases = [
        "Calculate 25 + 17",
        "What is 8 * 6?",
        "Divide 100 by 5",
        "Subtract 15 from 30"
    ]
    
    print("Available test cases:")
    for i, case in enumerate(test_cases, 1):
        print(f"  {i}. {case}")
    
    print("\nChoose a test case (1-4) or enter custom message:")
    choice = input("> ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(test_cases):
        message = test_cases[int(choice) - 1]
    else:
        message = choice
    
    if message:
        tester.test_tool_confirmation_flow(message)
    else:
        print("❌ No message provided")

if __name__ == "__main__":
    main()
