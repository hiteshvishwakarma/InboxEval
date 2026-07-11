import React from 'react';
import fs from 'fs';
import path from 'path';

export default async function EvalPage({ params }) {
  const { id } = params;
  const dataPath = path.join(process.cwd(), '../data/evals', `${id}.json`);

  if (!fs.existsSync(dataPath)) {
    return (
      <main className="container" style={{ textAlign: 'center', marginTop: '10rem' }}>
        <h1 style={{ color: '#ef4444' }}>Evaluation Not Found</h1>
        <p className="subtitle" style={{ margin: '0 auto' }}>The ID {id} does not exist in our database.</p>
      </main>
    );
  }

  const fileContents = fs.readFileSync(dataPath, 'utf8');
  const evalResult = JSON.parse(fileContents);

  return (
    <main>
      <div className="bg-gradient-blob"></div>
      <div className="bg-gradient-blob right"></div>

      <div className="container">
        <header>
          <h1>InboxEval Scorecard</h1>
          <p className="subtitle">
            Shareable Evidence ID: <span style={{ color: 'var(--accent-1)' }}>{id}</span>
          </p>
        </header>

        <section className="glass" style={{ padding: '2rem', marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Original Email</h3>
          <pre style={{ 
            background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', 
            whiteSpace: 'pre-wrap', color: 'var(--text-primary)', fontFamily: 'inherit' 
          }}>
            {evalResult.email_text}
          </pre>
        </section>

        <section className="glass" style={{ padding: '2rem', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.5rem' }}>Overall Score:</h3>
            <span style={{ fontSize: '2.5rem', fontWeight: '800', color: '#10b981' }}>
              {evalResult.overall_score}/10
            </span>
          </div>
          <p style={{ fontStyle: 'italic', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
            Moderator Reasoning: "{evalResult.reasoning}"
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
        </section>

        <section className="glass" style={{ padding: '2rem', borderLeft: '4px solid #ef4444', marginBottom: '2rem' }}>
          <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>Agent 1: Harsh Critic</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{evalResult.debate?.critic || "Not recorded."}</p>
        </section>

        <section className="glass" style={{ padding: '2rem', borderLeft: '4px solid #3b82f6', marginBottom: '4rem' }}>
          <h3 style={{ color: '#3b82f6', marginBottom: '1rem' }}>Agent 2: Constructive Advocate</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{evalResult.debate?.advocate || "Not recorded."}</p>
        </section>
      </div>
    </main>
  );
}
