import React from 'react';

const LEADERBOARD_DATA = [
  { rank: 1, model: "qwen/qwen3-32b", score: 9.56, parameters: "32B", type: "Open Source" },
  { rank: 2, model: "meta-llama/llama-4-scout-17b", score: 9.38, parameters: "17B", type: "Open Source" },
  { rank: 3, model: "llama-3.1-8b-instant", score: 9.37, parameters: "8B", type: "Open Source" },
];

export default function Home() {
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

        <section className="glass" style={{ padding: '1rem', marginTop: '2rem' }}>
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
              {LEADERBOARD_DATA.map((item) => (
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
        </section>
      </div>
    </main>
  );
}
