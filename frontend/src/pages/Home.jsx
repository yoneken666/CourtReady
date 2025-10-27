import React, { useContext } from 'react'; // 1. Import useContext
import { NavLink } from 'react-router-dom';
import Emblem from '../ui/Emblem';
import { AuthContext } from '../services/auth.jsx'; // 2. Import AuthContext

// This is the Home/Landing Page
function Home() {
  const { token } = useContext(AuthContext); // 3. Get token status
  const destination = token ? "/case-intake" : "/login"; // 4. Set dynamic destination

  return (
    <div className="container">
      {/* The <header> component was removed from here to fix the double navbar */}

      <div className="hero fade-in-up">
        <div className="hero-left">
          <h2>Welcome to CourtReady</h2>
          <p>
            Your AI-powered legal assistant for understanding case law,
            drafting documents, and preparing for court with confidence.
          </p>
          <div className="cta-row">
            {/* 5. Apply dynamic destination to the button */}
            <NavLink to={destination} className="btn btn-primary">
              Analyze a Case
            </NavLink>
            <NavLink to="/simulation" className="btn btn-outline">
              Start the Simulation
            </NavLink>
          </div>
        </div>
        <div className="emblem-container fade-in-up delay-1">
          <Emblem />
        </div>
      </div>

      {/* Added "Key Features" heading */}
      <h2 style={{ marginTop: '40px', color: 'var(--olive)' }} className="fade-in-up delay-1">
        Key Features
      </h2>

      <div className="grid features">
        <div className="card fade-in-up delay-2">
          <svg className="feature-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
          <h4>Case Analyzer</h4>
          <p>Upload your case files and get an AI-powered breakdown of key facts, legal issues, and precedents.</p>
        </div>
        <div className="card fade-in-up delay-3">
          <svg className="feature-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          <h4>Document Assistant</h4>
          <p>Draft professional legal documents like complaints, motions, and affidavits with AI guidance.</p>
        </div>
        <div className="card fade-in-up delay-4">
          <svg className="feature-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
          <h4>Simulation Mode</h4>
          <p>Practice your arguments in a realistic courtroom simulation and receive instant feedback.</p>
        </div>

        {/* Restored "AI Case Matching" feature card */}
        <div className="card fade-in-up delay-5">
          <svg className="feature-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
          <h4>AI Case Matching</h4>
          <p>Find relevant past cases and precedents that match the unique details of your situation.</p>
        </div>
      </div>

      <div className="watermark">
        <Emblem />
      </div>

      <footer>
        CourtReady FYP - All Rights Reserved © 2025
      </footer>
    </div>
  );
}

export default Home;

