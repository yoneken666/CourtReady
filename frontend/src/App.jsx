import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './ui/Navbar';
import Home from './pages/Home';
import CaseIntake from './pages/CaseIntake';
import Placeholder from './pages/Placeholder';

// Import the new pages
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ProtectedRoute from './components/ProtectedRoute'; // Import the protector

import './App.css';

function App() {
    return (
        <Router>
            <div className="App">
                <Navbar />
                <Routes>
                    {/* Public Routes */}
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/signup" element={<SignupPage />} />

                    {/* Protected Routes */}
                    <Route
                        path="/case-intake"
                        element={
                            <ProtectedRoute>
                                <CaseIntake />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/document-assistant"
                        element={
                            <ProtectedRoute>
                                <Placeholder pageName="Document Assistant" />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/simulation"
                        element={
                            <ProtectedRoute>
                                <Placeholder pageName="Simulation Mode" />
                            </ProtectedRoute>
                        }
                    />
                </Routes>
            </div>
        </Router>
    );
}

export default App;
