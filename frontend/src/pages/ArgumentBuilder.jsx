import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { buildArguments } from '../services/api';

// ── Strength badge ────────────────────────────────────────────────────────────
function StrengthBadge({ strength }) {
  const map = {
    strong:        { bg: '#d4edda', color: '#155724', border: '#c3e6cb', label: '💪 Strong'        },
    moderate:      { bg: '#fff3cd', color: '#856404', border: '#ffeeba', label: '⚖️ Moderate'      },
    supplementary: { bg: '#e2e3e5', color: '#383d41', border: '#d6d8db', label: '📌 Supplementary' },
  };
  const key = strength?.toLowerCase() || 'supplementary';
  const s   = map[key] || map.supplementary;
  return (
    <span style={{
      display: 'inline-block', padding: '3px 12px', borderRadius: 12,
      fontSize: '0.78rem', fontWeight: 700,
      backgroundColor: s.bg, color: s.color, border: `1px solid ${s.border}`,
    }}>
      {s.label}
    </span>
  );
}

// ── Single argument card ──────────────────────────────────────────────────────
function ArgumentCard({ item, index }) {
  const rankColors = ['#1a5276', '#1f618d', '#2874a6', '#2e86c1', '#3498db',
                      '#5dade2', '#7fb3d3', '#a9cce3', '#d6eaf8', '#ebf5fb'];
  const rankColor  = rankColors[index] || '#3498db';

  return (
    <div style={{
      display: 'flex', gap: '1rem', alignItems: 'flex-start',
      backgroundColor: '#fff', borderRadius: 12, padding: '1.5rem',
      marginBottom: '1.2rem', boxShadow: '0 2px 10px rgba(0,0,0,0.07)',
      border: '1px solid #e8ecef', borderLeft: `5px solid ${rankColor}`,
    }}>
      {/* Rank circle */}
      <div style={{
        minWidth: 48, height: 48, borderRadius: '50%',
        backgroundColor: rankColor, color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontWeight: 800, fontSize: '1.2rem', flexShrink: 0,
      }}>
        {item.rank}
      </div>

      {/* Content */}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
          <h4 style={{ margin: 0, color: '#2c3e50', fontSize: '1.05rem' }}>{item.title}</h4>
          <StrengthBadge strength={item.strength} />
        </div>

        <p style={{ color: '#444', lineHeight: 1.7, margin: '0 0 10px 0', fontSize: '0.97rem' }}>
          {item.argument}
        </p>

        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          backgroundColor: '#f4f6f8', borderRadius: 6,
          padding: '4px 12px', fontSize: '0.82rem', color: '#555',
        }}>
          <span>⚖️</span>
          <strong>Legal basis:</strong>&nbsp;{item.legal_basis}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
