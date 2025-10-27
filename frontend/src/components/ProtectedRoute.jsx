import React, { useContext } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../services/auth.jsx';

function ProtectedRoute({ children }) {
    const { token, loading } = useContext(AuthContext);
    const location = useLocation();

    // If we are still checking if a token exists, show a loading message
    if (loading) {
        return <div>Loading...</div>;
    }

    if (!token) {
        // If no token, redirect to login page
        // 'state={{ from: location }}' saves the page they were trying to access
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return children; // If token exists, show the protected page
}

export default ProtectedRoute;
