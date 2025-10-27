import React, { useState, useRef } from 'react';
import { createCase, uploadDocuments } from '../services/api';

// Reusable FileIcon component
function FileIcon() {
  return (
    <svg className="file-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

// Reusable UploadIcon component
function UploadIcon() {
  return (
    <svg className="file-drop-zone-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
    </svg>
  );
}


function CaseIntake() {
  const [caseTitle, setCaseTitle] = useState('');
  const [caseType, setCaseType] = useState('');
  const [caseDescription, setCaseDescription] = useState('');
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  // Ref for the hidden file input
  const fileInputRef = useRef(null);

  // --- BUG FIX ---
  // The 'e.g.value' was a critical error.
  // It has been corrected to 'e.target.value'.
  // ---

  const handleFileChange = (newFiles) => {
    // Combine new files with existing, avoiding duplicates
    setFiles((prevFiles) => {
      const existingFileNames = new Set(prevFiles.map(f => f.name));
      const filteredNewFiles = Array.from(newFiles).filter(
        (file) => !existingFileNames.has(file.name)
      );
      return [...prevFiles, ...filteredNewFiles];
    });
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const droppedFiles = event.dataTransfer.files;
    if (droppedFiles.length) {
      handleFileChange(droppedFiles);
    }
  };

  const handleRemoveFile = (fileName) => {
    setFiles(files.filter(file => file.name !== fileName));
  };

  // Triggers the hidden file input
  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('Submitting case details...');

    // 1. Submit text data
    const caseDetails = { caseTitle, caseType, caseDescription };
    try {
      const textResponse = await createCase(caseDetails);
      console.log('Case details submitted:', textResponse);

      // 2. If text submission is successful and files exist, upload files
      if (files.length > 0) {
        setMessage('Uploading documents...');
        const formData = new FormData();
        files.forEach((file) => {
          formData.append('files', file);
        });

        const fileResponse = await uploadDocuments(formData);
        console.log('Files uploaded:', fileResponse);
        setMessage('Case and documents submitted successfully!');
      } else {
        setMessage('Case details submitted successfully!');
      }

      // Clear the form
      setCaseTitle('');
      setCaseType('');
      setCaseDescription('');
      setFiles([]);

    } catch (error) {
      console.error('Submission error:', error);
      if (error.response && error.response.status === 401) {
         setMessage('Error: You are not authorized. Please log in again.');
      } else {
         setMessage(`Error: ${error.message}. Please try again.`);
      }
    }
  };

  return (
    <div className="container">
      <div className="hero fade-in-up">
        <div className="hero-left">
          <h2>Case Analyzer</h2>
          <p>
            Provide details about your case and upload any relevant documents.
            Our AI will analyze the information to provide you with a strategic
            roadmap.
          </p>
        </div>
      </div>

      {/* This structure uses the .card and .form classes on the
        outer wrapper, as defined in your App.css file.
      */}
      <div className="card form fade-in-up delay-1">
        <form onSubmit={handleSubmit}>

          <div className="field">
            <label style={{ color: 'var(--olive)' }}>Case Name</label>
            <input
              type="text"
              placeholder="e.g., Land Dispute in Sector G-11"
              value={caseTitle}
              onChange={(e) => setCaseTitle(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label style={{ color: 'var(--olive)' }}>Case type</label>
            <input
              type="text"
              placeholder="e.g., Civil, Family, Property"
              value={caseType}
              onChange={(e) => setCaseType(e.target.value)}
              required
            />
          </div>
          <div className="field">
              <label style={{ color: 'var(--olive)' }}>Case Description</label>
            <textarea
              rows="6"
              placeholder="Briefly describe the situation, key events, and what you are seeking."
              value={caseDescription}
              onChange={(e) => setCaseDescription(e.target.value)}
              required
            ></textarea>
          </div>

          <h4 style={{ marginTop: '10px', marginBottom: '20px' }}>Upload Documents</h4>
          <div className="field">
            {/* New Drag and Drop Zone */}
            <div
              className={`file-drop-zone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={triggerFileInput} // Click to upload
            >
              <UploadIcon />
              <p>Drag & drop files here</p>
              <span>or click to browse (PDFs, images, etc.)</span>
            </div>
            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFileChange(e.target.files)}
              multiple
              className="file-input-hidden"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            />
          </div>

          {/* New, styled file list */}
          {files.length > 0 && (
            <div className="file-list">
              {files.map((file, index) => (
                <div key={index} className="file-list-item">
                  <div className="file-list-item-info">
                    <FileIcon />
                    <span className="file-name">{file.name}</span>
                  </div>
                  <span classNameG="file-size">
                    ({(file.size / 1024).toFixed(1)} KB)
                    <button
                      type="button"
                      className="file-remove-btn"
                      onClick={() => handleRemoveFile(file.name)}
                      title="Remove file"
                    >
                      &times;
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="action">
            <button type="submit" className="btn btn-primary">
              Analyze Case
            </button>
          </div>

          {message && <p style={{ marginTop: '15px', fontWeight: '500', color: message.startsWith('Error') ? 'red' : 'var(--olive)' }}>{message}</p>}
        </form>
      </div>

      <footer>
        CourtReady FYP - All Rights Reserved © 2025
      </footer>
    </div>
  );
}

export default CaseIntake;

