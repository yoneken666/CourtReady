import React, { useState, useContext } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../services/auth.jsx';

function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useContext(AuthContext);
    const navigate = useNavigate();
    const location = useLocation();

    // Get the page the user was trying to access before being redirected
    const from = location.state?.from?.pathname || "/case-intake";

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await login(email, password);
            navigate(from, { replace: true }); // Send user back where they came from
        } catch (err) {
            // Updated error handling to show backend message
            if (err.response && err.response.data && err.response.data.detail) {
                setError(err.response.data.detail);
            } else {
                setError('Failed to log in. Please check your credentials.');
            }
        }
    };

    return (
        <div className="container">
            {/* Removed the extra <main> wrapper for consistency */}
            <div className="form fade-in-up">
                {/* Changed to h2 and added theme styling */}
                <h2 style={{ color: 'var(--olive)', textAlign: 'center' }}>Log In to Your Account</h2>
                <form onSubmit={handleSubmit}>
                    <div className="field">
                        <label htmlFor="email">Email Address</label>
                        <input
                            id="email"
                            type="text"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@example.com"
                            required
                        />
                    </div>
                    <div className="field">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                        />
                    </div>
                    {error && <p style={{ color: 'red', textAlign: 'center' }}>{error}</p>}
                    <div className="action">
                        <button type="submit" className="btn btn-primary">Log In</button>
                    </div>
                </form>
                {/* Updated styling to match SignupPage.jsx */}
                <p style={{ textAlign: 'center', marginTop: '16px' }}>
                    Don't have an account? <Link to="/signup" style={{ color: 'var(--olive)' }}>Sign Up</Link>
                </p>
            </div>
        </div>
    );
}
export default LoginPage;

