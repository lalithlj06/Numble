from typing import List, Dict, Optional
from fastapi import WebSocket
from models import Room, Player, GameState, GuessResult
from game_logic import validate_guess, validate_secret
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self, db):
        # Room ID -> Room object
        self.rooms: Dict[str, Room] = {}
        # Client ID -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        self.db = db

    async def get_room(self, room_id: str) -> Optional[Room]:
        if room_id in self.rooms:
            return self.rooms[room_id]
        
        # Try to fetch from DB
        try:
            doc = await self.db.rooms.find_one({"id": room_id})
            if doc:
                if "_id" in doc: del doc["_id"]
                room = Room(**doc)
                self.rooms[room_id] = room
                return room
        except Exception as e:
            logger.error(f"Error fetching room {room_id} from DB: {e}")
        return None

    async def save_room(self, room: Room):
        try:
            await self.db.rooms.replace_one({"id": room.id}, room.model_dump(), upsert=True)
        except Exception as e:
            logger.error(f"Error saving room {room.id} to DB: {e}")

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total active connections: {len(self.active_connections)}")

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Check if player was in a room and handle disconnect
        for room_id, room in self.rooms.items():
            # If room state is not fully loaded/synced with DB, we might miss this check
            # But disconnecting only matters for ACTIVE rooms in memory.
            # If room is not in memory (after restart), no one is connected to it anyway.
            # So iterating self.rooms is correct.
            
            player_in_room = False
            opponent = None
            player_name = "Unknown"
            
            if room.player1 and room.player1.id == client_id:
                room.player1.connected = False
                player_in_room = True
                player_name = room.player1.name or "Player 1"
                opponent = room.player2
            elif room.player2 and room.player2.id == client_id:
                room.player2.connected = False
                player_in_room = True
                player_name = room.player2.name or "Player 2"
                opponent = room.player1
                
            if player_in_room and room.game_state.status == "playing":
                # Opponent wins automatically
                if opponent and opponent.connected:
                    room.game_state.status = "finished"
                    room.game_state.winner_id = opponent.id
                    await self.broadcast_to_room(room_id, {
                        "type": "game_over",
                        "winner_id": opponent.id,
                        "reason": "opponent_disconnected",
                        "message": f"{player_name} disconnected. You win!",
                        "p1_secret": room.player1.secret_number,
                        "p2_secret": room.player2.secret_number
                    })
            elif player_in_room:
                 # Just notify disconnection if not playing
                 await self.broadcast_to_room(room_id, {
                     "type": "player_disconnected",
                     "player_id": client_id
                 })

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_room(self, room_id: str, message: dict):
        room = await self.get_room(room_id)
        if not room:
            logger.warning(f"Room {room_id} not found for broadcast")
            return
        
        if room.player1 and room.player1.id in self.active_connections:
            await self.active_connections[room.player1.id].send_json(message)
            logger.info(f"Sent message to player1 {room.player1.id}: {message}")
        else:
            logger.warning(f"Player1 {room.player1.id if room.player1 else 'None'} not in active connections")
        
        if room.player2 and room.player2.id in self.active_connections:
            await self.active_connections[room.player2.id].send_json(message)
            logger.info(f"Sent message to player2 {room.player2.id}: {message}")
        else:
            logger.warning(f"Player2 {room.player2.id if room.player2 else 'None'} not in active connections")

    async def create_room(self, client_id: str) -> str:
        room_id = str(uuid.uuid4())[:6].upper()
        room = Room(
            id=room_id,
            player1=Player(id=client_id, is_host=True),
            game_state=GameState(status="waiting")
        )
        self.rooms[room_id] = room
        await self.save_room(room)
        return room_id

    async def join_room(self, client_id: str, room_id: str) -> bool:
        room = await self.get_room(room_id)
        if not room:
            return False
        
        if room.player2 is not None:
            return False # Room full
        
        # Prevent joining same room twice
        if room.player1.id == client_id:
            return True

        room.player2 = Player(id=client_id, is_host=False)
        room.game_state.status = "setup"
        await self.save_room(room)
        
        logger.info(f"Player {client_id} joined room {room_id}. Active connections: {list(self.active_connections.keys())}")
        
        # Small delay to ensure WebSocket connection is fully established
        await asyncio.sleep(0.1)
        
        await self.broadcast_to_room(room_id, {
            "type": "player_joined",
            "room_id": room_id,
            "game_state": room.game_state.model_dump(),
            "players": {
                "player1": {"id": room.player1.id, "name": room.player1.name, "is_ready": room.player1.is_ready},
                "player2": {"id": room.player2.id, "name": room.player2.name, "is_ready": room.player2.is_ready} if room.player2 else None
            }
        })
        return True

    async def set_player_setup(self, client_id: str, room_id: str, name: str, secret: str):
        room = await self.get_room(room_id)
        if not room:
            return
        
        if not validate_secret(secret):
             await self.send_personal_message({"type": "error", "message": "Invalid secret number"}, self.active_connections[client_id])
             return
             
        if not name or len(name.strip()) == 0:
             await self.send_personal_message({"type": "error", "message": "Name is required"}, self.active_connections[client_id])
             return

        if room.player1.id == client_id:
            room.player1.name = name
            room.player1.secret_number = secret
            room.player1.is_ready = True
        elif room.player2 and room.player2.id == client_id:
            room.player2.name = name
            room.player2.secret_number = secret
            room.player2.is_ready = True
            
        await self.broadcast_to_room(room_id, {
            "type": "player_ready",
            "player_id": client_id,
            "name": name,
            "game_state": room.game_state.model_dump(),
            "players": {
                "player1": {"id": room.player1.id, "name": room.player1.name, "is_ready": room.player1.is_ready},
                "player2": {"id": room.player2.id, "name": room.player2.name, "is_ready": room.player2.is_ready} if room.player2 else None
            }
        })
        await self.save_room(room)

    async def start_game(self, client_id: str, room_id: str):
        room = await self.get_room(room_id)
        if not room:
            return
        
        if room.player1.id != client_id:
            return # Only host can start
            
        if not (room.player1.is_ready and room.player2 and room.player2.is_ready):
            return # Not everyone ready

        room.game_state.status = "playing"
        room.game_state.start_time = datetime.now(timezone.utc).isoformat()
        
        await self.broadcast_to_room(room_id, {
            "type": "game_started",
            "game_state": room.game_state.model_dump(),
            "players": {
                "player1": {"id": room.player1.id, "name": room.player1.name},
                "player2": {"id": room.player2.id, "name": room.player2.name}
            }
        })
        await self.save_room(room)

    async def submit_guess(self, client_id: str, room_id: str, guess: str):
        room = await self.get_room(room_id)
        if not room:
            return
        
        if room.game_state.status != "playing":
            return

        player = room.player1 if room.player1.id == client_id else room.player2
        opponent = room.player2 if room.player1.id == client_id else room.player1
        
        if not player or not opponent:
            return

        if len(player.guesses) >= 6:
            return 

        # Validate guess
        if not validate_secret(guess): # Reuse secret validation
             await self.send_personal_message({"type": "error", "message": "Invalid guess"}, self.active_connections[client_id])
             return

        # Calculate result
        feedback = validate_guess(guess, opponent.secret_number)
        
        # Add guess to player's history
        guess_result = GuessResult(guess=guess, feedback=feedback)
        player.guesses.append(guess_result)
        
        # Check win condition
        if guess == opponent.secret_number:
            player.has_won = True
            room.game_state.winner_id = client_id
            room.game_state.status = "finished"
            
            await self.broadcast_to_room(room_id, {
                "type": "guess_made",
                "player_id": client_id,
                "guess": guess,
                "feedback": feedback,
                "attempt": len(player.guesses)
            })

            await self.broadcast_to_room(room_id, {
                 "type": "game_over",
                 "winner_id": client_id,
                 "winner_name": player.name,
                 "p1_secret": room.player1.secret_number,
                 "p2_secret": room.player2.secret_number
             })
            await self.save_room(room)
             
        elif len(player.guesses) >= 6 and len(opponent.guesses) >= 6 and not opponent.has_won:
             # Both exhausted guesses -> Draw (or loss for both?)
             # "If both players guess correctly on the same attempt number -> Draw" - covered if simultaneous
             # But if they run out of guesses, it's a draw? 
             # Let's say Draw.
             
             room.game_state.status = "finished"
             await self.broadcast_to_room(room_id, {
                "type": "guess_made",
                "player_id": client_id,
                "guess": guess,
                "feedback": feedback,
                "attempt": len(player.guesses)
             })

             await self.broadcast_to_room(room_id, {
                 "type": "game_over",
                 "winner_id": None, # Draw
                 "p1_secret": room.player1.secret_number,
                 "p2_secret": room.player2.secret_number
             })
             await self.save_room(room)
        else:
            # Just a guess
            await self.broadcast_to_room(room_id, {
                "type": "guess_made",
                "player_id": client_id,
                "guess": guess,
                "feedback": feedback,
                "attempt": len(player.guesses)
            })
            await self.save_room(room)

    async def rematch(self, room_id: str):
        room = await self.get_room(room_id)
        if not room:
            return
        
        # Reset state
        room.player1.secret_number = None
        room.player1.guesses = []
        room.player1.is_ready = False
        room.player1.has_won = False
        
        room.player2.secret_number = None
        room.player2.guesses = []
        room.player2.is_ready = False
        room.player2.has_won = False
        
        room.game_state.status = "setup"
        room.game_state.winner_id = None
        room.game_state.start_time = None
        
        await self.broadcast_to_room(room_id, {
            "type": "rematch_started",
            "game_state": room.game_state.model_dump()
        })
        await self.save_room(room)
