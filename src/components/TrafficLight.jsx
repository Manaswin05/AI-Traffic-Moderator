import React from 'react'
import './TrafficLight.css'

function TrafficLight({ signal }) {
  return (
    <div className="traffic-light-container">
      <div className="traffic-light">
        <div className={`light red ${signal === 'red' ? 'active' : ''}`}></div>
        <div className={`light yellow ${signal === 'yellow' ? 'active' : ''}`}></div>
        <div className={`light green ${signal === 'green' ? 'active' : ''}`}></div>
      </div>
      <div className="traffic-status">
        Current Signal
        <span style={{ 
          color: signal === 'red' ? '#ef4444' : signal === 'yellow' ? '#fbbf24' : '#10b981',
          textTransform: 'uppercase',
          fontWeight: '800',
          letterSpacing: '1px'
        }}>
          {signal}
        </span>
      </div>
    </div>
  )
}

export default TrafficLight
