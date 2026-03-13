import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import './Header.css'

function Header({ isAuthenticated, setIsAuthenticated }) {
  const navigate = useNavigate()

  const handleLogout = () => {
    setIsAuthenticated(false)
    navigate('/')
  }

  return (
    <header className="header">
      <div className="header-content">
        <Link to="/" className="logo">
          <span className="logo-icon">🚦</span>
          <span className="logo-text">Smart Traffic AI</span>
        </Link>
        
        {isAuthenticated && (
          <nav className="nav">
            <Link to="/dashboard" className="nav-link">Dashboard</Link>
            <Link to="/map" className="nav-link">Map</Link>
            <button onClick={handleLogout} className="btn btn-logout">Logout</button>
          </nav>
        )}
      </div>
    </header>
  )
}

export default Header
