        import React, { createContext, useState, useEffect } from 'react';
        import { loginUser } from './api';

        export const AuthContext = createContext(null);

        export const AuthProvider = ({ children }) => {
            const [token, setToken] = useState(null);
            const [loading, setLoading] = useState(true);

            useEffect(() => {
                // Check if token exists in localStorage on app load
                const storedToken = localStorage.getItem('token');
                if (storedToken) {
                    setToken(storedToken);
                }
                setLoading(false);
            }, []);

            const login = async (email, password) => {
                try {
                    const data = await loginUser(email, password);
                    setToken(data.access_token);
                    localStorage.setItem('token', data.access_token);
                } catch (error) {
                    // Clear token on failed login
                    localStorage.removeItem('token');
                    setToken(null);
                    throw error; // Re-throw error to be caught by LoginPage
                }
            };

            const logout = () => {
                setToken(null);
                localStorage.removeItem('token');
            };

            // We return 'loading' so ProtectedRoute can wait
            // until we've checked localStorage for a token.
            return (
                <AuthContext.Provider value={{ token, login, logout, loading }}>
                    {children}
                </AuthContext.Provider>
            );
        };


