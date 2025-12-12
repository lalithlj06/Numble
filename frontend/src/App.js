import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { GameProvider } from "@/context/GameContext";
import Lobby from "@/pages/Lobby";
import GameRoom from "@/pages/GameRoom";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <GameProvider>
      <div className="App min-h-screen font-body text-foreground">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Lobby />} />
            <Route path="/game/:roomId" element={<GameRoom />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-center" theme="dark" />
      </div>
    </GameProvider>
  );
}

export default App;
