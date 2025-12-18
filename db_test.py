import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from models import Room, Player, GameState
import uuid

async def test_db():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    room_id = "TEST01"
    print(f"Saving room {room_id}...")
    
    room = Room(
        id=room_id,
        player1=Player(id="p1", is_host=True),
        game_state=GameState(status="waiting")
    )
    
    try:
        await db.rooms.replace_one({"id": room.id}, room.model_dump(), upsert=True)
        print("Save successful.")
    except Exception as e:
        print(f"Save failed: {e}")
        
    print("Fetching room...")
    doc = await db.rooms.find_one({"id": room_id})
    if doc:
        print("Fetch successful:", doc['id'])
    else:
        print("Fetch failed: Room not found.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    ROOT_DIR = Path("/app/backend")
    load_dotenv(ROOT_DIR / '.env')
    
    # Need to add backend dir to sys.path to import models
    import sys
    sys.path.append("/app/backend")
    
    asyncio.run(test_db())
