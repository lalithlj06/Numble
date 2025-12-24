import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import sys
import json
# Add backend to path
sys.path.append("/app/backend")
from connection_manager import ConnectionManager
from models import Room, Player, GameState

async def test_backend():
    print("Testing Backend...")
    try:
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        mongo_url = os.environ['MONGO_URL']
        client = AsyncIOMotorClient(mongo_url)
        db = client[os.environ['DB_NAME']]
        
        manager = ConnectionManager(db)
        
        # Test Create Room
        client_id_1 = str(uuid.uuid4())
        room_id = await manager.create_room(client_id_1)
        print(f"Created Room: {room_id}")
        
        # Verify in DB
        room = await manager.get_room(room_id)
        if room and room.id == room_id:
            print("Room found in DB.")
        else:
            print("Room NOT found in DB.")
            return

        # Test Join Room
        client_id_2 = str(uuid.uuid4())
        result = await manager.join_room(client_id_2, room_id)
        print(f"Join Result: {result}")
        
        room = await manager.get_room(room_id)
        if room.player2 and room.player2.id == client_id_2:
            print("Player 2 joined successfully.")
        else:
            print("Player 2 join failed.")
            
        print("Backend Test Passed.")
        
    except Exception as e:
        print(f"Backend Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backend())