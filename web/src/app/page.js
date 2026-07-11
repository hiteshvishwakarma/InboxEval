"use client";
import React, { useState, useEffect } from 'react';

export default function Home() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  // Sandbox State
  const [emailInput, setEmailInput] = useState("");
  const [isGrading, setIsGrading] = useState(false);
  const [evalResult, setEvalResult] = useState(null);

  useEffect(() => {
    fetch('/api/leaderboard')
      .then(res => res.json())
      .then(data => {
        setLeaderboard(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleGradeEmail = async () => {
    if (!emailInput.trim()) return;
    setIsGrading(true);
    setEvalResult(null);
    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emailText: emailInput })
      });
      const data = await res.json();
      setEvalResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGrading(false);
    }
  };

  return (
    <main>
      <div className="bg-gradient-blob"></div>
      <div className="bg-gradient-blob right"></div>
      
      <div className="container">
        <header>
          <h1>InboxEval Leaderboard</h1>
          <p className="subtitle">
            The industry standard benchmark for enterprise AI email generation. 
            Models are evaluated across 12 strict parameters including Tone, Persona Adherence, and Hallucination rates.
          </p>
        </header>

        <section className="glass" style={{ padding: '1rem', marginTop: '2rem', minHeight: '300px' }}>
          {loading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--accent-1)' }}>
               <h2>Loading Live Evaluator Data...</h2>
            </div>
          ) : leaderboard.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
               <h2>No benchmarks run yet.</h2>
            </div>
          ) : (
            <table className="leaderboard">
              <thead>
                <tr>
                  <th style={{ width: '10%' }}>Rank</th>
                  <th style={{ width: '40%' }}>Model</th>
                  <th style={{ width: '20%' }}>Size</th>
                  <th style={{ width: '30%' }}>Overall Score (Out of 10)</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((item) => (
                  <tr key={item.model}>
                    <td>
                      <span className="rank">#{item.rank}</span>
                    </td>
                    <td>
                      <div className="model-name">
                        {item.model}
                        {item.rank === 1 && <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399' }}>SOTA</span>}
                      </div>
                    </td>
                    <td>
                      <span className="badge">{item.parameters}</span>
                    </td>
                    <td>
                      <div className="score">{item.score.toFixed(2)}</div>
                      <div className="score-bar-container">
                        <div 
                          className="score-bar" 
                          style={{ width: `${(item.score / 10) * 100}%` }}
                        ></div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* Interactive Sandbox Section */}
        <section className="glass" style={{ padding: '2rem', marginTop: '4rem', marginBottom: '4rem' }}>
          <h2 style={{ fontSize: '2rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>Live Evaluator Sandbox</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
            Paste any AI-generated email below. Our elite Judge model will grade it against our 12 world-class parameters in real-time.
          </p>
          
          <textarea 
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            placeholder="Subject: Project Update\n\nHi Team,\n\nI wanted to reach out regarding..."
            style={{
              width: '100%',
              height: '200px',
              backgroundColor: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--card-border)',
              borderRadius: '12px',
              padding: '1rem',
              color: 'var(--text-primary)',
              fontFamily: 'inherit',
              fontSize: '1rem',
              resize: 'vertical',
              marginBottom: '1.5rem'
            }}
          />
          
          <button 
            onClick={handleGradeEmail}
            disabled={isGrading || !emailInput.trim()}
            style={{
              background: isGrading ? '#475569' : 'var(--accent-gradient)',
              color: '#fff',
              border: 'none',
              padding: '1rem 2rem',
              borderRadius: '8px',
              fontSize: '1.1rem',
              fontWeight: '600',
              cursor: isGrading ? 'not-allowed' : 'pointer',
              transition: 'transform 0.2s',
              boxShadow: '0 4px 15px rgba(59, 130, 246, 0.4)'
            }}
          >
            {isGrading ? 'Evaluating (This takes ~5s)...' : 'Grade My Email'}
          </button>

          {evalResult && evalResult.scorecard && (
            <div style={{ marginTop: '3rem', borderTop: '1px solid var(--card-border)', paddingTop: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '1.5rem' }}>Overall Score:</h3>
                <span style={{ fontSize: '2.5rem', fontWeight: '800', color: '#10b981' }}>
                  {evalResult.overall_score}/10
                </span>
              </div>
              <p style={{ fontStyle: 'italic', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
                "{evalResult.reasoning}"
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                {Object.entries(evalResult.scorecard).map(([param, score]) => (
                  <div key={param} style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
                    <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                      {param.replace('_', ' ')}
                    </div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700', color: score >= 8 ? '#34d399' : score >= 5 ? '#fbbf24' : '#ef4444' }}>
                      {score}/10
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
