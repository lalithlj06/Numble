from pydantic import BaseModel
from typing import List, Optional, Literal

class GuessResult(BaseModel):
    guess: str
    feedback: List[str] # "green", "yellow", "grey"

class Player(BaseModel):
    id: str
    name: Optional[str] = None
    is_host: bool = False
    connected: bool = True
    is_ready: bool = False
    secret_number: Optional[str] = None
    guesses: List[GuessResult] = []
    has_won: bool = False

class GameState(BaseModel):
    status: Literal["waiting", "setup", "playing", "finished"] = "waiting"
    winner_id: Optional[str] = None
    start_time: Optional[str] = None
    current_turn: Optional[str] = None # Not really used in free-for-all but kept for compat

class Room(BaseModel):
    id: str
    player1: Player
    player2: Optional[Player] = None
    game_state: GameState
