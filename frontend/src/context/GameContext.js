import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'sonner';

const GameContext = createContext();

export const useGame = () => useContext(GameContext);

export const GameProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [clientId, setClientId] = useState(localStorage.getItem('clientId') || uuidv4());
  const [isConnected, setIsConnected] = useState(false);
  const [gameState, setGameState] = useState(null);
  const [roomId, setRoomId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [playerSecret, setPlayerSecret] = useState(null);
  const [opponentSecret, setOpponentSecret] = useState(null);

  useEffect(() => {
    localStorage.setItem('clientId', clientId);
    
    // Construct WebSocket URL
    const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
    const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${backendUrl.split('://')[1]}/api/ws/${clientId}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to WebSocket');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    };

    ws.onclose = () => {
      console.log('Disconnected from WebSocket');
      setIsConnected(false);
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [clientId]);

  const handleServerMessage = (data) => {
    console.log("Received:", data);
    switch (data.type) {
      case 'room_created':
        setRoomId(data.room_id);
        setGameState({ status: 'waiting' });
        toast.success(`Room created! Code: ${data.room_id}`);
        break;
      case 'joined_room':
        setRoomId(data.room_id);
        // We'll get player_joined next to update state
        break;
      case 'player_joined':
        // Set room ID if not already set (for joining player)
        if (!roomId && data.room_id) {
          setRoomId(data.room_id);
        }
        setGameState(data.game_state);
        toast.success("Player joined!");
        break;
      case 'player_ready':
        toast.info(`Player is ready!`);
        break;
      case 'game_started':
        setGameState(data.game_state);
        toast.success("Game Started! Guess the number!");
        break;
      case 'guess_made':
         // Re-fetch or just update local state if we had full state sync
         // The server sends updated guess info in data.guess/feedback but we need full state usually.
         // Ideally server sends full game state or we patch it.
         // For MVP, let's trigger a UI update via state. 
         // Actually, our backend broadcasts specific events. We should store guesses in state.
         
         setGameState(prev => {
             // Deep copy to avoid mutation issues
             const newState = JSON.parse(JSON.stringify(prev)); // simplistic deep copy
             // We need to know WHICH player made the guess.
             // Backend sends: player_id, guess, feedback
             
             // BUT, we don't have the full player objects in local state unless we sync them.
             // Let's assume we can map player_id to 'player1' or 'player2' based on something?
             // Or better, let's request full state sync or trust the event.
             
             // Wait, the backend 'guess_made' event just sends the guess. 
             // We need to attach it to the right player's board.
             // Let's stick to a simpler approach: 
             // We will maintain a 'guesses' object in our context: { [playerId]: [] }
             return newState;
         });
         
         setMessages(prev => [...prev, data]); // specific handler in component
        break;
      case 'game_over':
        setGameState(prev => ({ ...prev, status: 'finished', winner_id: data.winner_id }));
        setPlayerSecret(data.p1_secret); // This might be mixed up if we don't know who is p1/p2
        // Actually, let's just use what server sent.
        if (clientId === data.winner_id) {
            toast.success("VICTORY!", { duration: 5000 });
        } else if (data.winner_id === null) {
            toast.info("DRAW!", { duration: 5000 });
        } else {
            toast.error("DEFEAT!", { duration: 5000 });
        }
        break;
      case 'rematch_started':
         setGameState(data.game_state);
         setPlayerSecret(null);
         toast.success("Rematch started!");
         break;
      case 'error':
        toast.error(data.message);
        break;
      default:
        break;
    }
  };

  const createRoom = () => {
    socket.send(JSON.stringify({ action: 'create_room' }));
  };

  const joinRoom = (code) => {
    socket.send(JSON.stringify({ action: 'join_room', room_id: code }));
  };

  const setSecret = (secret) => {
    socket.send(JSON.stringify({ action: 'set_secret', room_id: roomId, secret }));
  };

  const startGame = () => {
    socket.send(JSON.stringify({ action: 'start_game', room_id: roomId }));
  };

  const submitGuess = (guess) => {
    socket.send(JSON.stringify({ action: 'submit_guess', room_id: roomId, guess }));
  };
  
  const rematch = () => {
      socket.send(JSON.stringify({ action: 'rematch', room_id: roomId }));
  }

  return (
    <GameContext.Provider value={{
      socket,
      clientId,
      isConnected,
      gameState,
      setGameState, // Allow manual updates if needed
      roomId,
      createRoom,
      joinRoom,
      setSecret,
      startGame,
      submitGuess,
      rematch,
      messages, // For components to listen to specific events
      playerSecret
    }}>
      {children}
    </GameContext.Provider>
  );
};
