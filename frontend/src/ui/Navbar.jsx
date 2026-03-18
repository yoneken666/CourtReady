import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { AuthContext } from '../services/auth.jsx';
import Emblem from './Emblem';

function Navbar() {
    const { token, logout } = useContext(AuthContext);

    return (
        <header className="navbar-main">
            <div className="container navbar-container">
                <div className="brand">
                    <Emblem />
                    <h1>CourtReady</h1>
                </div>
                <nav>
                    <NavLink to="/">Home</NavLink>
                    <NavLink to="/case-intake">Case Analyzer</NavLink>
                    <NavLink to="/case-matching">Case Matcher</NavLink>
                    <NavLink to="/argument-builder">Argument Builder</NavLink>
                    <NavLink to="/document-assistant">Document Assistant</NavLink>
                    <NavLink to="/simulation">Simulation Mode</NavLink>

                    {token ? (
                        <button onClick={logout} className="btn-nav-logout">
                            Logout
                        </button>
                    ) : (
                        <>
                            <NavLink to="/login">Login</NavLink>
                            <NavLink to="/signup">Sign Up</NavLink>
                        </>
                    )}
                </nav>
            </div>
        </header>
    );
}

export default Navbar;
