#!/usr/bin/env python3
"""
NUMBLE Multiplayer Game WebSocket API Test
Tests the complete game flow including room creation, joining, secret setting, and gameplay.
"""

import asyncio
import websockets
import json
import sys
import uuid
from datetime import datetime

class NumbleGameTester:
    def __init__(self, backend_url="https://fastmath-2.preview.emergentagent.com"):
        self.backend_url = backend_url
        # Convert HTTP URL to WebSocket URL
        if backend_url.startswith('https'):
            self.ws_url = backend_url.replace('https://', 'wss://')
        else:
            self.ws_url = backend_url.replace('http://', 'ws://')
        
        self.client_a_id = str(uuid.uuid4())
        self.client_b_id = str(uuid.uuid4())
        self.room_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    async def connect_client(self, client_id):
        """Connect a WebSocket client"""
        try:
            uri = f"{self.ws_url}/api/ws/{client_id}"
            websocket = await websockets.connect(uri)
            return websocket
        except Exception as e:
            print(f"❌ Failed to connect client {client_id}: {e}")
            return None

    async def send_and_wait(self, websocket, message, expected_type=None, timeout=5):
        """Send message and wait for response"""
        try:
            await websocket.send(json.dumps(message))
            
            if expected_type:
                response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                data = json.loads(response)
                return data if data.get('type') == expected_type else None
            return True
        except Exception as e:
            print(f"❌ WebSocket communication error: {e}")
            return None

    async def test_room_creation(self, client_a):
        """Test Client A creating a room"""
        print("\n🔍 Testing Room Creation...")
        
        response = await self.send_and_wait(
            client_a, 
            {"action": "create_room"}, 
            "room_created"
        )
        
        if response and 'room_id' in response:
            self.room_id = response['room_id']
            return self.log_test("Room Creation", True, f"Room ID: {self.room_id}")
        else:
            return self.log_test("Room Creation", False, "No room_id received")

    async def test_room_joining(self, client_b):
        """Test Client B joining the room"""
        print("\n🔍 Testing Room Joining...")
        
        if not self.room_id:
            return self.log_test("Room Joining", False, "No room_id available")
        
        response = await self.send_and_wait(
            client_b,
            {"action": "join_room", "room_id": self.room_id},
            "joined_room"
        )
        
        success = response is not None
        return self.log_test("Room Joining", success, f"Joined room: {self.room_id}" if success else "Failed to join")

    async def test_secret_setting(self, client_a, client_b):
        """Test both clients setting secret numbers"""
        print("\n🔍 Testing Secret Number Setting...")
        
        # Client A sets secret "1234"
        await self.send_and_wait(
            client_a,
            {"action": "set_secret", "room_id": self.room_id, "secret": "1234"}
        )
        
        # Client B sets secret "5678"
        await self.send_and_wait(
            client_b,
            {"action": "set_secret", "room_id": self.room_id, "secret": "5678"}
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.5)
        
        return self.log_test("Secret Setting", True, "Both clients set secrets")

    async def test_invalid_secret_validation(self, client_a):
        """Test validation: Try setting '1122' as secret (should fail)"""
        print("\n🔍 Testing Invalid Secret Validation...")
        
        # Try to set invalid secret with repeating digits
        await client_a.send(json.dumps({
            "action": "set_secret", 
            "room_id": self.room_id, 
            "secret": "1122"
        }))
        
        try:
            # Wait for error response
            response = await asyncio.wait_for(client_a.recv(), timeout=3)
            data = json.parse(response)
            
            if data.get('type') == 'error' and 'Invalid secret' in data.get('message', ''):
                return self.log_test("Invalid Secret Validation", True, "Correctly rejected '1122'")
            else:
                return self.log_test("Invalid Secret Validation", False, f"Unexpected response: {data}")
        except asyncio.TimeoutError:
            return self.log_test("Invalid Secret Validation", False, "No error response received")

    async def test_game_start(self, client_a):
        """Test host starting the game"""
        print("\n🔍 Testing Game Start...")
        
        response = await self.send_and_wait(
            client_a,
            {"action": "start_game", "room_id": self.room_id},
            "game_started"
        )
        
        success = response is not None
        return self.log_test("Game Start", success, "Game started successfully" if success else "Failed to start game")

    async def test_winning_guess(self, client_a):
        """Test Client A making winning guess '5678'"""
        print("\n🔍 Testing Winning Guess...")
        
        # Client A guesses "5678" (Client B's secret)
        await client_a.send(json.dumps({
            "action": "submit_guess",
            "room_id": self.room_id,
            "guess": "5678"
        }))
        
        try:
            # Wait for game_over message
            response = await asyncio.wait_for(client_a.recv(), timeout=5)
            data = json.loads(response)
            
            if data.get('type') == 'game_over' and data.get('winner_id') == self.client_a_id:
                return self.log_test("Winning Guess", True, "Client A won with correct guess")
            else:
                return self.log_test("Winning Guess", False, f"Unexpected response: {data}")
        except asyncio.TimeoutError:
            return self.log_test("Winning Guess", False, "No game_over response received")

    async def test_invalid_guess_validation(self, client_a):
        """Test validation: Try guessing '0000' (should fail)"""
        print("\n🔍 Testing Invalid Guess Validation...")
        
        # Try to make invalid guess with repeating digits
        await client_a.send(json.dumps({
            "action": "submit_guess",
            "room_id": self.room_id,
            "guess": "0000"
        }))
        
        try:
            # Wait for error response
            response = await asyncio.wait_for(client_a.recv(), timeout=3)
            data = json.loads(response)
            
            if data.get('type') == 'error' and 'Invalid guess' in data.get('message', ''):
                return self.log_test("Invalid Guess Validation", True, "Correctly rejected '0000'")
            else:
                return self.log_test("Invalid Guess Validation", False, f"Unexpected response: {data}")
        except asyncio.TimeoutError:
            return self.log_test("Invalid Guess Validation", False, "No error response received")

    async def run_full_test_suite(self):
        """Run the complete test suite"""
        print(f"🚀 Starting NUMBLE Game Test Suite")
        print(f"Backend URL: {self.backend_url}")
        print(f"WebSocket URL: {self.ws_url}")
        print(f"Client A ID: {self.client_a_id}")
        print(f"Client B ID: {self.client_b_id}")
        
        try:
            # Connect both clients
            print("\n🔌 Connecting clients...")
            client_a = await self.connect_client(self.client_a_id)
            client_b = await self.connect_client(self.client_b_id)
            
            if not client_a or not client_b:
                print("❌ Failed to connect clients")
                return False
            
            print("✅ Both clients connected successfully")
            
            # Run test sequence
            success = True
            success &= await self.test_room_creation(client_a)
            success &= await self.test_room_joining(client_b)
            success &= await self.test_secret_setting(client_a, client_b)
            success &= await self.test_invalid_secret_validation(client_a)
            success &= await self.test_game_start(client_a)
            success &= await self.test_winning_guess(client_a)
            success &= await self.test_invalid_guess_validation(client_a)
            
            # Close connections
            await client_a.close()
            await client_b.close()
            
            return success
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            return False

    def print_results(self):
        """Print final test results"""
        print(f"\n📊 Test Results:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed")
            return False

async def main():
    """Main test function"""
    tester = NumbleGameTester()
    
    try:
        success = await tester.run_full_test_suite()
        final_success = tester.print_results()
        
        return 0 if final_success else 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)