"use client";
import React, { useState, useEffect } from 'react';
import Link from 'next/link';

export default function ArenaPage() {
  const [promptInput, setPromptInput] = useState("");
  const [availableModels, setAvailableModels] = useState([]);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [battleData, setBattleData] = useState(null);
  const [startTime, setStartTime] = useState(0);
  
  const [voteStatus, setVoteStatus] = useState(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    fetch('/api/models')
      .then(res => res.json())
      .then(models => setAvailableModels(models))
      .catch(e => console.error(e));
  }, []);

  const handleBattle = async () => {
    if (!promptInput.trim()) return;
    setIsGenerating(true);
    setBattleData(null);
    setRevealed(false);
    setVoteStatus(null);
    
    try {
      const res = await fetch('/api/arena/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptInput, available_models: availableModels })
      });
      const data = await res.json();
      if (res.ok) {
        setBattleData(data);
        setStartTime(Date.now()); // Start Telemetry Timer
      } else {
        setVoteStatus(`Error: ${data.error}`);
      }
    } catch (e) {
      setVoteStatus("Failed to start battle.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleVote = async (winner) => {
    if (revealed) return; // Prevent double voting
    const timeToVoteMs = Date.now() - startTime;
    const approxTokens = (battleData.textA.length + battleData.textB.length) / 4;
    
    setRevealed(true);
    setVoteStatus("Recording vote...");

    try {
      const res = await fetch('/api/arena/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          modelA: battleData.modelA,
          modelB: battleData.modelB,
          winner,
          timeToVoteMs,
          approxTokens
        })
      });
      const data = await res.json();
      if (data.success) {
        setVoteStatus(data.feedback);
      } else {
        setVoteStatus(`Error: ${data.error}`);
      }
    } catch (e) {
      setVoteStatus("Failed to record vote.");
    }
  };

  return (
    <main>
      <div className="bg-gradient-blob"></div>
      <div className="bg-gradient-blob right"></div>

      <div className="container">
        <header style={{ marginBottom: '2rem' }}>
          <h1>A/B Blind Arena</h1>
          <p className="subtitle">Crowdsourcing Ground-Truth via Telemetry-Filtered Human Preference</p>
          <div style={{ marginTop: '1rem' }}>
            <Link href="/" style={{ color: '#3b82f6', textDecoration: 'none' }}>&larr; Back to Leaderboard</Link>
          </div>
        </header>

        <section className="glass" style={{ padding: '2rem', marginBottom: '2rem' }}>
          <textarea 
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            placeholder="Write a highly professional email to my team about..."
            style={{
              width: '100%', height: '100px', backgroundColor: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--card-border)', borderRadius: '12px', padding: '1rem',
              color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem',
              resize: 'vertical', marginBottom: '1.5rem'
            }}
          />
          <button 
            onClick={handleBattle}
            disabled={isGenerating || !promptInput.trim() || availableModels.length < 2}
            style={{
              width: '100%', background: isGenerating ? '#475569' : '#8b5cf6',
              color: '#fff', border: 'none', padding: '1rem 2rem', borderRadius: '8px',
              fontSize: '1.1rem', fontWeight: '600', cursor: isGenerating ? 'not-allowed' : 'pointer'
            }}
          >
            {isGenerating ? 'Summoning Models...' : 'Start Blind Battle'}
          </button>
        </section>

        {battleData && (
          <div style={{ display: 'flex', gap: '2rem', marginBottom: '2rem' }}>
            {/* Model A */}
            <div className="glass" style={{ flex: 1, padding: '2rem', borderTop: revealed && voteStatus?.includes("ignored") ? '4px solid #ef4444' : '4px solid #3b82f6' }}>
              <h2 style={{ textAlign: 'center', marginBottom: '1rem' }}>Model A</h2>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', color: 'var(--text-secondary)', minHeight: '300px' }}>
                {battleData.textA}
              </pre>
              <button onClick={() => handleVote('A')} disabled={revealed} style={{ width: '100%', padding: '1rem', marginTop: '1rem', background: 'rgba(59, 130, 246, 0.2)', border: '1px solid #3b82f6', color: '#60a5fa', borderRadius: '8px', cursor: revealed ? 'not-allowed' : 'pointer' }}>
                👈 Model A is Better
              </button>
            </div>

            {/* Model B */}
            <div className="glass" style={{ flex: 1, padding: '2rem', borderTop: revealed && voteStatus?.includes("ignored") ? '4px solid #ef4444' : '4px solid #10b981' }}>
              <h2 style={{ textAlign: 'center', marginBottom: '1rem' }}>Model B</h2>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', color: 'var(--text-secondary)', minHeight: '300px' }}>
                {battleData.textB}
              </pre>
              <button onClick={() => handleVote('B')} disabled={revealed} style={{ width: '100%', padding: '1rem', marginTop: '1rem', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#34d399', borderRadius: '8px', cursor: revealed ? 'not-allowed' : 'pointer' }}>
                👉 Model B is Better
              </button>
            </div>
          </div>
        )}

        {battleData && (
          <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
             <button onClick={() => handleVote('Tie')} disabled={revealed} style={{ padding: '1rem 3rem', background: 'rgba(255, 255, 255, 0.1)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: '8px', cursor: revealed ? 'not-allowed' : 'pointer' }}>
                🤝 Tie
              </button>
          </div>
        )}

        {revealed && (
          <div className="glass" style={{ padding: '2rem', textAlign: 'center', animation: 'fadeIn 0.5s', marginBottom: '4rem' }}>
            <h2 style={{ color: 'var(--text-primary)', marginBottom: '1rem' }}>Identities Revealed!</h2>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '4rem', marginBottom: '1.5rem', fontSize: '1.2rem' }}>
              <div><strong>Model A:</strong> <span style={{ color: '#60a5fa' }}>{battleData.modelA}</span></div>
              <div><strong>Model B:</strong> <span style={{ color: '#34d399' }}>{battleData.modelB}</span></div>
            </div>
            <div style={{ padding: '1rem', background: voteStatus.includes("ignored") ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)', color: voteStatus.includes("ignored") ? '#ef4444' : '#34d399', borderRadius: '8px', border: `1px solid ${voteStatus.includes("ignored") ? '#ef4444' : '#10b981'}` }}>
              {voteStatus}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
