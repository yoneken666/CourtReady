import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signupUser } from "../services/api";

function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match!");
      return;
    }

    try {
      const user = await signupUser(email, password);
      console.log("Signup successful:", user);
      // Navigate to login page after successful signup
      navigate("/login");
    } catch (error) {
      console.error("Signup error:", error);

      // --- THIS IS THE UPDATED PART ---
      // Check if the error response from the backend has a 'detail' field
      if (error.response && error.response.data && error.response.data.detail) {
        // Display the specific error message from FastAPI
        setError(error.response.data.detail);
      } else {
        // Fallback to a generic error
        setError("Signup failed. Please try again.");
      }
    }
  };

  return (
    <div className="container">
      <div className="form fade-in-up">
        <h2 style={{ color: 'var(--olive)', textAlign: 'center' }}>Create Account</h2>
        <form onSubmit={handleSubmit}>
          {error && <p style={{ color: 'red', textAlign: 'center' }}>{error}</p>}
          <div className="field">
            <label>Email</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          <div className="action">
            <button type="submit" className="btn btn-primary">Sign Up</button>
          </div>
        </form>
        <p style={{ textAlign: 'center', marginTop: '16px' }}>
          Already have an account? <Link to="/login" style={{ color: 'var(--olive)' }}>Login here</Link>
        </p>
      </div>
    </div>
  );
}

export default SignupPage;

