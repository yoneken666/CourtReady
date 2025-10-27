import React from 'react';
import { useLocation } from 'react-router-dom';

function Placeholder() {
    const location = useLocation();
    // Extract a readable name from the pathname (e.g., '/document-assistant' -> 'Document Assistant')
    const featureName = location.pathname
        .substring(1) // Remove leading slash
        .split('-') // Split by hyphen
        .map(word => word.charAt(0).toUpperCase() + word.slice(1)) // Capitalize each word
        .join(' '); // Join back with spaces

    return (
        <div className="container fade-in-up">
            {/* The redundant <header> was removed from here */}

            <div className="card" style={{ marginTop: '20px', textAlign: 'center', padding: '40px' }}>
                <h3 style={{ color: 'var(--olive)', marginBottom: '10px' }}>Coming Soon!</h3>
                <p style={{ color: 'var(--muted)' }}>
                    The "{featureName}" feature is currently under construction.
                </p>
            </div>

            <footer style={{ marginTop: '30px' }}>
                CourtReady FYP - All Rights Reserved © 2025
            </footer>
        </div>
    );
}

export default Placeholder;

