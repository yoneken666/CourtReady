import React, { useState, useRef } from 'react';
import { matchCases } from '../services/api';

// ── Icons ────────────────────────────────────────────────────────────────────
function UploadIcon() {
  return (
    <svg className="file-drop-zone-icon" xmlns="http://www.w3.org/2000/svg"
         fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
         width="48" height="48">
      <path strokeLinecap="round" strokeLinejoin="round"
            d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775
               5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18
               19.5H6.75Z" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg className="file-icon" xmlns="http://www.w3.org/2000/svg"
         fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
         width="24" height="24">
      <path strokeLinecap="round" strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0
               1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0
               3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0
               .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504
               1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

// ── Relevance badge ───────────────────────────────────────────────────────────
function RelevanceBadge({ relevance }) {
  const map = {
    supports: { bg: '#d4edda', color: '#155724', border: '#c3e6cb', label: '✅ Supports Your Claim' },
    opposes:  { bg: '#fff3cd', color: '#856404', border: '#ffeeba', label: '⚠️ Opposes Your Claim' },
    neutral:  { bg: '#e8f4fd', color: '#1a5276', border: '#aed6f1', label: '⚖️ Neutral Precedent' },
  };
  const style = map[relevance?.toLowerCase()] || map.neutral;
  return (
    <span style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '20px',
      fontSize: '0.82rem',
      fontWeight: 700,
      backgroundColor: style.bg,
      color: style.color,
      border: `1px solid ${style.border}`,
    }}>
      {style.label}
    </span>
  );
}

// ── Similarity ring — always green, darker shade for higher % ─────────────────
function SimilarityRing({ pct }) {
  const radius = 28;
  const circ   = 2 * Math.PI * radius;
  const fill   = ((pct || 0) / 100) * circ;

  // Three shades of green depending on match strength
  const color = pct >= 60 ? '#1e8449'   // deep green  — strong match
              : pct >= 30 ? '#27ae60'   // mid green   — moderate match
              :              '#58d68d'; // light green — weak match

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 72 }}>
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#d5f5e3" strokeWidth="7" />
        <circle
          cx="36" cy="36" r={radius} fill="none"
          stroke={color} strokeWidth="7"
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 36 36)"
        />
        <text x="36" y="41" textAnchor="middle"
              fontSize="13" fontWeight="bold" fill={color}>
          {pct}%
        </text>
      </svg>
      <span style={{ fontSize: '0.72rem', color: '#888', marginTop: 2 }}>match</span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
