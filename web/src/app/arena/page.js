"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Send, Activity, Cpu, ShieldAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Arena() {
  const [prompt, setPrompt] = useState('');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [results, setResults] = useState(null);
  
  const handleEvaluate = async (e) => {
    e.preventDefault();
    if (!prompt) return;
    
    setIsEvaluating(true);
    try {
      const response = await fetch('/api/arena/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          available_models: [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "gemma2-9b-it",
            "mixtral-8x7b-32768"
          ]
        })
      });

      if (!response.ok) throw new Error("Failed to generate");
      
      const data = await response.json();
      
      setResults({
        modelA: { name: data.modelA, output: data.textA },
        modelB: { name: data.modelB, output: data.textB },
      });
    } catch (error) {
      console.error(error);
      alert("Error generating responses. Is your GROQ_API_KEY set?");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleVote = (winner) => {
    alert(`Vote recorded for ${winner}. Updating ELO Matrix...`);
    setResults(null);
    setPrompt('');
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white font-mono selection:bg-cyan-500 selection:text-black overflow-x-hidden">
      
      {/* Top Navigation Bar */}
      <header className="border-b border-neutral-900 bg-black p-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <Link href="/" className="hover:text-cyan-400 transition-colors flex items-center gap-2 text-sm uppercase">
            <ArrowLeft size={16} /> Exit Arena
          </Link>
          <div className="h-4 w-px bg-neutral-800" />
          <h1 className="text-xl font-black tracking-tighter text-cyan-500">InboxEval // ARENA</h1>
        </div>
        
        <div className="flex items-center gap-6 text-xs text-neutral-500">
          <span className="flex items-center gap-2"><Activity size={12} className="text-green-500 animate-pulse" /> LIVE ELO TRACKING</span>
          <span className="flex items-center gap-2"><Cpu size={12} /> 12 MODELS ACTIVE</span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Input Panel */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[#0a0a0a] border border-neutral-900 p-6 rounded-lg relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-blue-600 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500" />
            
            <h2 className="text-sm font-bold uppercase mb-4 text-cyan-400 flex items-center gap-2">
              <ShieldAlert size={16} /> Evaluation Protocol
            </h2>
            
            <form onSubmit={handleEvaluate}>
              <div className="mb-4">
                <label className="block text-xs text-neutral-500 mb-2">TARGET CONTEXT / EMAIL INSTRUCTION</label>
                <textarea 
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Paste the customer email or instruction here to evaluate how the models respond..."
                  className="w-full h-48 bg-black border border-neutral-800 rounded p-4 text-sm focus:outline-none focus:border-cyan-500 transition-colors resize-none shadow-inner"
                  required
                />
              </div>
              
              <button 
                type="submit" 
                disabled={isEvaluating || !prompt}
                className="w-full bg-cyan-950 hover:bg-cyan-500 text-cyan-500 hover:text-black border border-cyan-800 hover:border-cyan-400 py-3 rounded font-bold tracking-widest transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isEvaluating ? (
                  <span className="animate-pulse">GENERATING RESPONSES...</span>
                ) : (
                  <>INITIATE BLIND TEST <Send size={16} /></>
                )}
              </button>
            </form>
          </div>

          {/* Stats Panel */}
          <div className="bg-[#0a0a0a] border border-neutral-900 p-6 rounded-lg">
            <h3 className="text-xs text-neutral-500 mb-4 uppercase">Current Leaderboard (Top 3)</h3>
            <div className="space-y-3">
              {[
                { name: 'GPT-4o', elo: 1250, delta: '+12' },
                { name: 'Claude-3.5-Sonnet', elo: 1245, delta: '+8' },
                { name: 'Llama-3-70B', elo: 1190, delta: '-4' }
              ].map((model, i) => (
                <div key={i} className="flex justify-between items-center text-sm border-b border-neutral-900 pb-2">
                  <span className="text-neutral-300">{i + 1}. {model.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-white">{model.elo}</span>
                    <span className={`text-[10px] ${model.delta.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>{model.delta}</span>
                  </div>
                </div>
              ))}
            </div>
            <button className="w-full mt-4 text-xs text-neutral-500 hover:text-cyan-400 transition-colors uppercase border border-neutral-800 py-2">
              View Full Matrix
            </button>
          </div>
        </div>

        {/* Right Column: Battle Arena */}
        <div className="lg:col-span-2 relative">
          {!results && !isEvaluating && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-neutral-700 border border-neutral-900 border-dashed rounded-lg bg-[#0a0a0a]/50">
              <ShieldAlert size={48} className="mb-4 opacity-50" />
              <p className="uppercase tracking-widest text-sm">Awaiting Input Sequence</p>
              <p className="text-xs mt-2 opacity-50">Enter a prompt on the left to begin the blind evaluation.</p>
            </div>
          )}

          {isEvaluating && (
            <div className="absolute inset-0 flex items-center justify-center border border-cyan-900/50 rounded-lg bg-black/80 backdrop-blur-sm z-10">
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 border-4 border-cyan-900 border-t-cyan-400 rounded-full animate-spin mb-4" />
                <p className="text-cyan-400 animate-pulse uppercase tracking-widest text-sm">Synthesizing Outputs...</p>
              </div>
            </div>
          )}

          <AnimatePresence>
            {results && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-2 gap-6 h-full"
              >
                {/* Model A */}
                <div className="bg-[#0a0a0a] border border-neutral-800 rounded-lg p-6 flex flex-col h-full hover:border-cyan-900 transition-colors">
                  <div className="flex justify-between items-center mb-4 border-b border-neutral-900 pb-2">
                    <h3 className="font-bold text-neutral-400">MODEL A</h3>
                    <span className="text-[10px] bg-neutral-900 px-2 py-1 text-neutral-500">ANONYMOUS</span>
                  </div>
                  <div className="flex-1 bg-black p-4 rounded border border-neutral-900 text-sm leading-relaxed text-neutral-300 shadow-inner">
                    {results.modelA.output}
                  </div>
                  <button 
                    onClick={() => handleVote('Model A')}
                    className="w-full mt-4 bg-transparent border border-neutral-700 hover:bg-white hover:text-black py-3 font-bold uppercase tracking-wider transition-all"
                  >
                    👈 Model A is Better
                  </button>
                </div>

                {/* Model B */}
                <div className="bg-[#0a0a0a] border border-neutral-800 rounded-lg p-6 flex flex-col h-full hover:border-blue-900 transition-colors">
                  <div className="flex justify-between items-center mb-4 border-b border-neutral-900 pb-2">
                    <h3 className="font-bold text-neutral-400">MODEL B</h3>
                    <span className="text-[10px] bg-neutral-900 px-2 py-1 text-neutral-500">ANONYMOUS</span>
                  </div>
                  <div className="flex-1 bg-black p-4 rounded border border-neutral-900 text-sm leading-relaxed text-neutral-300 shadow-inner">
                    {results.modelB.output}
                  </div>
                  <button 
                    onClick={() => handleVote('Model B')}
                    className="w-full mt-4 bg-transparent border border-neutral-700 hover:bg-white hover:text-black py-3 font-bold uppercase tracking-wider transition-all"
                  >
                    Model B is Better 👉
                  </button>
                </div>
                
                {/* Tie / Both Bad */}
                <div className="col-span-2 grid grid-cols-2 gap-4">
                  <button onClick={() => handleVote('Tie')} className="bg-neutral-900 hover:bg-neutral-800 text-neutral-400 py-2 text-xs uppercase border border-neutral-800">Tie</button>
                  <button onClick={() => handleVote('Both Bad')} className="bg-neutral-900 hover:bg-neutral-800 text-neutral-400 py-2 text-xs uppercase border border-neutral-800">Both are bad</button>
                </div>

              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </main>
    </div>
  );
}
