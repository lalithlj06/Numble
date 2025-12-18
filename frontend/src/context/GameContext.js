import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'sonner';
import axios from 'axios';

const GameContext = createContext();

export const useGame = () => useContext(GameContext);

export const GameProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  // Use sessionStorage to persist ID across refreshes but keep unique per tab
  const [clientId] = useState(() => {
    const stored = sessionStorage.getItem('clientId');
    if (stored) return stored;
    const newId = uuidv4();
    sessionStorage.setItem('clientId', newId);
    return newId;
  });
  const [isConnected, setIsConnected] = useState(false);
  const [gameState, setGameState] = useState(null);
  const [roomId, setRoomId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [playerSecret, setPlayerSecret] = useState(null);
  const [players, setPlayers] = useState({});
  const [isHost, setIsHost] = useState(false);

  // Polling ref
  const pollInterval = useRef(null);

  useEffect(() => {
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

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Suppress toast on error to avoid initial connection jitter warnings
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [clientId]);

  // Fetch Room State via REST
  const fetchRoomState = useCallback(async (currentRoomId) => {
      if (!currentRoomId) return;
      try {
          const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
          const response = await axios.get(`${backendUrl}/api/rooms/${currentRoomId}`);
          const room = response.data;
          
          if (room) {
              // Update Game State
              setGameState(room.game_state);
              
              // Update Players
              const newPlayers = {
                  player1: room.player1,
                  player2: room.player2
              };
              setPlayers(newPlayers);
              
              // Determine if host
              if (room.player1.id === clientId) setIsHost(true);
              
              // If waiting and player2 is now present, we are setup!
              if (room.player2 && room.game_state.status === 'waiting') {
                   // Force update to setup if backend hasn't yet (race condition) or if we missed the event
                   // Actually backend should have updated status to 'setup' when p2 joined.
                   // If backend status is 'setup', setGameState handles it.
              }
          }
      } catch (error) {
          console.error("Error fetching room state:", error);
      }
  }, [clientId]);

  // Polling Logic
  useEffect(() => {
      if (roomId) {
          // Poll every 2 seconds if in critical states or just generally to keep sync
          pollInterval.current = setInterval(() => {
              fetchRoomState(roomId);
          }, 2000);
      }
      
      return () => {
          if (pollInterval.current) clearInterval(pollInterval.current);
      };
  }, [roomId, fetchRoomState]);


  const handleServerMessage = (data) => {
    console.log("Received:", data);
    setMessages(prev => [...prev, data]);
    
    switch (data.type) {
      case 'room_created':
        setRoomId(data.room_id);
        setGameState({ status: 'waiting' });
        setIsHost(true); // User who creates room is the host
        toast.success(`Room created! Code: ${data.room_id}`);
        // Immediate fetch to sync
        fetchRoomState(data.room_id);
        break;
      case 'joined_room':
        setRoomId(data.room_id);
        fetchRoomState(data.room_id);
        break;
      case 'player_joined':
        if (!roomId && data.room_id) {
            setRoomId(data.room_id);
        }
        setGameState(data.game_state);
        if (data.players) setPlayers(data.players);
        toast.success("Player joined!");
        break;
      case 'player_ready':
        setGameState(data.game_state);
        if (data.players) setPlayers(data.players);
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
        fetchRoomState(roomId); // Sync final state
        break;
      case 'rematch_started':
         setGameState(data.game_state);
         setPlayerSecret(null);
         toast.success("Rematch started!");
         fetchRoomState(roomId);
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
    if (!code) return;
    socket.send(JSON.stringify({ action: 'join_room', room_id: code.trim() }));
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
      players,
      isHost
    }}>
      {children}
    </GameContext.Provider>
  );
};
