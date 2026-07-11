"use client";
import React, { useState, useEffect } from 'react';

export default function Home() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

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
      </div>
    </main>
  );
}
