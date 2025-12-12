#!/usr/bin/env python3
"""
Complete NUMBLE Multiplayer Flow Test
Tests the entire flow from room creation to game completion.
"""

import asyncio
import websockets
import json
import uuid
import sys

class CompleteFlowTester:
    def __init__(self, backend_url="https://fastmath-2.preview.emergentagent.com"):
        self.backend_url = backend_url
        if backend_url.startswith('https'):
            self.ws_url = backend_url.replace('https://', 'wss://')
        else:
            self.ws_url = backend_url.replace('http://', 'ws://')
        
        self.client_a_id = str(uuid.uuid4())
        self.client_b_id = str(uuid.uuid4())
        self.room_id = None
        
    async def connect_client(self, client_id):
        """Connect a WebSocket client"""
        try:
            uri = f"{self.ws_url}/api/ws/{client_id}"
            websocket = await websockets.connect(uri)
            print(f"✅ Connected client {client_id[:8]}...")
            return websocket
        except Exception as e:
            print(f"❌ Failed to connect client {client_id}: {e}")
            return None

    async def test_complete_multiplayer_flow(self):
        """Test the complete multiplayer flow"""
        print("🚀 Testing Complete NUMBLE Multiplayer Flow")
        print(f"Client A ID: {self.client_a_id}")
        print(f"Client B ID: {self.client_b_id}")
        
        try:
            # Connect both clients
            print("\n📡 Connecting clients...")
            client_a = await self.connect_client(self.client_a_id)
            client_b = await self.connect_client(self.client_b_id)
            
            if not client_a or not client_b:
                return False
            
            # Step 1: Client A creates room
            print("\n🏠 Step 1: Creating room...")
            await client_a.send(json.dumps({"action": "create_room"}))
            
            response = await client_a.recv()
            data = json.loads(response)
            
            if data.get('type') == 'room_created':
                self.room_id = data['room_id']
                print(f"✅ Room created: {self.room_id}")
            else:
                print(f"❌ Room creation failed: {data}")
                return False
            
            # Step 2: Client B joins room
            print(f"\n👥 Step 2: Client B joining room {self.room_id}...")
            await client_b.send(json.dumps({"action": "join_room", "room_id": self.room_id}))
            
            # Listen for join responses
            messages_received = []
            
            # Collect messages for a few seconds
            end_time = asyncio.get_event_loop().time() + 5
            while asyncio.get_event_loop().time() < end_time:
                try:
                    # Check both clients for messages
                    try:
                        msg_a = await asyncio.wait_for(client_a.recv(), timeout=0.5)
                        data_a = json.loads(msg_a)
                        messages_received.append(("Client A", data_a))
                        print(f"📨 Client A: {data_a}")
                    except asyncio.TimeoutError:
                        pass
                    
                    try:
                        msg_b = await asyncio.wait_for(client_b.recv(), timeout=0.5)
                        data_b = json.loads(msg_b)
                        messages_received.append(("Client B", data_b))
                        print(f"📨 Client B: {data_b}")
                    except asyncio.TimeoutError:
                        pass
                        
                except Exception as e:
                    break
            
            # Check if join was successful
            player_joined_msgs = [msg for client, msg in messages_received if msg.get('type') == 'player_joined']
            joined_room_msgs = [msg for client, msg in messages_received if msg.get('type') == 'joined_room']
            
            if player_joined_msgs and any(msg.get('game_state', {}).get('status') == 'setup' for msg in player_joined_msgs):
                print("✅ Player joined successfully, game state is 'setup'")
            else:
                print("❌ Player join failed or game state not 'setup'")
                return False
            
            # Step 3: Both players set secrets
            print(f"\n🔐 Step 3: Setting secret numbers...")
            await client_a.send(json.dumps({"action": "set_secret", "room_id": self.room_id, "secret": "1234"}))
            await client_b.send(json.dumps({"action": "set_secret", "room_id": self.room_id, "secret": "5678"}))
            
            # Wait for ready messages
            await asyncio.sleep(2)
            
            # Collect ready messages
            ready_messages = []
            for _ in range(4):  # Expect up to 4 messages (2 per client)
                try:
                    msg_a = await asyncio.wait_for(client_a.recv(), timeout=1)
                    ready_messages.append(json.loads(msg_a))
                except asyncio.TimeoutError:
                    break
            
            for _ in range(4):
                try:
                    msg_b = await asyncio.wait_for(client_b.recv(), timeout=1)
                    ready_messages.append(json.loads(msg_b))
                except asyncio.TimeoutError:
                    break
            
            ready_count = len([msg for msg in ready_messages if msg.get('type') == 'player_ready'])
            print(f"✅ Received {ready_count} player_ready messages")
            
            # Step 4: Host starts game
            print(f"\n🎮 Step 4: Starting game...")
            await client_a.send(json.dumps({"action": "start_game", "room_id": self.room_id}))
            
            # Wait for game start
            game_started = False
            for _ in range(2):
                try:
                    msg_a = await asyncio.wait_for(client_a.recv(), timeout=2)
                    data_a = json.loads(msg_a)
                    if data_a.get('type') == 'game_started':
                        game_started = True
                        print(f"✅ Game started: {data_a}")
                        break
                except asyncio.TimeoutError:
                    pass
            
            if not game_started:
                print("❌ Game start failed")
                return False
            
            # Step 5: Test guessing
            print(f"\n🎯 Step 5: Testing guesses...")
            
            # Client A makes a guess
            await client_a.send(json.dumps({"action": "submit_guess", "room_id": self.room_id, "guess": "9876"}))
            
            # Wait for guess response
            guess_received = False
            for _ in range(2):
                try:
                    msg_a = await asyncio.wait_for(client_a.recv(), timeout=2)
                    data_a = json.loads(msg_a)
                    if data_a.get('type') == 'guess_made':
                        guess_received = True
                        print(f"✅ Guess processed: {data_a}")
                        break
                except asyncio.TimeoutError:
                    pass
            
            if not guess_received:
                print("❌ Guess processing failed")
                return False
            
            # Step 6: Test winning guess
            print(f"\n🏆 Step 6: Testing winning guess...")
            await client_a.send(json.dumps({"action": "submit_guess", "room_id": self.room_id, "guess": "5678"}))
            
            # Wait for game over
            game_over = False
            for _ in range(2):
                try:
                    msg_a = await asyncio.wait_for(client_a.recv(), timeout=2)
                    data_a = json.loads(msg_a)
                    if data_a.get('type') == 'game_over':
                        game_over = True
                        print(f"✅ Game over: {data_a}")
                        break
                except asyncio.TimeoutError:
                    pass
            
            if not game_over:
                print("❌ Game over not received")
                return False
            
            # Close connections
            await client_a.close()
            await client_b.close()
            
            print(f"\n🎉 Complete multiplayer flow test PASSED!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False

async def main():
    """Main test function"""
    tester = CompleteFlowTester()
    
    try:
        success = await tester.test_complete_multiplayer_flow()
        
        if success:
            print("\n🎉 All tests passed! Multiplayer flow is working correctly.")
            return 0
        else:
            print("\n⚠️ Some tests failed.")
            return 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)