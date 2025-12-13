import React, { useState, useEffect } from 'react';
import { useGame } from '@/context/GameContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion } from 'framer-motion';
import RulesModal from '@/components/RulesModal';
import { Rocket } from 'lucide-react';

export default function Lobby() {
  const { createRoom, joinRoom, roomId, isConnected } = useGame();
  const navigate = useNavigate();
  const [joinCode, setJoinCode] = useState("");
  const [isRulesOpen, setIsRulesOpen] = useState(false);

  useEffect(() => {
    if (roomId) {
      navigate(`/game/${roomId}`);
    }
  }, [roomId, navigate]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 md:p-8 relative overflow-hidden bg-background">
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-background z-[-1]" />
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[120px]" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-[120px]" />

      <div className="w-full max-w-md space-y-8 z-10 flex flex-col items-center">
        <div className="text-center space-y-4">
          {/* Static Logo - Sharp, No Blur, No Animation, Mild Gradient */}
          <h1 className="text-5xl md:text-8xl font-heading font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-[#00FF94] to-[#00F0FF] drop-shadow-md select-none">
            NUMBLE
          </h1>
          <p className="text-muted-foreground text-base md:text-lg italic tracking-wider">
            Think fast or stay last.
          </p>
        </div>

        <div className="glass-panel w-full p-6 md:p-8 rounded-2xl space-y-6 flex flex-col items-center">
          <div className="space-y-4 w-full">
            <Button 
              onClick={createRoom} 
              disabled={!isConnected}
              className="w-full h-14 text-lg font-bold bg-primary hover:bg-primary/90 text-black skew-x-[-5deg]"
            >
              <Rocket className="mr-2 h-5 w-5" /> CREATE ROOM
            </Button>
            
            <div className="relative w-full">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-white/10" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-black px-2 text-muted-foreground">Or Join Existing</span>
              </div>
            </div>

            <div className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-2 w-full">
              <Input 
                placeholder="ENTER CODE" 
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                maxLength={6}
                className="uppercase tracking-[0.5em] font-bold text-center h-14 bg-black/40"
              />
              <Button 
                onClick={() => joinRoom(joinCode)}
                disabled={!isConnected || joinCode.length < 4}
                variant="secondary"
                className="skew-x-[-5deg] h-14 w-full md:w-auto px-8"
              >
                JOIN
              </Button>
            </div>
          </div>
        </div>

        <div className="flex w-full justify-between items-center text-sm text-muted-foreground px-2">
          <button onClick={() => setIsRulesOpen(true)} className="hover:text-primary transition-colors underline decoration-dotted underline-offset-4">
            HOW TO PLAY
          </button>
          <span>v1.0 MVP</span>
        </div>
      </div>

      <RulesModal open={isRulesOpen} onOpenChange={setIsRulesOpen} />
    </div>
  );
}