function ArgumentBuilder() {
  const navigate = useNavigate();

  const [analyzerData,  setAnalyzerData]  = useState(null);
  const [matchingData,  setMatchingData]  = useState(null);
  const [arguments_,    setArguments]     = useState([]);
  const [isGenerating,  setIsGenerating]  = useState(false);
  const [message,       setMessage]       = useState('');
  const [generated,     setGenerated]     = useState(false);

  // ── Read both upstream results from sessionStorage ────────────────────────
  useEffect(() => {
    const ad = sessionStorage.getItem('caseAnalyzerData');
    const md = sessionStorage.getItem('caseMatchingData');
    if (ad) setAnalyzerData(JSON.parse(ad));
    if (md) setMatchingData(JSON.parse(md));
  }, []);

  const bothReady = !!(analyzerData && matchingData);

  // ── Generate arguments ────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setIsGenerating(true);
    setMessage('');
    setArguments([]);
    setGenerated(false);

    try {
      const result = await buildArguments({
        caseDescription: analyzerData.caseDescription,
        analysisResult:  JSON.stringify(analyzerData.analysisResult),
        matchingResult:  JSON.stringify(matchingData.matchingResult),
      });

      if (result.arguments?.length > 0) {
        setArguments(result.arguments);
        setGenerated(true);
        setMessage(result.message || '');
      } else {
        setMessage(result.message || 'No arguments could be generated. Please try again.');
      }
    } catch (err) {
      setMessage(`Error: ${err.message || 'Failed to generate arguments.'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Styles ────────────────────────────────────────────────────────────────
  const lockedBox = {
    backgroundColor: '#fff8e1', border: '1px solid #ffe082',
    borderRadius: 12, padding: '2.5rem', textAlign: 'center',
    marginTop: '2rem',
  };

  return (
    <div className="container">

      {/* ── Hero ── */}
      <div className="hero fade-in-up">
        <div className="hero-left">
          <h2>⚔️ Argument Builder</h2>
          <p>
            Powered by both your case analysis and matched precedents, this tool
            generates the <strong>10 strongest arguments</strong> you can present
            to the judge — grounded in Pakistani law and real court cases.
          </p>
        </div>
      </div>

      {/* ── Locked state ── */}
      {!bothReady && (
        <div style={lockedBox} className="fade-in-up delay-1">
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
          <h3 style={{ color: '#856404', marginBottom: '0.5rem' }}>
            Complete Both Steps First
          </h3>
          <p style={{ color: '#666', maxWidth: 520, margin: '0 auto 1.5rem auto', lineHeight: 1.6 }}>
            The Argument Builder requires the outputs of both the <strong>Case Analyzer</strong> and
            the <strong>Case Matcher</strong>. Please complete these steps in order.
          </p>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <div style={{
              padding: '0.8rem 1.4rem', borderRadius: 8, fontSize: '0.9rem',
              backgroundColor: analyzerData ? '#d4edda' : '#f8d7da',
              color: analyzerData ? '#155724' : '#721c24',
              border: `1px solid ${analyzerData ? '#c3e6cb' : '#f5c6cb'}`,
            }}>
              {analyzerData ? '✅' : '❌'} Case Analyzer
            </div>
            <div style={{
              padding: '0.8rem 1.4rem', borderRadius: 8, fontSize: '0.9rem',
              backgroundColor: matchingData ? '#d4edda' : '#f8d7da',
              color: matchingData ? '#155724' : '#721c24',
              border: `1px solid ${matchingData ? '#c3e6cb' : '#f5c6cb'}`,
            }}>
              {matchingData ? '✅' : '❌'} Case Matcher
            </div>
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            {!analyzerData && (
              <button className="btn btn-primary" onClick={() => navigate('/case-intake')}
                style={{ backgroundColor: '#2c3e50', borderColor: '#2c3e50' }}>
                Go to Case Analyzer →
              </button>
            )}
            {analyzerData && !matchingData && (
              <button className="btn btn-primary" onClick={() => navigate('/case-matching')}
                style={{ backgroundColor: '#2c3e50', borderColor: '#2c3e50' }}>
                Go to Case Matcher →
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Ready state ── */}
      {bothReady && !generated && (
        <div className="card form fade-in-up delay-1" style={{ textAlign: 'center' }}>

          {/* Summary of what we have */}
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            <div style={{ padding: '0.8rem 1.4rem', borderRadius: 8, backgroundColor: '#d4edda', color: '#155724', border: '1px solid #c3e6cb', fontSize: '0.9rem' }}>
              ✅ Case Analysis Ready
            </div>
            <div style={{ padding: '0.8rem 1.4rem', borderRadius: 8, backgroundColor: '#d4edda', color: '#155724', border: '1px solid #c3e6cb', fontSize: '0.9rem' }}>
              ✅ Case Matching Ready ({matchingData?.matchingResult?.top_matches?.length || 0} precedent{matchingData?.matchingResult?.top_matches?.length !== 1 ? 's' : ''} found)
            </div>
          </div>

          <div style={{ backgroundColor: '#f8f9fa', borderRadius: 8, padding: '1rem', marginBottom: '1.5rem', textAlign: 'left' }}>
            <strong style={{ color: '#2c3e50' }}>Case:</strong>
            <span style={{ color: '#555', marginLeft: 8 }}>{analyzerData.caseTitle || '(Untitled)'}</span>
            <br />
            <strong style={{ color: '#2c3e50' }}>Description preview:</strong>
            <p style={{ color: '#777', marginTop: 4, marginBottom: 0, fontSize: '0.9rem', fontStyle: 'italic' }}>
              "{analyzerData.caseDescription?.slice(0, 180)}{analyzerData.caseDescription?.length > 180 ? '…' : ''}"
            </p>
          </div>

          <button
            onClick={handleGenerate}
            className="btn btn-primary"
            disabled={isGenerating}
            style={{ backgroundColor: '#1a5276', borderColor: '#1a5276', padding: '14px 36px', fontSize: '1.05rem', width: '100%' }}
          >
            {isGenerating
              ? '⚔️ Generating your 10 strongest arguments with AI…'
              : '⚔️ Generate My Top 10 Arguments'}
          </button>

          {message && (
            <p style={{ marginTop: 14, fontWeight: 'bold', color: '#e74c3c' }}>{message}</p>
          )}
        </div>
      )}

      {/* ── Arguments list ── */}
      {generated && arguments_.length > 0 && (
        <div className="fade-in-up">

          <div style={{
            backgroundColor: '#1a5276', color: '#fff', borderRadius: 12,
            padding: '1.5rem 2rem', marginTop: '2rem', marginBottom: '1.5rem',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
          }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.3rem' }}>⚔️ Your Top 10 Court Arguments</h3>
              <p style={{ margin: '4px 0 0 0', opacity: 0.8, fontSize: '0.9rem' }}>
                Ranked by strength · Grounded in Pakistani law &amp; real precedents
              </p>
            </div>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              style={{
                background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.4)',
                color: '#fff', padding: '8px 18px', borderRadius: 8, cursor: 'pointer', fontSize: '0.88rem',
              }}
            >
              {isGenerating ? '⏳ Regenerating…' : '🔄 Regenerate'}
            </button>
          </div>

          {arguments_.map((arg, idx) => (
            <ArgumentCard key={arg.rank} item={arg} index={idx} />
          ))}

          {/* Re-run other steps */}
          <div style={{ textAlign: 'center', padding: '1.5rem 0 2rem 0', borderTop: '1px solid #ecf0f1', marginTop: '1rem' }}>
            <p style={{ color: '#888', fontSize: '0.9rem', marginBottom: 12 }}>
              Want to refine your case? Start over from the beginning.
            </p>
            <button
              className="btn btn-outline"
              onClick={() => {
                sessionStorage.removeItem('caseAnalyzerData');
                sessionStorage.removeItem('caseMatchingData');
                navigate('/case-intake');
              }}
            >
              ← Start New Case Analysis
            </button>
          </div>
        </div>
      )}

    </div>
  );
}

export default ArgumentBuilder;
