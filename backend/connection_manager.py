from typing import List, Dict, Optional
from fastapi import WebSocket
from models import Room, Player, GameState, GuessResult
from game_logic import validate_guess, validate_secret
import json
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Room ID -> Room object
        self.rooms: Dict[str, Room] = {}
        # Client ID -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Remove player from any room they are in
        # Note: In a real app, might want to handle reconnection logic
        for room_id, room in self.rooms.items():
            if room.player1 and room.player1.id == client_id:
                room.player1.connected = False
            if room.player2 and room.player2.id == client_id:
                room.player2.connected = False

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        
        if room.player1 and room.player1.id in self.active_connections:
            await self.active_connections[room.player1.id].send_json(message)
        
        if room.player2 and room.player2.id in self.active_connections:
            await self.active_connections[room.player2.id].send_json(message)

    async def create_room(self, client_id: str) -> str:
        room_id = str(uuid.uuid4())[:6].upper()
        self.rooms[room_id] = Room(
            id=room_id,
            player1=Player(id=client_id, is_host=True),
            game_state=GameState(status="waiting")
        )
        return room_id

    async def join_room(self, client_id: str, room_id: str) -> bool:
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        if room.player2 is not None:
            return False # Room full
        
        # Prevent joining same room twice
        if room.player1.id == client_id:
            return True

        room.player2 = Player(id=client_id, is_host=False)
        room.game_state.status = "setup"
        
        # Notify both players
        await self.broadcast_to_room(room_id, {
            "type": "player_joined",
            "room_id": room_id,
            "game_state": room.game_state.model_dump()
        })
        return True

    async def set_secret(self, client_id: str, room_id: str, secret: str):
        print(f"Setting secret for {client_id} in {room_id}: {secret}")
        if room_id not in self.rooms:
            return

        
        room = self.rooms[room_id]
        
        if not validate_secret(secret):
             await self.send_personal_message({"type": "error", "message": "Invalid secret number"}, self.active_connections[client_id])
             return

        if room.player1.id == client_id:
            room.player1.secret_number = secret
            room.player1.is_ready = True
        elif room.player2 and room.player2.id == client_id:
            room.player2.secret_number = secret
            room.player2.is_ready = True
            
        await self.broadcast_to_room(room_id, {
            "type": "player_ready",
            "player_id": client_id
        })

        # Check if both ready
        if room.player1.is_ready and room.player2 and room.player2.is_ready:
            # Wait for host to start, or auto start? PRD says "Host must press LET'S BEGIN"
            # So we just wait.
            pass

    async def start_game(self, client_id: str, room_id: str):
        if room_id not in self.rooms:
            return
        room = self.rooms[room_id]
        
        if room.player1.id != client_id:
            return # Only host can start
            
        if not (room.player1.is_ready and room.player2 and room.player2.is_ready):
            return # Not everyone ready

        room.game_state.status = "playing"
        room.game_state.current_turn = room.player1.id # Host starts? Or random? Let's say Host starts or simultaneous?
        # PRD doesn't specify turn-based or real-time race. 
        # "Compete to guess each other's number first" -> implies race (simultaneous turns).
        # "If both players guess correctly in the same attempt -> Draw"
        
        await self.broadcast_to_room(room_id, {
            "type": "game_started",
            "game_state": room.game_state.dict()
        })

    async def submit_guess(self, client_id: str, room_id: str, guess: str):
        if room_id not in self.rooms:
            return
        room = self.rooms[room_id]
        
        if room.game_state.status != "playing":
            return

        player = room.player1 if room.player1.id == client_id else room.player2
        opponent = room.player2 if room.player1.id == client_id else room.player1
        
        if not player or not opponent:
            return

        if len(player.guesses) >= 6:
            return 

        # Validate guess
        if not validate_secret(guess): # Reuse secret validation (4 unique digits)
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
            room.game_state.status = "finished" # Wait, need to check if opponent also wins on this "turn" (attempt index)
        
        # Notify room of the update
        # We send the guess to EVERYONE so they can see it on the board
        await self.broadcast_to_room(room_id, {
            "type": "guess_made",
            "player_id": client_id,
            "guess": guess,
            "feedback": feedback,
            "attempt": len(player.guesses)
        })

        # Check for game end
        if player.has_won:
             # Check if it's a draw (opponent also won on same attempt count)
             # Wait, this is real-time. "Same attempt" means if P1 guesses on attempt 4 and wins, 
             # and P2 is ALREADY on attempt 4 and wins right after? 
             # Or does "same attempt" imply turn-based? 
             # "First player to guess correctly -> Winner". 
             # "If both players guess correctly in the same attempt -> Draw" 
             # This implies a race. If I guess it on my 3rd try, and you are on your 2nd, I win. 
             # If we both submit 3rd try at EXACT same time... handled by server serialization.
             # However, usually "same attempt" means if I win on turn 3, you get to finish your turn 3.
             # For MVP, let's stick to "First to guess wins".
             
             # Reveal numbers
             await self.broadcast_to_room(room_id, {
                 "type": "game_over",
                 "winner_id": client_id,
                 "p1_secret": room.player1.secret_number,
                 "p2_secret": room.player2.secret_number
             })
             
        elif len(player.guesses) >= 6 and len(opponent.guesses) >= 6:
             if not player.has_won and not opponent.has_won:
                 room.game_state.status = "finished"
                 await self.broadcast_to_room(room_id, {
                     "type": "game_over",
                     "winner_id": None, # Draw/Loss
                     "p1_secret": room.player1.secret_number,
                     "p2_secret": room.player2.secret_number
                 })

    async def rematch(self, room_id: str):
        if room_id not in self.rooms:
            return
        room = self.rooms[room_id]
        
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
        
        await self.broadcast_to_room(room_id, {
            "type": "rematch_started",
            "game_state": room.game_state.dict()
        })
