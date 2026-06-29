import React from 'react'
import { Link } from 'react-router-dom'
import './Header.css'

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <Link to="/" className="logo">
          <span className="logo-icon">🚦</span>
          <span className="logo-text">Smart Traffic AI</span>
        </Link>
        
        <nav className="nav">
          <Link to="/dashboard" className="nav-link">Dashboard</Link>
          <Link to="/map" className="nav-link">Map</Link>
        </nav>
      </div>
    </header>
  )
}

export default Header
