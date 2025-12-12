import React, { useState, useEffect } from 'react';
import { useGame } from '@/context/GameContext';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Copy, CheckCircle, Play, RefreshCw, LogOut } from 'lucide-react';
import Board from '@/components/Board';
import RulesModal from '@/components/RulesModal';
import { motion, AnimatePresence } from 'framer-motion';

export default function GameRoom() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const { 
    gameState, 
    setSecret, 
    startGame, 
    submitGuess, 
    rematch, 
    clientId, 
    messages 
  } = useGame();

  const [secretInput, setSecretInput] = useState("");
  const [guessInput, setGuessInput] = useState("");
  const [myGuesses, setMyGuesses] = useState([]);
  const [oppGuesses, setOppGuesses] = useState([]);
  const [isRulesOpen, setIsRulesOpen] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [gameResult, setGameResult] = useState(null);

  // Listen for game events to update local board state
  useEffect(() => {
    if (messages.length > 0) {
        const lastMsg = messages[messages.length - 1];
        if (lastMsg.type === 'guess_made') {
            if (lastMsg.player_id === clientId) {
                setMyGuesses(prev => [...prev, { guess: lastMsg.guess, feedback: lastMsg.feedback }]);
            } else {
                setOppGuesses(prev => [...prev, { guess: lastMsg.guess, feedback: lastMsg.feedback }]);
            }
        } else if (lastMsg.type === 'rematch_started') {
            setMyGuesses([]);
            setOppGuesses([]);
            setIsReady(false);
            setSecretInput("");
            setGameResult(null);
        } else if (lastMsg.type === 'game_over') {
             // Determine result
             if (lastMsg.winner_id === clientId) setGameResult("VICTORY");
             else if (lastMsg.winner_id === null) setGameResult("DRAW");
             else setGameResult("DEFEAT");
        }
    }
  }, [messages, clientId]);

  const copyRoomCode = () => {
    navigator.clipboard.writeText(roomId);
    toast.success("Room code copied!");
  };

  const handleSetSecret = () => {
      if (secretInput.length !== 4 || new Set(secretInput).size !== 4) {
          toast.error("Must be 4 unique digits");
          return;
      }
      setSecret(secretInput);
      setIsReady(true);
  };

  const handleSubmitGuess = (e) => {
      e.preventDefault();
      if (guessInput.length !== 4) return;
      submitGuess(guessInput);
      setGuessInput("");
  };
  
  const handleExit = () => {
      navigate('/');
      window.location.reload(); // Quick way to disconnect/reset
  }

  if (!gameState) return <div className="flex h-screen items-center justify-center text-primary animate-pulse">CONNECTING...</div>;

  return (
    <div className="min-h-screen p-4 flex flex-col md:flex-row gap-4 bg-background relative overflow-hidden">
        {/* Confetti / Overlay could go here */}
        
        {/* Header / HUD */}
        <div className="md:fixed top-0 left-0 w-full p-4 flex justify-between items-center z-50 glass-panel md:bg-black/20 border-b border-white/5">
            <div className="flex items-center gap-4">
                <h2 className="font-heading text-xl md:text-2xl text-primary neon-text">ROOM: {roomId}</h2>
                <Button size="icon" variant="ghost" onClick={copyRoomCode}><Copy className="w-4 h-4" /></Button>
            </div>
            <div className="flex gap-2">
                 <Button variant="ghost" size="sm" onClick={() => setIsRulesOpen(true)}>RULES</Button>
                 <Button variant="destructive" size="sm" onClick={handleExit}><LogOut className="w-4 h-4" /></Button>
            </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col md:flex-row gap-8 items-start justify-center pt-20">
            
            {/* WAITING PHASE - Waiting for second player to join */}
            {gameState.status === 'waiting' && (
                <div className="absolute inset-0 flex items-center justify-center z-40 bg-black/80 backdrop-blur-sm">
                    <div className="text-center space-y-4">
                        <h2 className="text-4xl font-heading text-primary animate-pulse">WAITING FOR OPPONENT...</h2>
                        <p className="text-muted-foreground">Share your room code with a friend to start playing!</p>
                        <div className="glass-panel p-4 rounded-xl">
                            <p className="text-sm text-muted-foreground mb-2">Room Code:</p>
                            <p className="text-3xl font-bold tracking-widest text-primary">{roomId}</p>
                        </div>
                    </div>
                </div>
            )}
            
            {/* SETUP PHASE */}
            {gameState.status === 'setup' && !isReady && (
                <div className="absolute inset-0 flex items-center justify-center z-40 bg-black/80 backdrop-blur-sm">
                    <motion.div 
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="glass-panel p-8 rounded-2xl max-w-md w-full text-center space-y-6"
                    >
                        <h2 className="text-3xl font-heading text-white">SET SECRET NUMBER</h2>
                        <p className="text-muted-foreground">Choose 4 unique digits. Your opponent will try to guess this.</p>
                        <Input 
                            autoFocus
                            value={secretInput}
                            onChange={(e) => {
                                const val = e.target.value.replace(/[^0-9]/g, '').slice(0, 4);
                                setSecretInput(val);
                            }}
                            className="text-6xl tracking-[0.5em] h-24"
                            placeholder="0000"
                        />
                        <Button onClick={handleSetSecret} className="w-full text-lg h-12">LOCK IN</Button>
                    </motion.div>
                </div>
            )}
            
            {gameState.status === 'setup' && isReady && (
                 <div className="absolute inset-0 flex items-center justify-center z-40 bg-black/80 backdrop-blur-sm">
                    <div className="text-center space-y-4">
                        <h2 className="text-4xl font-heading text-primary animate-pulse">WAITING FOR OPPONENT...</h2>
                        {gameState.player1_ready && gameState.player2_ready && (
                             // Both ready, show start button if host
                             <Button onClick={startGame} size="lg" className="animate-bounce">LET'S BEGIN</Button>
                        )}
                        {/* Note: In our simple state we might not have 'player1_ready' flags exposed in global 'gameState' directly depending on backend model. 
                            Using notifications for now. If host, just try clicking Start. 
                        */}
                         <Button onClick={startGame} size="lg" variant="secondary">START GAME (HOST ONLY)</Button>
                    </div>
                 </div>
            )}

             {/* GAME OVER PHASE */}
             {gameState.status === 'finished' && gameResult && (
                 <div className="absolute inset-0 flex flex-col items-center justify-center z-50 bg-black/90 backdrop-blur-md">
                     <motion.h1 
                        initial={{ scale: 0.5, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className={`text-8xl font-black font-heading mb-8 ${gameResult === 'VICTORY' ? 'text-primary neon-text' : gameResult === 'DEFEAT' ? 'text-destructive' : 'text-accent'}`}
                     >
                         {gameResult}
                     </motion.h1>
                     
                     <div className="flex gap-4">
                         <Button onClick={rematch} size="lg" className="h-16 text-xl px-8">
                            <RefreshCw className="mr-2" /> PLAY AGAIN
                         </Button>
                         <Button onClick={handleExit} variant="outline" size="lg" className="h-16 text-xl px-8">
                            EXIT
                         </Button>
                     </div>
                 </div>
             )}


            {/* MY BOARD (LEFT) */}
            <div className="w-full md:w-1/2 max-w-md flex flex-col gap-4">
                <div className="glass-panel p-4 rounded-xl border-l-4 border-primary">
                    <h3 className="font-heading text-xl text-primary mb-2">YOU</h3>
                    <Board guesses={myGuesses} isMe={true} />
                    
                    {/* INPUT AREA */}
                    {gameState.status === 'playing' && (
                        <form onSubmit={handleSubmitGuess} className="mt-6 flex gap-2">
                             <Input 
                                value={guessInput}
                                onChange={(e) => {
                                    const val = e.target.value.replace(/[^0-9]/g, '').slice(0, 4);
                                    setGuessInput(val);
                                }}
                                placeholder="GUESS"
                                className="text-2xl tracking-widest font-bold"
                                autoFocus
                             />
                             <Button type="submit" disabled={guessInput.length !== 4}>SUBMIT</Button>
                        </form>
                    )}
                </div>
            </div>

            {/* OPPONENT BOARD (RIGHT) */}
            <div className="w-full md:w-1/2 max-w-md flex flex-col gap-4 opacity-90">
                <div className="glass-panel p-4 rounded-xl border-r-4 border-secondary">
                    <h3 className="font-heading text-xl text-secondary mb-2 text-right">OPPONENT</h3>
                    <Board guesses={oppGuesses} isMe={false} />
                </div>
            </div>

        </div>
        
        <RulesModal open={isRulesOpen} onOpenChange={setIsRulesOpen} />
    </div>
  );
}
