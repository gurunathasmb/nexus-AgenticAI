import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiBase } from '../config';

const API_BASE = getApiBase();
const RANK_URL = `${API_BASE}/table-agent/rank`;

function TableAgentPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('show me 3rd sem results');
  const [topK, setTopK] = useState(3);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const search = async () => {
    setLoading(true);
    setError(null);
    setStatus(null);
    setResult(null);
    try {
      const res = await fetch(RANK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), top_k: topK }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data) || res.statusText);
        return;
      }
      setResult(data);
      setStatus('Tables ranked successfully!');
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(to bottom, #16213e, #0f3460)',
        color: 'white',
        padding: '24px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div
        style={{
          maxWidth: 720,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: '1.35rem' }}>Table Agent</h1>
          <button
            type="button"
            onClick={() => navigate('/chatbot')}
            style={{
              padding: '8px 14px',
              background: 'rgba(76,175,80,0.35)',
              border: '1px solid rgba(255,255,255,0.25)',
              color: 'white',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            Back to chat
          </button>
        </div>

        <p style={{ margin: 0, opacity: 0.9, lineHeight: 1.5 }}>
          Rank the most relevant academic result sources (rows in{' '}
          <code style={{ background: 'rgba(0,0,0,0.25)', padding: '2px 6px', borderRadius: 4 }}>
            aiml_academic.result_sessions
          </code>
          ).
        </p>

        <div
          style={{
            background: 'rgba(0,0,0,0.22)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 10,
            padding: 18,
          }}
        >
          <div style={{ marginBottom: 8, fontSize: 14 }}>Endpoint (POST, JSON body)</div>
          <code
            style={{
              display: 'block',
              padding: 10,
              background: '#0d1117',
              borderRadius: 6,
              fontSize: 13,
              wordBreak: 'break-all',
              color: '#7ee787',
            }}
          >
            {RANK_URL}
          </code>
          <div style={{ fontSize: 12, opacity: 0.75, marginTop: 8 }}>
            Body: {`{ "query": string, "top_k": number }`}
          </div>
        </div>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <span>Enter your query:</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              padding: 12,
              borderRadius: 8,
              border: 'none',
              background: '#E8F5E8',
              color: '#222',
            }}
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <span>Number of tables to return (top_k): {topK}</span>
          <input
            type="range"
            min={1}
            max={15}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            style={{ width: '100%' }}
          />
        </label>

        <button
          type="button"
          onClick={search}
          disabled={loading || !query.trim()}
          style={{
            padding: '12px 20px',
            background: loading ? '#555' : '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
            fontWeight: 600,
          }}
        >
          {loading ? 'Searching…' : 'Search tables'}
        </button>

        {status && (
          <div
            style={{
              padding: 12,
              background: 'rgba(76,175,80,0.25)',
              border: '1px solid rgba(129,199,132,0.5)',
              borderRadius: 8,
              color: '#c8e6c9',
            }}
          >
            {status}
          </div>
        )}

        {error && (
          <div
            style={{
              padding: 12,
              background: 'rgba(244,67,54,0.2)',
              border: '1px solid rgba(244,67,54,0.45)',
              borderRadius: 8,
            }}
          >
            {error}
          </div>
        )}

        {result && (
          <pre
            style={{
              margin: 0,
              padding: 16,
              background: '#0d1117',
              borderRadius: 10,
              overflow: 'auto',
              fontSize: 13,
              lineHeight: 1.45,
              color: '#e6edf3',
              border: '1px solid rgba(255,255,255,0.12)',
            }}
          >
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

export default TableAgentPage;
