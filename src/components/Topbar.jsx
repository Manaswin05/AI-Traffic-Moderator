import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Topbar.css'

function Topbar() {
  const { pathname } = useLocation()

  return (
    <header className="topbar">
      {/* Left */}
      <div className="topbar-left">
        <span className="topbar-brand">Traffic Control Center</span>
        <span className="topbar-live">
          <span className="pulse-dot" />
          LIVE
        </span>
      </div>

      {/* Center nav — real pages only */}
      <nav className="topbar-nav">
        <Link to="/dashboard" className={`topbar-link${pathname === '/dashboard' ? ' active' : ''}`}>
          Dashboard
        </Link>
        <Link to="/analytics" className={`topbar-link${pathname === '/analytics' ? ' active' : ''}`}>
          Analytics
        </Link>
        <Link to="/map" className={`topbar-link${pathname === '/map' ? ' active' : ''}`}>
          Map
        </Link>
      </nav>

      {/* Right */}
      <div className="topbar-right">
        <span className="topbar-status">SYSTEM_STATUS: OK</span>
        <button className="topbar-icon-btn">
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button className="topbar-icon-btn">
          <span className="material-symbols-outlined">account_circle</span>
        </button>
      </div>
    </header>
  )
}

export default Topbar
