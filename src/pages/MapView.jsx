import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './MapView.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function MapView() {
  const position = [18.5074, 73.8077]

  return (
    <>
      <div className="map-header">
        <div>
          <h2 className="map-title">Map View</h2>
          <p className="map-subtitle">Traffic camera deployment · Kothrud, Pune</p>
        </div>
      </div>

      <div className="data-card map-panel">
        <div className="map-panel-bar">
          <span className="material-symbols-outlined">map</span>
          <span className="map-panel-label">Live Traffic Map</span>
        </div>
        <div className="map-inner">
          <MapContainer center={position} zoom={14} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={position}>
              <Popup>
                <strong>CAM-01</strong><br />
                Kothrud, Pune, India
              </Popup>
            </Marker>
          </MapContainer>
        </div>
      </div>
    </>
  )
}

export default MapView
