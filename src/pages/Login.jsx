import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Login.css'

function Login({ setIsAuthenticated }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    // Simple authentication - in production, validate against backend
    if (username && password) {
      setIsAuthenticated(true)
      navigate('/dashboard')
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="hero-section">
          <h1>AI-Powered Traffic Management</h1>
          <p>
            Experience the future of traffic control with real-time vehicle detection,
            intelligent signal management, and comprehensive analytics.
          </p>
          <div className="features">
            <div className="feature-item">
              <span className="feature-icon">🎯</span>
              <span>Real-time Vehicle Detection</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🤖</span>
              <span>AI-Powered Signal Control</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">📊</span>
              <span>Advanced Analytics Dashboard</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🗺️</span>
              <span>Interactive Traffic Maps</span>
            </div>
          </div>
        </div>

        <div className="login-card">
          <h2>Welcome Back</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="username">Username or Email</label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>
            <button type="submit" className="btn-login">
              Login
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
