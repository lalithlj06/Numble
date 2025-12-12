#!/usr/bin/env python3
"""
Focused test for NUMBLE Multiplayer Setup Phase
Tests the specific flow that was failing in the previous iteration.
"""

import asyncio
import websockets
import json
import uuid
import sys

class MultiplayerSetupTester:
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

    async def listen_for_messages(self, websocket, client_name, duration=10):
        """Listen for messages from websocket for a given duration"""
        messages = []
        try:
            end_time = asyncio.get_event_loop().time() + duration
            while asyncio.get_event_loop().time() < end_time:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1)
                    data = json.loads(message)
                    messages.append(data)
                    print(f"📨 {client_name} received: {data}")
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            print(f"❌ Error listening for {client_name}: {e}")
        return messages

    async def test_multiplayer_setup_flow(self):
        """Test the complete multiplayer setup flow"""
        print("🚀 Testing NUMBLE Multiplayer Setup Phase")
        print(f"Client A ID: {self.client_a_id}")
        print(f"Client B ID: {self.client_b_id}")
        
        try:
            # Step 1: Connect both clients
            print("\n📡 Step 1: Connecting clients...")
            client_a = await self.connect_client(self.client_a_id)
            client_b = await self.connect_client(self.client_b_id)
            
            if not client_a or not client_b:
                print("❌ Failed to connect clients")
                return False
            
            # Step 2: Client A creates room
            print("\n🏠 Step 2: Client A creates room...")
            await client_a.send(json.dumps({"action": "create_room"}))
            
            # Listen for room creation response
            messages_a = await self.listen_for_messages(client_a, "Client A", 3)
            room_created = next((msg for msg in messages_a if msg.get('type') == 'room_created'), None)
            
            if not room_created:
                print("❌ Room creation failed")
                return False
            
            self.room_id = room_created['room_id']
            print(f"✅ Room created: {self.room_id}")
            
            # Step 3: Client B joins room
            print(f"\n👥 Step 3: Client B joins room {self.room_id}...")
            await client_b.send(json.dumps({"action": "join_room", "room_id": self.room_id}))
            
            # Listen for join responses on both clients
            print("🔄 Listening for player_joined events...")
            
            # Use asyncio.gather to listen to both clients simultaneously
            task_a = asyncio.create_task(self.listen_for_messages(client_a, "Client A", 5))
            task_b = asyncio.create_task(self.listen_for_messages(client_b, "Client B", 5))
            
            messages_a, messages_b = await asyncio.gather(task_a, task_b)
            
            # Check if player_joined event was received
            player_joined_a = next((msg for msg in messages_a if msg.get('type') == 'player_joined'), None)
            player_joined_b = next((msg for msg in messages_b if msg.get('type') == 'player_joined'), None)
            joined_room_b = next((msg for msg in messages_b if msg.get('type') == 'joined_room'), None)
            
            print(f"\n📊 Results:")
            print(f"Client A received player_joined: {player_joined_a is not None}")
            print(f"Client B received player_joined: {player_joined_b is not None}")
            print(f"Client B received joined_room: {joined_room_b is not None}")
            
            if player_joined_a and player_joined_a.get('game_state', {}).get('status') == 'setup':
                print("✅ Game state correctly transitioned to 'setup'")
                setup_success = True
            else:
                print("❌ Game state did not transition to 'setup'")
                setup_success = False
            
            # Step 4: Both players set secret numbers
            print(f"\n🔐 Step 4: Setting secret numbers...")
            await client_a.send(json.dumps({"action": "set_secret", "room_id": self.room_id, "secret": "1234"}))
            await client_b.send(json.dumps({"action": "set_secret", "room_id": self.room_id, "secret": "5678"}))
            
            # Listen for ready events
            task_a = asyncio.create_task(self.listen_for_messages(client_a, "Client A", 3))
            task_b = asyncio.create_task(self.listen_for_messages(client_b, "Client B", 3))
            
            messages_a, messages_b = await asyncio.gather(task_a, task_b)
            
            ready_events_a = [msg for msg in messages_a if msg.get('type') == 'player_ready']
            ready_events_b = [msg for msg in messages_b if msg.get('type') == 'player_ready']
            
            print(f"Client A received {len(ready_events_a)} player_ready events")
            print(f"Client B received {len(ready_events_b)} player_ready events")
            
            # Step 5: Host starts the game
            print(f"\n🎮 Step 5: Host (Client A) starts the game...")
            await client_a.send(json.dumps({"action": "start_game", "room_id": self.room_id}))
            
            # Listen for game start events
            task_a = asyncio.create_task(self.listen_for_messages(client_a, "Client A", 3))
            task_b = asyncio.create_task(self.listen_for_messages(client_b, "Client B", 3))
            
            messages_a, messages_b = await asyncio.gather(task_a, task_b)
            
            game_started_a = next((msg for msg in messages_a if msg.get('type') == 'game_started'), None)
            game_started_b = next((msg for msg in messages_b if msg.get('type') == 'game_started'), None)
            
            print(f"Client A received game_started: {game_started_a is not None}")
            print(f"Client B received game_started: {game_started_b is not None}")
            
            if game_started_a and game_started_b:
                print("✅ Game started successfully")
                game_start_success = True
            else:
                print("❌ Game start failed")
                game_start_success = False
            
            # Step 6: Test a guess
            print(f"\n🎯 Step 6: Client A makes a guess...")
            await client_a.send(json.dumps({"action": "submit_guess", "room_id": self.room_id, "guess": "9876"}))
            
            # Listen for guess events
            task_a = asyncio.create_task(self.listen_for_messages(client_a, "Client A", 3))
            task_b = asyncio.create_task(self.listen_for_messages(client_b, "Client B", 3))
            
            messages_a, messages_b = await asyncio.gather(task_a, task_b)
            
            guess_made_a = next((msg for msg in messages_a if msg.get('type') == 'guess_made'), None)
            guess_made_b = next((msg for msg in messages_b if msg.get('type') == 'guess_made'), None)
            
            print(f"Client A received guess_made: {guess_made_a is not None}")
            print(f"Client B received guess_made: {guess_made_b is not None}")
            
            # Close connections
            await client_a.close()
            await client_b.close()
            
            # Summary
            print(f"\n📋 SUMMARY:")
            print(f"✅ Room Creation: Success")
            print(f"✅ Room Joining: Success")
            print(f"{'✅' if setup_success else '❌'} Setup Phase Transition: {'Success' if setup_success else 'Failed'}")
            print(f"{'✅' if len(ready_events_a) >= 2 else '❌'} Secret Setting: {'Success' if len(ready_events_a) >= 2 else 'Failed'}")
            print(f"{'✅' if game_start_success else '❌'} Game Start: {'Success' if game_start_success else 'Failed'}")
            print(f"{'✅' if guess_made_a and guess_made_b else '❌'} Guessing: {'Success' if guess_made_a and guess_made_b else 'Failed'}")
            
            return setup_success and game_start_success and (guess_made_a and guess_made_b)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False

async def main():
    """Main test function"""
    tester = MultiplayerSetupTester()
    
    try:
        success = await tester.test_multiplayer_setup_flow()
        
        if success:
            print("\n🎉 All multiplayer setup tests passed!")
            return 0
        else:
            print("\n⚠️ Some multiplayer setup tests failed")
            return 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)