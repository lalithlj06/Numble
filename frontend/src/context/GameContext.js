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
  const [players, setPlayers] = useState({});

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
    setMessages(prev => [...prev, data]);
    
    switch (data.type) {
      case 'room_created':
        setRoomId(data.room_id);
        setGameState({ status: 'waiting' });
        toast.success(`Room created! Code: ${data.room_id}`);
        break;
      case 'joined_room':
        setRoomId(data.room_id);
        break;
      case 'player_joined':
        if (!roomId && data.room_id) {
            setRoomId(data.room_id);
        }
        setGameState(data.game_state);
        toast.success("Player joined!");
        break;
      case 'player_ready':
        setGameState(data.game_state);
        toast.info(`Player ${data.name || ''} is ready!`);
        break;
      case 'game_started':
        setGameState(data.game_state);
        setPlayers(data.players);
        toast.success("LET'S BEGIN!", { duration: 3000 });
        break;
      case 'guess_made':
         // handled by component for state updates
        break;
      case 'game_over':
        setGameState(prev => ({ ...prev, status: 'finished', winner_id: data.winner_id }));
        if (data.reason === 'opponent_disconnected') {
             toast.error(data.message);
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

  const setSetup = (name, secret) => {
    socket.send(JSON.stringify({ action: 'set_setup', room_id: roomId, name, secret }));
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
      setGameState,
      roomId,
      createRoom,
      joinRoom,
      setSetup,
      startGame,
      submitGuess,
      rematch,
      messages,
      playerSecret,
      players
    }}>
      {children}
    </GameContext.Provider>
  );
};
