import React from 'react';
import { motion } from 'framer-motion';

const TILE_COLORS = {
    green: 'bg-[#39D98A] text-black border-[#39D98A] shadow-[0_0_15px_rgba(57,217,138,0.6)]',
    yellow: 'bg-[#FFCB45] text-black border-[#FFCB45] shadow-[0_0_15px_rgba(255,203,69,0.6)]',
    grey: 'bg-[#606060] text-white/50 border-[#606060]',
    empty: 'bg-black/30 border-white/10 text-white',
    filled: 'bg-black/50 border-white/30 text-white'
};

const Row = ({ guess, isMe }) => {
    const tiles = [];
    
    // If guess exists, render it. If not, render empty slots.
    if (guess) {
        for (let i = 0; i < 4; i++) {
            const digit = guess.guess[i];
            const feedback = guess.feedback[i];
            tiles.push(
                <motion.div
                    key={i}
                    initial={{ rotateX: 0 }}
                    animate={{ rotateX: 360 }}
                    transition={{ delay: i * 0.1, duration: 0.5 }}
                    className={`w-14 h-14 md:w-16 md:h-16 flex items-center justify-center text-2xl md:text-3xl font-mono font-bold border-2 rounded-md ${TILE_COLORS[feedback]}`}
                >
                    {digit}
                </motion.div>
            );
        }
    } else {
        for (let i = 0; i < 4; i++) {
            tiles.push(
                <div key={i} className={`w-14 h-14 md:w-16 md:h-16 border-2 rounded-md ${TILE_COLORS.empty}`} />
            );
        }
    }

    return (
        <div className="flex gap-2 justify-center mb-2">
            {tiles}
        </div>
    );
};

export default function Board({ guesses, isMe }) {
    // Always render 6 rows
    const rows = [];
    for (let i = 0; i < 6; i++) {
        rows.push(<Row key={i} guess={guesses[i]} isMe={isMe} />);
    }

    return (
        <div className="flex flex-col">
            {rows}
        </div>
    );
}
