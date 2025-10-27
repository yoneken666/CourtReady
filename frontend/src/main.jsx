import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
// Import AuthProvider from the renamed .jsx file
import { AuthProvider } from './services/auth.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* Wrap the entire App in the AuthProvider */}
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)

