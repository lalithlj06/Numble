from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List
import uuid
from connection_manager import ConnectionManager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

manager = ConnectionManager()

# --- WebSocket ---
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "create_room":
                room_id = await manager.create_room(client_id)
                await manager.send_personal_message({"type": "room_created", "room_id": room_id}, websocket)
                
            elif action == "join_room":
                room_id = data.get("room_id")
                success = await manager.join_room(client_id, room_id)
                if success:
                    await manager.send_personal_message({"type": "joined_room", "room_id": room_id}, websocket)
                else:
                    await manager.send_personal_message({"type": "error", "message": "Room full or invalid"}, websocket)

            elif action == "set_secret":
                room_id = data.get("room_id")
                secret = data.get("secret")
                await manager.set_secret(client_id, room_id, secret)

            elif action == "start_game":
                room_id = data.get("room_id")
                await manager.start_game(client_id, room_id)

            elif action == "submit_guess":
                room_id = data.get("room_id")
                guess = data.get("guess")
                await manager.submit_guess(client_id, room_id, guess)

            elif action == "rematch":
                room_id = data.get("room_id")
                await manager.rematch(room_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)


# --- API Routes ---
@api_router.get("/")
async def root():
    return {"message": "NUMBLE API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"], # In production, restrict this
    allow_methods=["*"],
    allow_headers=["*"],
)