function CaseMatching() {
  const [caseTitle,       setCaseTitle]       = useState('');
  const [caseDescription, setCaseDescription] = useState('');
  const [files,           setFiles]           = useState([]);
  const [isDragging,      setIsDragging]      = useState(false);
  const [isSearching,     setIsSearching]     = useState(false);
  const [message,         setMessage]         = useState('');
  const [results,         setResults]         = useState(null);

  const fileInputRef = useRef(null);

  // ── File handling ───────────────────────────────────────────────────────────
  const handleFileChange = (newFiles) => {
    setFiles((prev) => {
      const existing = new Set(prev.map(f => f.name));
      return [...prev, ...Array.from(newFiles).filter(f => !existing.has(f.name))];
    });
  };
  const handleDragOver  = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files.length) handleFileChange(e.dataTransfer.files);
  };
  const handleRemoveFile  = (name) => setFiles(files.filter(f => f.name !== name));
  const triggerFileInput  = () => fileInputRef.current.click();

  // ── Search ──────────────────────────────────────────────────────────────────
  const handleSearch = async (e) => {
    e.preventDefault();
    setMessage('');
    setResults(null);

    if (caseDescription.trim().length < 30 && files.length === 0) {
      setMessage('Error: Please provide a description of at least 30 characters, or upload a document.');
      return;
    }

    setIsSearching(true);
    try {
      const formData = new FormData();
      formData.append('caseTitle',       caseTitle);
      formData.append('caseDescription', caseDescription);
      if (files.length > 0) formData.append('file', files[0]);

      const data = await matchCases(formData);
      setResults(data);
      if (data.top_matches.length === 0) {
        setMessage(data.message || 'No similar cases found.');
      }
    } catch (err) {
      setMessage(`Error: ${err.message || 'Failed to search for similar cases.'}`);
    } finally {
      setIsSearching(false);
    }
  };

  // ── Styles ──────────────────────────────────────────────────────────────────
  const s = {
    resultCard: {
      backgroundColor: '#fff',
      borderRadius: 10,
      padding: '1.5rem',
      marginBottom: '1rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      border: '1px solid #e9ecef',
      display: 'flex',
      gap: '1.2rem',
      alignItems: 'flex-start',
    },
    cardBody: { flex: 1 },
    caseLabel: {
      fontSize: '1rem',
      fontWeight: 700,
      color: '#2c3e50',
      marginBottom: '4px',
    },
    sourceFile: {
      fontSize: '0.78rem',
      color: '#999',
      marginBottom: '0.5rem',
      fontStyle: 'italic',
    },
    explanation: {
      color: '#555',
      lineHeight: 1.6,
      marginTop: '0.6rem',
      fontSize: '0.95rem',
    },
    noResults: {
      textAlign: 'center',
      padding: '2rem',
      color: '#777',
      backgroundColor: '#f8f9fa',
      borderRadius: 10,
      border: '1px dashed #ccc',
    },
    sectionWrapper: {
      backgroundColor: '#fff',
      borderRadius: 12,
      padding: '2rem',
      marginTop: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.07)',
      borderTop: '4px solid #6B8E23',
    },
  };

  return (
    <div className="container">

      {/* ── Hero ── */}
      <div className="hero fade-in-up">
        <div className="hero-left">
          <h2>Case Matcher</h2>
          <p>
            Describe your family dispute and let our AI find the most relevant past
            Pakistani court cases. Discover precedents that support — or challenge —
            your legal position.
          </p>
        </div>
      </div>

      {/* ── Form ── */}
      <div className="card form fade-in-up delay-1">
        <form onSubmit={handleSearch}>

          <h4 style={{ marginBottom: 20 }}>1. Case Details</h4>

          <div className="field">
            <label>Case Title</label>
            <input
              type="text"
              placeholder="e.g., Child Custody Dispute in Lahore"
              value={caseTitle}
              onChange={(e) => setCaseTitle(e.target.value)}
            />
          </div>

          {/* Category locked to Family Disputes */}
          <div className="field">
            <label>Case Category</label>
            <select
              value="Family Disputes"
              disabled
              style={{
                width: '100%', padding: '10px', borderRadius: 4,
                border: '1px solid #ccc', backgroundColor: '#f5f5f5',
                color: '#555', cursor: 'not-allowed',
              }}
            >
              <option>Family Disputes</option>
            </select>
            <small style={{ color: '#888' }}>
              Only Family Disputes are supported for case matching at this time.
            </small>
          </div>

          <div className="field">
            <label>Detailed Description</label>
            <textarea
              rows="7"
              placeholder="Describe the facts of your case in detail — who is involved, what happened, what relief you are seeking, and any key dates or agreements. (Min 30 chars)"
              value={caseDescription}
              onChange={(e) => setCaseDescription(e.target.value)}
            />
          </div>

          <h4 style={{ marginTop: 30, marginBottom: 20 }}>2. Supporting Document (Optional)</h4>
          <div className="field">
            <div
              className={`file-drop-zone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={triggerFileInput}
            >
              <UploadIcon />
              <p>Drag & drop a file here</p>
              <span>or click to browse (PDF or Word Doc)</span>
            </div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFileChange(e.target.files)}
              className="file-input-hidden"
              accept=".pdf,.doc,.docx"
            />
          </div>

          {files.length > 0 && (
            <div className="file-list">
              {files.map((file, idx) => (
                <div key={idx} className="file-list-item">
                  <div className="file-list-item-info">
                    <FileIcon />
                    <span className="file-name">{file.name}</span>
                  </div>
                  <span className="file-size">
                    ({(file.size / 1024).toFixed(1)} KB)
                    <button
                      type="button"
                      className="file-remove-btn"
                      onClick={() => handleRemoveFile(file.name)}
                    >&times;</button>
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="action" style={{ marginTop: 24 }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSearching}
              style={{ width: '100%' }}
            >
              {isSearching
                ? '🔍 Searching past cases with AI…'
                : '🔍 Find Similar Cases'}
            </button>
          </div>

          {message && (
            <p style={{
              marginTop: 14,
              fontWeight: 'bold',
              color: message.startsWith('Error') ? '#e74c3c' : '#555',
            }}>
              {message}
            </p>
          )}
        </form>
      </div>

      {/* ── Results ── */}
      {results && (
        <div style={s.sectionWrapper} className="fade-in-up">
          <h3 style={{ color: '#2c3e50', marginTop: 0, marginBottom: 6 }}>
            📂 Similar Past Cases
          </h3>
          <p style={{ color: '#777', marginBottom: 24, fontSize: '0.9rem' }}>
            {results.message}
          </p>

          {results.top_matches.length === 0 ? (
            <div style={s.noResults}>
              <p style={{ fontSize: '1.1rem', margin: 0 }}>
                No similar cases were found in our database.
              </p>
              <p style={{ marginTop: 8, fontSize: '0.9rem' }}>
                Try adding more detail to your case description to improve matching.
              </p>
            </div>
          ) : (
            results.top_matches.map((match, idx) => (
              <div key={idx} style={s.resultCard}>

                {/* Similarity ring — always green */}
                <SimilarityRing pct={match.similarity_percentage} />

                {/* Card body */}
                <div style={s.cardBody}>
                  <div style={{ marginBottom: 6 }}>
                    <div style={s.caseLabel}>📄 {match.case_label}</div>
                    <div style={s.sourceFile}>Source file: {match.source_file}</div>
                    <RelevanceBadge relevance={match.relevance} />
                  </div>
                  <p style={s.explanation}>{match.explanation}</p>
                </div>

              </div>
            ))
          )}
        </div>
      )}

    </div>
  );
}

export default CaseMatching;