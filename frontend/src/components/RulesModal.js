import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function RulesModal({ open, onOpenChange }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-panel text-white border-white/10">
        <DialogHeader>
          <DialogTitle className="text-2xl font-heading text-primary">HOW TO PLAY</DialogTitle>
          <DialogDescription className="text-gray-400">
            Compete to guess the secret number first!
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 font-body">
          <ul className="list-disc pl-5 space-y-2">
            <li>Choose a <strong>4-digit secret number</strong>. Digits must be unique.</li>
            <li>Guess your opponent's number in 6 tries.</li>
            <li>Feedback clues:</li>
          </ul>
          
          <div className="flex gap-4 items-center">
            <div className="w-10 h-10 bg-[#39D98A] rounded flex items-center justify-center text-black font-bold">1</div>
            <span><strong>Green:</strong> Correct digit, correct spot.</span>
          </div>
          <div className="flex gap-4 items-center">
            <div className="w-10 h-10 bg-[#FFCB45] rounded flex items-center justify-center text-black font-bold">2</div>
            <span><strong>Yellow:</strong> Correct digit, wrong spot.</span>
          </div>
          <div className="flex gap-4 items-center">
            <div className="w-10 h-10 bg-[#606060] rounded flex items-center justify-center text-white/50 font-bold">3</div>
            <span><strong>Grey:</strong> Digit not in number.</span>
          </div>

          <p className="pt-4 text-center text-sm text-muted-foreground">
            First to guess wins. If both guess correctly on the same turn, it's a draw!
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
