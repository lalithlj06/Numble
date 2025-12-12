import React, { useState, useEffect } from 'react';
import { useGame } from '@/context/GameContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion } from 'framer-motion';
import RulesModal from '@/components/RulesModal';
import { Rocket, Users } from 'lucide-react';

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
    <div className="flex flex-col items-center justify-center min-h-screen p-4 relative overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-background z-[-1]" />
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[120px]" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-[120px]" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md space-y-8 z-10"
      >
        <div className="text-center space-y-2">
          {/* Static Logo per requirements */}
          <h1 className="text-6xl md:text-8xl font-heading font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-primary via-white to-secondary neon-text">
            NUMBLE
          </h1>
          <p className="text-muted-foreground text-lg italic tracking-wider">Think fast or stay last.</p>
        </div>

        <div className="glass-panel p-8 rounded-2xl space-y-6">
          <div className="space-y-4">
            <Button 
              onClick={createRoom} 
              disabled={!isConnected}
              className="w-full h-14 text-lg font-bold bg-primary hover:bg-primary/90 text-black skew-x-[-5deg]"
            >
              <Rocket className="mr-2 h-5 w-5" /> CREATE ROOM
            </Button>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-white/10" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">Or Join Existing</span>
              </div>
            </div>

            <div className="flex space-x-2">
              <Input 
                placeholder="ENTER ROOM CODE" 
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                maxLength={6}
                className="uppercase tracking-[0.5em] font-bold"
              />
              <Button 
                onClick={() => joinRoom(joinCode)}
                disabled={!isConnected || joinCode.length < 4}
                variant="secondary"
                className="skew-x-[-5deg]"
              >
                JOIN
              </Button>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center text-sm text-muted-foreground">
          <button onClick={() => setIsRulesOpen(true)} className="hover:text-primary transition-colors underline decoration-dotted underline-offset-4">
            HOW TO PLAY
          </button>
          <span>v1.0 MVP</span>
        </div>
      </motion.div>

      <RulesModal open={isRulesOpen} onOpenChange={setIsRulesOpen} />
    </div>
  );
}
