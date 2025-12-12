#!/usr/bin/env python3
"""
NUMBLE Backend API and WebSocket Test Suite
Tests all backend functionality including WebSocket multiplayer flow
"""

import asyncio
import websockets
import json
import uuid
import sys
import requests
from datetime import datetime

class NUMBLEBackendTester:
    def __init__(self, backend_url="https://fastmath-2.preview.emergentagent.com"):
        self.backend_url = backend_url
        if backend_url.startswith('https'):
            self.ws_url = backend_url.replace('https://', 'wss://')
        else:
            self.ws_url = backend_url.replace('http://', 'ws://')
        
        self.tests_run = 0
        self.tests_passed = 0
        
    def run_test(self, name, test_func):
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            result = test_func()
            if result:
                self.tests_passed += 1
                print(f"✅ {name} - PASSED")
            else:
                print(f"❌ {name} - FAILED")
            return result
        except Exception as e:
            print(f"❌ {name} - ERROR: {str(e)}")
            return False

    async def run_async_test(self, name, test_func):
        """Run a single async test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            result = await test_func()
            if result:
                self.tests_passed += 1
                print(f"✅ {name} - PASSED")
            else:
                print(f"❌ {name} - FAILED")
            return result
        except Exception as e:
            print(f"❌ {name} - ERROR: {str(e)}")
            return False

    def test_api_health(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.backend_url}/api/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("message") == "NUMBLE API"
            return False
        except Exception as e:
            print(f"API Health check failed: {e}")
            return False

    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            client_id = str(uuid.uuid4())
            uri = f"{self.ws_url}/api/ws/{client_id}"
            
            async with websockets.connect(uri) as websocket:
                print(f"Connected to WebSocket: {uri}")
                return True
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            return False

    async def test_room_creation(self):
        """Test room creation functionality"""
        try:
            client_id = str(uuid.uuid4())
            uri = f"{self.ws_url}/api/ws/{client_id}"
            
            async with websockets.connect(uri) as websocket:
                # Send create room request
                await websocket.send(json.dumps({"action": "create_room"}))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                
                if data.get('type') == 'room_created' and 'room_id' in data:
                    print(f"Room created: {data['room_id']}")
                    return True
                return False
        except Exception as e:
            print(f"Room creation failed: {e}")
            return False

    async def test_multiplayer_setup_flow(self):
        """Test complete multiplayer setup flow"""
        try:
            client_a_id = str(uuid.uuid4())
            client_b_id = str(uuid.uuid4())
            
            # Connect both clients
            uri_a = f"{self.ws_url}/api/ws/{client_a_id}"
            uri_b = f"{self.ws_url}/api/ws/{client_b_id}"
            
            async with websockets.connect(uri_a) as client_a, \
                       websockets.connect(uri_b) as client_b:
                
                # Step 1: Client A creates room
                await client_a.send(json.dumps({"action": "create_room"}))
                response = await client_a.recv()
                data = json.loads(response)
                
                if data.get('type') != 'room_created':
                    return False
                
                room_id = data['room_id']
                print(f"Room created: {room_id}")
                
                # Step 2: Client B joins room
                await client_b.send(json.dumps({"action": "join_room", "room_id": room_id}))
                
                # Wait for join confirmation and game state update
                messages = []
                for _ in range(4):  # Collect multiple messages
                    try:
                        msg_a = await asyncio.wait_for(client_a.recv(), timeout=2)
                        messages.append(json.loads(msg_a))
                    except asyncio.TimeoutError:
                        break
                
                for _ in range(4):
                    try:
                        msg_b = await asyncio.wait_for(client_b.recv(), timeout=2)
                        messages.append(json.loads(msg_b))
                    except asyncio.TimeoutError:
                        break
                
                # Check for player_joined message with setup status
                player_joined = any(msg.get('type') == 'player_joined' and 
                                  msg.get('game_state', {}).get('status') == 'setup' 
                                  for msg in messages)
                
                if not player_joined:
                    print("Player join or setup state not received")
                    return False
                
                # Step 3: Both players set setup (name + secret)
                await client_a.send(json.dumps({
                    "action": "set_setup", 
                    "room_id": room_id, 
                    "name": "Player A",
                    "secret": "1234"
                }))
                
                await client_b.send(json.dumps({
                    "action": "set_setup", 
                    "room_id": room_id, 
                    "name": "Player B", 
                    "secret": "5678"
                }))
                
                # Wait for ready confirmations
                ready_messages = []
                for _ in range(6):  # Expect multiple ready messages
                    try:
                        msg_a = await asyncio.wait_for(client_a.recv(), timeout=2)
                        ready_messages.append(json.loads(msg_a))
                    except asyncio.TimeoutError:
                        break
                
                for _ in range(6):
                    try:
                        msg_b = await asyncio.wait_for(client_b.recv(), timeout=2)
                        ready_messages.append(json.loads(msg_b))
                    except asyncio.TimeoutError:
                        break
                
                ready_count = len([msg for msg in ready_messages if msg.get('type') == 'player_ready'])
                print(f"Received {ready_count} player_ready messages")
                
                if ready_count < 2:
                    print("Not enough player_ready messages received")
                    return False
                
                # Step 4: Host starts game
                await client_a.send(json.dumps({"action": "start_game", "room_id": room_id}))
                
                # Wait for game start
                game_started = False
                for _ in range(4):
                    try:
                        msg_a = await asyncio.wait_for(client_a.recv(), timeout=2)
                        data_a = json.loads(msg_a)
                        if data_a.get('type') == 'game_started':
                            game_started = True
                            print(f"Game started with players: {data_a.get('players', {})}")
                            break
                    except asyncio.TimeoutError:
                        pass
                
                return game_started
                
        except Exception as e:
            print(f"Multiplayer setup flow failed: {e}")
            return False

    async def test_game_mechanics(self):
        """Test game mechanics including guessing and win conditions"""
        try:
            client_a_id = str(uuid.uuid4())
            client_b_id = str(uuid.uuid4())
            
            uri_a = f"{self.ws_url}/api/ws/{client_a_id}"
            uri_b = f"{self.ws_url}/api/ws/{client_b_id}"
            
            async with websockets.connect(uri_a) as client_a, \
                       websockets.connect(uri_b) as client_b:
                
                # Quick setup
                await client_a.send(json.dumps({"action": "create_room"}))
                response = await client_a.recv()
                room_id = json.loads(response)['room_id']
                
                await client_b.send(json.dumps({"action": "join_room", "room_id": room_id}))
                await asyncio.sleep(1)  # Wait for join
                
                # Clear any pending messages
                for _ in range(5):
                    try:
                        await asyncio.wait_for(client_a.recv(), timeout=0.5)
                        await asyncio.wait_for(client_b.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        break
                
                # Set secrets
                await client_a.send(json.dumps({
                    "action": "set_setup", "room_id": room_id, 
                    "name": "Player A", "secret": "1234"
                }))
                await client_b.send(json.dumps({
                    "action": "set_setup", "room_id": room_id, 
                    "name": "Player B", "secret": "5678"
                }))
                
                await asyncio.sleep(1)  # Wait for ready
                
                # Clear ready messages
                for _ in range(5):
                    try:
                        await asyncio.wait_for(client_a.recv(), timeout=0.5)
                        await asyncio.wait_for(client_b.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        break
                
                # Start game
                await client_a.send(json.dumps({"action": "start_game", "room_id": room_id}))
                await asyncio.sleep(1)  # Wait for start
                
                # Clear start messages
                for _ in range(3):
                    try:
                        await asyncio.wait_for(client_a.recv(), timeout=0.5)
                        await asyncio.wait_for(client_b.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        break
                
                # Test guess submission
                await client_a.send(json.dumps({
                    "action": "submit_guess", "room_id": room_id, "guess": "9876"
                }))
                
                # Wait for guess response
                guess_received = False
                for _ in range(3):
                    try:
                        msg = await asyncio.wait_for(client_a.recv(), timeout=2)
                        data = json.loads(msg)
                        if data.get('type') == 'guess_made':
                            guess_received = True
                            print(f"Guess processed: {data}")
                            break
                    except asyncio.TimeoutError:
                        pass
                
                if not guess_received:
                    return False
                
                # Test winning guess
                await client_a.send(json.dumps({
                    "action": "submit_guess", "room_id": room_id, "guess": "5678"
                }))
                
                # Wait for game over
                game_over = False
                for _ in range(3):
                    try:
                        msg = await asyncio.wait_for(client_a.recv(), timeout=2)
                        data = json.loads(msg)
                        if data.get('type') == 'game_over':
                            game_over = True
                            print(f"Game over: {data}")
                            break
                    except asyncio.TimeoutError:
                        pass
                
                return game_over
                
        except Exception as e:
            print(f"Game mechanics test failed: {e}")
            return False

    async def test_disconnect_handling(self):
        """Test disconnect handling during game"""
        try:
            client_a_id = str(uuid.uuid4())
            client_b_id = str(uuid.uuid4())
            
            uri_a = f"{self.ws_url}/api/ws/{client_a_id}"
            uri_b = f"{self.ws_url}/api/ws/{client_b_id}"
            
            client_a = await websockets.connect(uri_a)
            client_b = await websockets.connect(uri_b)
            
            # Quick setup to playing state
            await client_a.send(json.dumps({"action": "create_room"}))
            response = await client_a.recv()
            room_id = json.loads(response)['room_id']
            
            await client_b.send(json.dumps({"action": "join_room", "room_id": room_id}))
            await asyncio.sleep(1)
            
            # Clear messages
            for _ in range(5):
                try:
                    await asyncio.wait_for(client_a.recv(), timeout=0.5)
                    await asyncio.wait_for(client_b.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    break
            
            # Set secrets and start
            await client_a.send(json.dumps({
                "action": "set_setup", "room_id": room_id, 
                "name": "Player A", "secret": "1234"
            }))
            await client_b.send(json.dumps({
                "action": "set_setup", "room_id": room_id, 
                "name": "Player B", "secret": "5678"
            }))
            
            await asyncio.sleep(1)
            
            # Clear ready messages
            for _ in range(5):
                try:
                    await asyncio.wait_for(client_a.recv(), timeout=0.5)
                    await asyncio.wait_for(client_b.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    break
            
            await client_a.send(json.dumps({"action": "start_game", "room_id": room_id}))
            await asyncio.sleep(1)
            
            # Clear start messages
            for _ in range(3):
                try:
                    await asyncio.wait_for(client_a.recv(), timeout=0.5)
                    await asyncio.wait_for(client_b.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    break
            
            # Disconnect client A during game
            await client_a.close()
            print("Client A disconnected")
            
            # Check if client B receives disconnect notification
            disconnect_handled = False
            for _ in range(3):
                try:
                    msg = await asyncio.wait_for(client_b.recv(), timeout=3)
                    data = json.loads(msg)
                    if data.get('type') == 'game_over' and data.get('reason') == 'opponent_disconnected':
                        disconnect_handled = True
                        print(f"Disconnect handled: {data}")
                        break
                except asyncio.TimeoutError:
                    pass
            
            await client_b.close()
            return disconnect_handled
            
        except Exception as e:
            print(f"Disconnect handling test failed: {e}")
            return False

async def main():
    """Main test function"""
    print("🚀 Starting NUMBLE Backend Test Suite")
    print(f"Backend URL: https://fastmath-2.preview.emergentagent.com")
    
    tester = NUMBLEBackendTester()
    
    # Run tests
    tester.run_test("API Health Check", tester.test_api_health)
    await tester.run_async_test("WebSocket Connection", tester.test_websocket_connection)
    await tester.run_async_test("Room Creation", tester.test_room_creation)
    await tester.run_async_test("Multiplayer Setup Flow", tester.test_multiplayer_setup_flow)
    await tester.run_async_test("Game Mechanics", tester.test_game_mechanics)
    await tester.run_async_test("Disconnect Handling", tester.test_disconnect_handling)
    
    # Print results
    print(f"\n📊 Backend Tests: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All backend tests passed!")
        return 0
    else:
        print("⚠️ Some backend tests failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)