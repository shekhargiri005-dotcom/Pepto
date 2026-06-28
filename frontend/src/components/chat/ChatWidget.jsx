import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    
    return (
        <div className="fixed bottom-6 right-6 z-50">
            <AnimatePresence>
                {isOpen && (
                    <motion.div 
                        initial={{ opacity: 0, y: 20, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.9 }}
                        className="glass w-[350px] h-[500px] mb-4 rounded-2xl border border-slate-700 flex flex-col overflow-hidden shadow-2xl"
                    >
                        <div className="bg-gradient-to-r from-[#6C63FF] to-[#FF6584] p-4 flex justify-between items-center text-white">
                            <div className="flex items-center gap-2">
                                <span className="text-2xl">🤖</span>
                                <div>
                                    <h3 className="font-bold">Pepto Assistant</h3>
                                    <p className="text-xs opacity-80">Online 24/7</p>
                                </div>
                            </div>
                            <button onClick={() => setIsOpen(false)} className="hover:bg-white/20 p-1 rounded">✕</button>
                        </div>
                        <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 bg-[#0F0F1A]/80">
                            <div className="bg-[#1A1A2E] p-3 rounded-lg rounded-tl-none self-start max-w-[85%] text-sm text-slate-200">
                                Hi there! 🐾 I'm your Pepto AI assistant. How can I help you and your pet today?
                            </div>
                        </div>
                        <div className="p-3 border-t border-slate-800 bg-[#1A1A2E]">
                            <input 
                                type="text" 
                                placeholder="Type a message..." 
                                className="w-full bg-[#0F0F1A] border border-slate-700 rounded-full px-4 py-2 text-sm text-white outline-none focus:border-[#6C63FF] transition-colors"
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            
            <button 
                onClick={() => setIsOpen(!isOpen)}
                className="w-14 h-14 rounded-full gradient-btn flex items-center justify-center text-white text-2xl shadow-lg hover:scale-110 transition-transform ml-auto relative"
            >
                {!isOpen && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-ping" />
                )}
                💬
            </button>
        </div>
    );
};
export default ChatWidget;
