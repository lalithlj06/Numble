import React, { useState, useEffect } from 'react';
import { useGame } from '@/context/GameContext';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Copy, LogOut, RefreshCw } from 'lucide-react';
import Board from '@/components/Board';
import RulesModal from '@/components/RulesModal';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';

const Timer = ({ startTime }) => {
    const [elapsed, setElapsed] = useState(0);
    
    useEffect(() => {
        if (!startTime) return;
        const start = new Date(startTime).getTime();
        const interval = setInterval(() => {
            setElapsed(Math.floor((Date.now() - start) / 1000));
        }, 1000);
        return () => clearInterval(interval);
    }, [startTime]);

    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    
    return <div className="font-mono text-xl text-primary">{minutes}:{seconds}</div>;
};

export default function GameRoom() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const { 
    gameState, 
    setSetup, 
    startGame, 
    submitGuess, 
    rematch, 
    clientId, 
    messages,
    players,
    isHost
  } = useGame();

  const [nameInput, setNameInput] = useState("");
  const [secretInput, setSecretInput] = useState("");
  const [guessInput, setGuessInput] = useState("");
  const [myGuesses, setMyGuesses] = useState([]);
  const [oppGuesses, setOppGuesses] = useState([]);
  const [isRulesOpen, setIsRulesOpen] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [gameResult, setGameResult] = useState(null);
  const [revealedSecrets, setRevealedSecrets] = useState(null);
  const [winnerName, setWinnerName] = useState("");

  // Listen for game events
  useEffect(() => {
    if (messages.length > 0) {
        const lastMsg = messages[messages.length - 1];
        if (lastMsg.type === 'guess_made') {
            if (lastMsg.player_id === clientId) {
                // Check if already exists to prevent duplicate
                setMyGuesses(prev => {
                    if (prev.length >= lastMsg.attempt) return prev;
                    return [...prev, { guess: lastMsg.guess, feedback: lastMsg.feedback }];
                });
            } else {
                 setOppGuesses(prev => {
                    if (prev.length >= lastMsg.attempt) return prev;
                    return [...prev, { guess: lastMsg.guess, feedback: lastMsg.feedback }];
                });
            }
        } else if (lastMsg.type === 'rematch_started') {
            setMyGuesses([]);
            setOppGuesses([]);
            setIsReady(false);
            setSecretInput("");
            setGameResult(null);
            setRevealedSecrets(null);
            setWinnerName("");
        } else if (lastMsg.type === 'game_over') {
             setRevealedSecrets({ p1: lastMsg.p1_secret, p2: lastMsg.p2_secret });
             setWinnerName(lastMsg.winner_name || "Unknown");
             
             if (lastMsg.winner_id === clientId) {
                 setGameResult("WIN");
                 confetti({
                    particleCount: 150,
                    spread: 70,
                    origin: { y: 0.6 },
                    colors: ['#A020F0', '#FFD700', '#00FF94']
                 });
             } else if (lastMsg.winner_id === null) {
                 setGameResult("DRAW");
             } else {
                 setGameResult("LOSE");
             }
        }
    }
  }, [messages, clientId]);

  const copyRoomCode = () => {
    navigator.clipboard.writeText(roomId);
    toast.success("Room code copied!");
  };

  const handleSetup = () => {
      if (!nameInput.trim()) {
          toast.error("Name is required");
          return;
      }
      if (secretInput.length !== 4 || new Set(secretInput).size !== 4) {
          toast.error("Must be 4 unique digits");
          return;
      }
      setSetup(nameInput, secretInput);
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
      window.location.reload();
  }
  
  // Determine names
  const myName = players?.player1?.id === clientId ? players.player1.name : (players?.player2?.id === clientId ? players.player2.name : "YOU");
  const oppName = players?.player1?.id === clientId ? players?.player2?.name : (players?.player2?.id === clientId ? players?.player1?.name : "OPPONENT");

  if (!gameState) return <div className="flex h-screen items-center justify-center text-primary animate-pulse">CONNECTING...</div>;

  return (
    <div className="min-h-screen p-4 flex flex-col md:flex-row gap-4 bg-background relative overflow-hidden">
        
        {/* Header / HUD */}
        <div className="md:fixed top-0 left-0 w-full p-4 flex justify-between items-center z-50 glass-panel md:bg-black/20 border-b border-white/5">
            <div className="flex items-center gap-4">
                <div className="font-heading text-xl md:text-2xl text-primary neon-text tracking-widest">NUMBLE</div>
                <div className="bg-white/5 px-3 py-1 rounded text-sm font-mono flex items-center gap-2">
                    ROOM: {roomId}
                    <Copy className="w-3 h-3 cursor-pointer hover:text-primary" onClick={copyRoomCode} />
                </div>
            </div>
            
            {gameState.status === 'playing' && gameState.start_time && (
                <Timer startTime={gameState.start_time} />
            )}

            <div className="flex gap-2">
                 <Button variant="ghost" size="sm" onClick={() => setIsRulesOpen(true)}>RULES</Button>
                 <Button variant="destructive" size="sm" onClick={handleExit}><LogOut className="w-4 h-4" /></Button>
            </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col md:flex-row gap-8 items-start justify-center pt-20">
            
            {/* WAITING PHASE */}
            {gameState.status === 'waiting' && (
                <div className="absolute inset-0 flex items-center justify-center z-40 bg-black/80 backdrop-blur-sm">
                    <div className="text-center space-y-4">
                        <h2 className="text-4xl font-heading text-primary animate-pulse">WAITING FOR OPPONENT...</h2>
                        <div className="glass-panel p-4 rounded-xl">
                            <p className="text-sm text-muted-foreground mb-2">Room Code:</p>
                            <p className="text-3xl font-bold tracking-widest text-primary select-all">{roomId}</p>
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
                        <h2 className="text-3xl font-heading text-white">SETUP</h2>
                        
                        <div className="space-y-4 text-left">
                            <div>
                                <label className="text-xs text-muted-foreground ml-1">YOUR NAME</label>
                                <Input 
                                    value={nameInput}
                                    onChange={(e) => setNameInput(e.target.value)}
                                    placeholder="ENTER NAME"
                                    className="text-2xl h-14"
                                    maxLength={12}
                                />
                            </div>
                            
                            <div>
                                <label className="text-xs text-muted-foreground ml-1">SECRET NUMBER (4 UNIQUE DIGITS)</label>
                                <Input 
                                    value={secretInput}
                                    onChange={(e) => {
                                        const val = e.target.value.replace(/[^0-9]/g, '').slice(0, 4);
                                        setSecretInput(val);
                                    }}
                                    className="text-4xl tracking-[0.5em] h-20"
                                    placeholder="0000"
                                    type="tel"
                                />
                            </div>
                        </div>

                        <Button onClick={handleSetup} className="w-full text-lg h-12 skew-x-[-10deg]">READY</Button>
                    </motion.div>
                </div>
            )}
            
            {gameState.status === 'setup' && isReady && (
                 <div className="absolute inset-0 flex items-center justify-center z-40 bg-black/80 backdrop-blur-sm">
                    <div className="text-center space-y-4">
                        <h2 className="text-4xl font-heading text-white">YOU ARE READY</h2>
                        <p className="text-muted-foreground">Waiting for host to start...</p>
                        
                        {gameState.player1 && gameState.player1.id === clientId && (
                             <Button 
                                onClick={startGame} 
                                size="lg" 
                                className="mt-4 w-64 h-16 text-xl"
                                disabled={!gameState.player1?.is_ready || !gameState.player2?.is_ready}
                             >
                                LET'S BEGIN
                             </Button>
                        )}
                        
                        <div className="flex gap-8 justify-center mt-8">
                             <div className="flex flex-col items-center">
                                 <div className={`w-3 h-3 rounded-full mb-2 ${gameState.player1?.is_ready ? 'bg-primary shadow-[0_0_10px_#00FF94]' : 'bg-gray-700'}`} />
                                 <span className="text-sm">PLAYER 1</span>
                             </div>
                             <div className="flex flex-col items-center">
                                 <div className={`w-3 h-3 rounded-full mb-2 ${gameState.player2?.is_ready ? 'bg-primary shadow-[0_0_10px_#00FF94]' : 'bg-gray-700'}`} />
                                 <span className="text-sm">PLAYER 2</span>
                             </div>
                        </div>
                    </div>
                 </div>
            )}

             {/* GAME OVER PHASE */}
             {gameState.status === 'finished' && gameResult && (
                 <div className="absolute inset-0 flex flex-col items-center justify-center z-50 bg-black/90 backdrop-blur-md">
                     <motion.div 
                        initial={{ scale: 0.5, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="text-center space-y-6"
                     >
                        <h1 className={`text-6xl md:text-8xl font-black font-heading ${gameResult === 'WIN' ? 'text-primary neon-text' : gameResult === 'LOSE' ? 'text-destructive' : 'text-accent'}`}>
                            {gameResult === 'WIN' ? `${myName} — WIN` : gameResult === 'LOSE' ? `${myName} — LOSE` : 'DRAW'}
                        </h1>
                        
                        <div className="flex gap-12 justify-center py-8">
                            <div className="text-center">
                                <p className="text-muted-foreground text-sm mb-2">YOUR SECRET</p>
                                <div className="text-4xl font-mono font-bold tracking-widest bg-white/5 p-4 rounded border border-white/10">
                                    {players?.player1?.id === clientId ? revealedSecrets?.p1 : revealedSecrets?.p2}
                                </div>
                            </div>
                            <div className="text-center">
                                <p className="text-muted-foreground text-sm mb-2">OPPONENT SECRET</p>
                                <div className="text-4xl font-mono font-bold tracking-widest bg-white/5 p-4 rounded border border-white/10">
                                    {players?.player1?.id === clientId ? revealedSecrets?.p2 : revealedSecrets?.p1}
                                </div>
                            </div>
                        </div>

                         <div className="flex gap-4 justify-center">
                             <Button onClick={rematch} size="lg" className="h-14 px-8 text-lg skew-x-[-10deg]">
                                <RefreshCw className="mr-2" /> PLAY AGAIN
                             </Button>
                         </div>
                     </motion.div>
                 </div>
             )}


            {/* MY BOARD (LEFT) */}
            <div className="w-full md:w-1/2 max-w-md flex flex-col gap-4">
                <div className="glass-panel p-4 rounded-xl border-l-4 border-primary min-h-[600px] flex flex-col">
                    <div className="flex justify-between items-center mb-4 pb-2 border-b border-white/5">
                        <h3 className="font-heading text-xl text-primary">{myName || "YOU"}</h3>
                        <div className="text-xs text-muted-foreground">ATTEMPTS: {myGuesses.length}/6</div>
                    </div>
                    
                    <div className="flex-1">
                        <Board guesses={myGuesses} isMe={true} />
                    </div>
                    
                    {/* INPUT AREA */}
                    {gameState.status === 'playing' && (
                        <form onSubmit={handleSubmitGuess} className="mt-4 flex gap-2">
                             <Input 
                                value={guessInput}
                                onChange={(e) => {
                                    const val = e.target.value.replace(/[^0-9]/g, '').slice(0, 4);
                                    setGuessInput(val);
                                }}
                                placeholder="GUESS"
                                className="text-2xl tracking-widest font-bold h-14"
                                autoFocus
                                disabled={myGuesses.length >= 6}
                             />
                             <Button type="submit" className="h-14 px-6" disabled={guessInput.length !== 4 || myGuesses.length >= 6}>SUBMIT</Button>
                        </form>
                    )}
                </div>
            </div>

            {/* OPPONENT BOARD (RIGHT) */}
            <div className="w-full md:w-1/2 max-w-md flex flex-col gap-4">
                <div className="glass-panel p-4 rounded-xl border-r-4 border-secondary min-h-[600px] flex flex-col">
                    <div className="flex justify-between items-center mb-4 pb-2 border-b border-white/5">
                         <div className="text-xs text-muted-foreground">ATTEMPTS: {oppGuesses.length}/6</div>
                         <h3 className="font-heading text-xl text-secondary">{oppName || "OPPONENT"}</h3>
                    </div>
                    
                    <div className="flex-1">
                        <Board guesses={oppGuesses} isMe={false} />
                    </div>
                </div>
            </div>

        </div>
        
        <RulesModal open={isRulesOpen} onOpenChange={setIsRulesOpen} />
    </div>
  );
}
