import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCase, uploadDocuments, analyzeCase } from '../services/api';

function FileIcon() {
  return (
    <svg className="file-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="24" height="24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg className="file-drop-zone-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="48" height="48">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
    </svg>
  );
}

function CaseIntake() {
  const navigate = useNavigate();

  const [caseTitle, setCaseTitle] = useState('');
  const [caseType, setCaseType] = useState('Contract Disputes');
  const [caseDescription, setCaseDescription] = useState('');
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const fileInputRef = useRef(null);

  const allowedCategories = [
    "Contract Disputes",
    "Property Disputes",
    "Family Disputes"
  ];

  // --- FILE HANDLING ---
  const handleFileChange = (newFiles) => {
    setFiles((prevFiles) => {
      const existingFileNames = new Set(prevFiles.map(f => f.name));
      const filteredNewFiles = Array.from(newFiles).filter(
        (file) => !existingFileNames.has(file.name)
      );
      return [...prevFiles, ...filteredNewFiles];
    });
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) handleFileChange(e.dataTransfer.files);
  };
  const handleRemoveFile = (fileName) => setFiles(files.filter(f => f.name !== fileName));
  const triggerFileInput = () => fileInputRef.current.click();

  // --- ANALYSIS LOGIC ---
  const handleAnalyze = async (e) => {
    e.preventDefault();
    setIsAnalyzing(true);
    setMessage('');
    setAnalysisResult(null);

    // Allow analysis if text exists OR if a file is uploaded
    if (caseDescription.length < 10 && files.length === 0) {
        setMessage("Error: Please provide a description or upload a document to analyze.");
        setIsAnalyzing(false);
        return;
    }

    try {
        const formData = new FormData();
        formData.append('caseTitle', caseTitle);
        formData.append('caseType', caseType);
        formData.append('caseDescription', caseDescription);

        // Task 3: Attach the first file for analysis if present
        if (files.length > 0) {
            formData.append('file', files[0]);
        }

        const response = await analyzeCase(formData);

        if (response.validity_status === "REJECTED") {
            setMessage("Case Analysis Rejected: Input does not match the selected category.");
        }

        setAnalysisResult(response);
    } catch (err) {
        console.error("Analysis failed", err);
        setMessage(`Analysis Error: ${err.message || "Failed to analyze case."}`);
    } finally {
        setIsAnalyzing(false);
    }
  };

  const handleSaveAndProceed = async () => {
    setMessage('Saving case and uploading documents...');
    try {
      const caseDetails = { caseTitle, caseType, caseDescription };
      const caseResponse = await createCase(caseDetails);
      if (files.length > 0) {
        await uploadDocuments(caseResponse.id, files);
      }
      setMessage('Case saved successfully! Redirecting...');
      setTimeout(() => navigate('/'), 1500);
    } catch (error) {
      setMessage(`Error: ${error.message}. Please try again.`);
    }
  };

  // --- STYLES ---
  const styles = {
    resultBox: {
      backgroundColor: '#fff',
      padding: '2rem',
      borderRadius: '8px',
      marginTop: '2rem',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      borderTop: '4px solid #0056b3'
    },
    heading: {
      color: '#2c3e50',
      marginBottom: '1rem',
      borderBottom: '2px solid #ecf0f1',
      paddingBottom: '0.5rem'
    },
    subHeading: {
      fontSize: '1.1rem',
      fontWeight: 'bold',
      color: '#34495e',
      marginTop: '1.5rem',
      marginBottom: '0.5rem'
    },
    badge: {
      display: 'inline-block',
      padding: '0.5rem 1rem',
      borderRadius: '4px',
      fontWeight: 'bold',
      fontSize: '0.9rem',
      marginRight: '1rem',
      backgroundColor: '#ecf0f1',
      color: '#2c3e50'
    },
    badgeGreen: { backgroundColor: '#d4edda', color: '#155724', border: '1px solid #c3e6cb' },
    badgeYellow: { backgroundColor: '#fff3cd', color: '#856404', border: '1px solid #ffeeba' },
    badgeRed: { backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb' },
    list: { paddingLeft: '20px', color: '#555' },
    adviceBox: {
      backgroundColor: '#e8f4fd',
      padding: '1.5rem',
      borderRadius: '6px',
      borderLeft: '4px solid #3498db',
      marginTop: '1rem'
    },
    // Task 2: Style for Simplified Advice
    simplifiedBox: {
      backgroundColor: '#f0f9f4',
      padding: '1.5rem',
      borderRadius: '6px',
      borderLeft: '4px solid #27ae60',
      marginTop: '1rem'
    },
    // Task 1: Render newlines as paragraphs
    formattedText: {
        whiteSpace: 'pre-line',
        color: '#2c3e50',
        lineHeight: '1.6'
    }
  };

  const getStatusStyle = (status) => {
    if (!status) return styles.badge;
    const s = status.toLowerCase();
    if (s.includes("high") || s.includes("strong")) return { ...styles.badge, ...styles.badgeGreen };
    if (s.includes("moderate")) return { ...styles.badge, ...styles.badgeYellow };
    if (s.includes("rejected") || s.includes("error") || s.includes("weak")) return { ...styles.badge, ...styles.badgeRed };
    return styles.badge;
  };

  return (
    <div className="container">
      <div className="hero fade-in-up">
        <div className="hero-left">
          <h2>Case Analyzer & Intake</h2>
          <p>
            Describe your dispute or upload a document to let our AI check its validity against Pakistani Law.
            Once analyzed, you can save the case and proceed.
          </p>
        </div>
      </div>

      <div className="card form fade-in-up delay-1">
        <form>
          <h4 style={{ marginBottom: '20px' }}>1. Case Details</h4>

          <div className="field">
            <label>Case Title</label>
            <input
              type="text"
              placeholder="e.g., Tenant Eviction in Model Town"
              value={caseTitle}
              onChange={(e) => setCaseTitle(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label>Case Category (Restricted)</label>
            <select
              value={caseType}
              onChange={(e) => setCaseType(e.target.value)}
              required
              style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              {allowedCategories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <small style={{ color: '#666' }}>Only civil disputes are supported at this time.</small>
          </div>

          <div className="field">
            <label>Detailed Description</label>
            <textarea
              rows="6"
              placeholder="Describe the events chronologically. Who is involved? What agreements were broken? (Min 50 chars)"
              value={caseDescription}
              onChange={(e) => setCaseDescription(e.target.value)}
            ></textarea>
          </div>

          <h4 style={{ marginTop: '30px', marginBottom: '20px' }}>2. Supporting Documents (Upload for Analysis)</h4>
          <div className="field">
            <div
              className={`file-drop-zone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={triggerFileInput}
            >
              <UploadIcon />
              <p>Drag & drop files here</p>
              <span>or click to browse (PDFs, Word Docs)</span>
            </div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFileChange(e.target.files)}
              multiple
              className="file-input-hidden"
              accept=".pdf,.doc,.docx"
            />
          </div>

          {files.length > 0 && (
            <div className="file-list">
              {files.map((file, index) => (
                <div key={index} className="file-list-item">
                  <div className="file-list-item-info">
                    <FileIcon />
                    <span className="file-name">{file.name}</span>
                  </div>
                  <span className="file-size">
                    ({(file.size / 1024).toFixed(1)} KB)
                    <button type="button" className="file-remove-btn" onClick={() => handleRemoveFile(file.name)}>&times;</button>
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="action" style={{ display: 'flex', gap: '15px', marginTop: '20px' }}>
            <button
                onClick={handleAnalyze}
                className="btn btn-primary"
                disabled={isAnalyzing}
                style={{ flex: 1 }}
            >
              {isAnalyzing ? 'Analyzing with AI...' : 'Step 1: Analyze Case'}
            </button>
          </div>

          {message && <p style={{ marginTop: '15px', fontWeight: 'bold', color: message.includes('Error') || message.includes('Rejected') ? '#e74c3c' : '#27ae60' }}>{message}</p>}
        </form>
      </div>

      {analysisResult && (
        <div style={styles.resultBox} className="fade-in-up">
            <h3 style={styles.heading}>📋 AI Legal Analysis Report</h3>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
                <div style={getStatusStyle(analysisResult.validity_status)}>
                    Grounding: {analysisResult.validity_status}
                </div>
                {analysisResult.validity_status !== "REJECTED" && (
                    <div style={getStatusStyle(analysisResult.validity_assessment.risk_level)}>
                        Risk: {analysisResult.validity_assessment.risk_level}
                    </div>
                )}
            </div>

            <div>
                <h4 style={styles.subHeading}>Case Summary</h4>
                <p style={{ color: '#555', lineHeight: '1.6' }}>{analysisResult.case_summary}</p>
            </div>

            {analysisResult.key_facts.length > 0 && (
                <div>
                    <h4 style={styles.subHeading}>Key Facts Identified</h4>
                    <ul style={styles.list}>
                        {analysisResult.key_facts.map((fact, idx) => (
                            <li key={idx} style={{ marginBottom: '5px' }}>{fact}</li>
                        ))}
                    </ul>
                </div>
            )}

            {analysisResult.validity_status !== "REJECTED" && (
                <>
                    {/* Task 1: Strategic Advice (Formatted) */}
                    <div style={styles.adviceBox}>
                        <h4 style={{ ...styles.subHeading, marginTop: 0, color: '#0056b3' }}>⚖️ Strategic Advice</h4>
                        <div style={styles.formattedText}>
                            {analysisResult.validity_assessment.advice_summary}
                        </div>
                    </div>

                    {/* Task 2: Simplified Advice */}
                    <div style={styles.simplifiedBox}>
                        <h4 style={{ ...styles.subHeading, marginTop: 0, color: '#27ae60' }}>💡 Simply Put (For Laymen)</h4>
                        <p style={{ color: '#2c3e50', marginBottom: '0', fontSize: '1.05rem' }}>
                            {analysisResult.validity_assessment.simplified_advice}
                        </p>
                    </div>
                </>
            )}

            <div style={{ marginTop: '20px', paddingTop: '15px', borderTop: '1px solid #eee' }}>
                <h4 style={styles.subHeading}>Relevant Pakistani Laws</h4>
                {analysisResult.relevant_laws.length > 0 ? (
                    analysisResult.relevant_laws.map((law, idx) => (
                        <div key={idx} style={{ backgroundColor: '#f9f9f9', padding: '10px', marginBottom: '10px', borderLeft: '3px solid #ccc', fontSize: '0.9rem' }}>
                            <p style={{ fontStyle: 'italic', margin: 0 }}>"{law.source_text}"</p>
                            <div style={{ marginTop: '5px', fontSize: '0.8rem', color: '#777', fontWeight: 'bold' }}>
                                Match Score: {(law.relevance_score * 100).toFixed(1)}%
                            </div>
                        </div>
                    ))
                ) : (
                    <p style={{ color: '#999' }}>No specific legal precedents found.</p>
                )}
            </div>

            {analysisResult.validity_status !== "REJECTED" && (
                <div style={{ textAlign: 'right', marginTop: '30px' }}>
                    <button
                        onClick={handleSaveAndProceed}
                        className="btn btn-primary"
                        style={{ backgroundColor: '#2c3e50', borderColor: '#2c3e50', padding: '12px 24px' }}
                    >
                        Step 2: Save Case & Proceed
                    </button>
                </div>
            )}
        </div>
      )}

      <footer>
        CourtReady FYP - All Rights Reserved © 2025
      </footer>
    </div>
  );
}

export default CaseIntake;
