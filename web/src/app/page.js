"use client";
import React, { useState, useEffect } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import Link from 'next/link';

export default function Home() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  // Sandbox State
  const [promptInput, setPromptInput] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("qwen/qwen3-32b");
  const [isGrading, setIsGrading] = useState(false);
  const [evalResult, setEvalResult] = useState(null);
  const [expandedRow, setExpandedRow] = useState(null);

  useEffect(() => {
    // Check if models exist in local storage, else fetch
    const fetchModels = async () => {
      try {
        const res = await fetch('/api/models');
        const models = await res.json();
        if (models && models.length > 0) {
          setAvailableModels(models);
        }
      } catch (e) {
        console.error("Failed to load models");
      }
    };
    
    fetchModels();

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
        body: JSON.stringify({ promptText: promptInput, emailText: emailInput, judgeModel: selectedModel })
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
          <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--card-border)' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Evaluation Context</h3>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa' }}>Dataset: InboxEval Golden (Enterprise Scenarios)</span>
              <span className="badge" style={{ background: 'rgba(139, 92, 246, 0.1)', color: '#c084fc' }}>Rubric: 12-Parameter IPR Standard</span>
              <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#34d399' }}>Method: 3-Stage Debate (Temp: 0.0)</span>
            </div>
            <p style={{ marginTop: '1rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Transparency is our core principle. Every model below was strictly evaluated against our proprietary Enterprise Golden Dataset. 
              Click on any scored model to view its granular performance across all 12 rigorous parameters.
            </p>
          </div>

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
                {/* 1. Show models that have scores, sorted by score */}
                {leaderboard.map((item, index) => (
                  <React.Fragment key={item.model}>
                    <tr 
                      onClick={() => setExpandedRow(expandedRow === item.model ? null : item.model)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>
                        <span className="rank">#{index + 1}</span>
                      </td>
                      <td>
                        <div className="model-name">
                          {item.model}
                          {index === 0 && <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399' }}>SOTA</span>}
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
                    {expandedRow === item.model && item.paramScores && (
                      <tr>
                        <td colSpan="4" style={{ background: 'rgba(0,0,0,0.3)', padding: '2rem', borderTop: 'none' }}>
                          <h4 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Granular Parameter Breakdown (Out of 10)</h4>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '1rem' }}>
                            {Object.entries(item.paramScores).map(([param, pScore]) => (
                              <div key={param} style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
                                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '0.5rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  {param.replace('_', ' ')}
                                </div>
                                <div style={{ fontSize: '1.25rem', fontWeight: '700', color: pScore >= 8 ? '#34d399' : pScore >= 5 ? '#fbbf24' : '#ef4444' }}>
                                  {pScore.toFixed(2)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                
                {/* 2. Show active models that are pending benchmarking */}
                {availableModels
                  .filter(modelId => !leaderboard.find(l => l.model === modelId))
                  .map((modelId) => (
                    <tr key={modelId} style={{ opacity: 0.5 }}>
                      <td>
                        <span className="rank" style={{ color: 'var(--text-secondary)' }}>-</span>
                      </td>
                      <td>
                        <div className="model-name">{modelId}</div>
                      </td>
                      <td>
                        <span className="badge" style={{ background: 'transparent', border: '1px solid var(--text-secondary)', color: 'var(--text-secondary)' }}>Live on Groq</span>
                      </td>
                      <td>
                        <div className="score" style={{ color: 'var(--text-secondary)', fontSize: '1rem', fontStyle: 'italic' }}>Pending Benchmark Data</div>
                        <div className="score-bar-container">
                           <div className="score-bar" style={{ width: '0%', background: 'transparent' }}></div>
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
            Paste the Original Prompt and the AI-generated email below. Our elite Judge model will grade it against our 12 world-class parameters in real-time.
          </p>
          
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', fontSize: '1.2rem' }}>1. The Prompt (Optional - We will auto-reverse engineer if left blank)</h3>
          <textarea 
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            placeholder="Write a highly professional email to my team about the Q3 targets..."
            style={{
              width: '100%',
              height: '100px',
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

          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', fontSize: '1.2rem' }}>2. The Generated Email</h3>
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
          
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <select 
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                padding: '1rem',
                borderRadius: '8px',
                background: 'rgba(0,0,0,0.5)',
                color: 'white',
                border: '1px solid var(--card-border)',
                fontSize: '1rem',
                cursor: 'pointer'
              }}
            >
              {availableModels.length > 0 ? (
                availableModels.map(modelId => (
                  <option key={modelId} value={modelId}>Judge: {modelId}</option>
                ))
              ) : (
                <>
                  <option value="qwen/qwen3-32b">Judge: Qwen 32B</option>
                  <option value="llama-3.1-8b-instant">Judge: Llama 3.1 8B</option>
                  <option value="llama-3.3-70b-versatile">Judge: Llama 3.3 70B</option>
                </>
              )}
            </select>

            <button 
              onClick={handleGradeEmail}
              disabled={isGrading || !emailInput.trim()}
              style={{
                flex: 1,
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
          </div>

          {evalResult && evalResult.scorecard && (
            <div style={{ marginTop: '3rem', borderTop: '1px solid var(--card-border)', paddingTop: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <h3 style={{ fontSize: '1.5rem' }}>Final Moderated Score:</h3>
                  <span style={{ fontSize: '2.5rem', fontWeight: '800', color: '#10b981' }}>
                    {evalResult.overall_score}/10
                  </span>
                </div>
                <Link href={`/eval/${evalResult.id}`} style={{
                  padding: '0.5rem 1rem', background: 'rgba(59, 130, 246, 0.2)', 
                  color: '#60a5fa', borderRadius: '8px', textDecoration: 'none', fontWeight: 'bold'
                }}>
                  View Full Evidence Report &rarr;
                </Link>
              </div>
              <p style={{ fontStyle: 'italic', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
                Moderator Reasoning: "{evalResult.reasoning}"
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {/* Visual Radar Chart */}
                <div style={{ height: '400px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '1rem' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={
                      Object.entries(evalResult.scorecard).map(([key, val]) => ({
                        subject: key.replace('_', ' '),
                        A: val,
                        fullMark: 10
                      }))
                    }>
                      <PolarGrid stroke="rgba(255,255,255,0.1)" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: 'transparent' }} />
                      <Radar name="Email Score" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              
                {/* Numeric Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '1rem', alignContent: 'start' }}>
                  {Object.entries(evalResult.scorecard).map(([param, score]) => (
                    <div key={param} style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
                      <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '0.5rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {param.replace('_', ' ')}
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: score >= 8 ? '#34d399' : score >= 5 ? '#fbbf24' : '#ef4444' }}>
                        {score}/10
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
