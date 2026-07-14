import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Sidebar.css'

function Sidebar() {
  const { pathname } = useLocation()

  const mainTabs = [
    { to: '/dashboard', icon: 'dashboard',    label: 'Monitor',   fill: true },
    { to: '/analytics', icon: 'query_stats',  label: 'Analytics' },
    { to: '/map',       icon: 'map',          label: 'Map View' },
    { to: '/logs',      icon: 'terminal',     label: 'Sys Logs',   disabled: true },
  ]

  const footerTabs = [
    { icon: 'settings', label: 'Settings' },
    { icon: 'help',     label: 'Support' },
  ]

  return (
    <nav className="icon-sidebar">
      <div className="sb-brand">
        <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
          traffic
        </span>
      </div>

      <div className="sb-nav">
        {mainTabs.map(tab => {
          const isActive = pathname === tab.to
          if (tab.disabled) {
            return (
              <div key={tab.label} className="sb-tab" style={{ opacity: 0.4, cursor: 'default' }}>
                <span className="material-symbols-outlined">{tab.icon}</span>
                <span className="sb-tab-label">{tab.label}</span>
              </div>
            )
          }
          return (
            <Link key={tab.to} to={tab.to} className={`sb-tab${isActive ? ' active' : ''}`}>
              <span
                className="material-symbols-outlined"
                style={isActive && tab.fill ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                {tab.icon}
              </span>
              <span className="sb-tab-label">{tab.label}</span>
            </Link>
          )
        })}
      </div>

      <div className="sb-footer">
        {footerTabs.map(tab => (
          <div key={tab.label} className="sb-tab" style={{ opacity: 0.5, cursor: 'default' }}>
            <span className="material-symbols-outlined">{tab.icon}</span>
            <span className="sb-tab-label">{tab.label}</span>
          </div>
        ))}
      </div>
    </nav>
  )
}

export default Sidebar
