import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import TrafficLight from '../components/TrafficLight'
import './Dashboard.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

function Dashboard() {
  const [trafficData, setTrafficData] = useState({
    traffic_light: 'red',
    vehicle_count: 0,
    ml_trained: false,
    samples_collected: 0,
    min_samples_required: 15
  })

  const [notification, setNotification] = useState({ show: false, message: '', type: '' })

  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [
      {
        label: 'Vehicle Count',
        data: [],
        borderColor: 'rgb(102, 126, 234)',
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        tension: 0.4,
        fill: true
      }
    ]
  })

  useEffect(() => {
    const fetchTrafficStatus = async () => {
      try {
        const response = await axios.get('/api/traffic_status')
        setTrafficData(response.data)
        
        // Update chart data
        const currentTime = new Date().toLocaleTimeString()
        setChartData(prevData => {
          const newLabels = [...prevData.labels, currentTime]
          const newData = [...prevData.datasets[0].data, response.data.vehicle_count]
          
          // Keep only last 20 data points
          if (newLabels.length > 20) {
            newLabels.shift()
            newData.shift()
          }
          
          return {
            labels: newLabels,
            datasets: [
              {
                ...prevData.datasets[0],
                data: newData
              }
            ]
          }
        })
      } catch (error) {
        console.error('Error fetching traffic status:', error)
      }
    }

    fetchTrafficStatus()
    const interval = setInterval(fetchTrafficStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          font: {
            size: 12,
            weight: '600'
          },
          padding: 15,
          usePointStyle: true
        }
      },
      title: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: {
          size: 14,
          weight: 'bold'
        },
        bodyFont: {
          size: 13
        },
        cornerRadius: 8
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Number of Vehicles',
          font: {
            size: 13,
            weight: '600'
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          font: {
            size: 11
          }
        }
      },
      x: {
        title: {
          display: true,
          text: 'Time',
          font: {
            size: 13,
            weight: '600'
          }
        },
        grid: {
          display: false
        },
        ticks: {
          font: {
            size: 10
          },
          maxRotation: 45,
          minRotation: 45
        }
      }
    }
  }

  const showNotification = (message, type = 'info') => {
    setNotification({ show: true, message, type })
    setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000)
  }

  const handleTrainModel = async () => {
    try {
      const response = await axios.post('/api/train_model')
      showNotification(response.data.message, 'success')
    } catch (error) {
      showNotification(error.response?.data?.message || 'Training failed', 'error')
    }
  }

  const handleResetModel = async () => {
    if (!window.confirm('Are you sure you want to reset the ML model? This will clear all collected data.')) {
      return
    }
    
    try {
      const response = await axios.post('/api/reset_model')
      showNotification(response.data.message, 'success')
    } catch (error) {
      showNotification(error.response?.data?.message || 'Reset failed', 'error')
    }
  }

  return (
    <div className="dashboard">
      {notification.show && (
        <div className={`notification notification-${notification.type}`}>
          {notification.message}
        </div>
      )}
      
      <div className="container">
        <h1 className="page-title">Live Traffic Dashboard</h1>
        
        <div className="dashboard-grid">
          <div className="main-content">
            <div className="card video-card">
              <h2>Live Camera Feed</h2>
              <div className="signal-above-video">
                <TrafficLight signal={trafficData.traffic_light} />
              </div>
              <div className="video-container">
                <img 
                  src="/video_feed" 
                  alt="Live Traffic Feed" 
                  className="video-feed"
                />
              </div>
            </div>
          </div>

          <div className="sidebar">
            <div className="card stats-card">
              <h3>Traffic Statistics</h3>
              <div className="stat-item">
                <span className="stat-icon">🚗</span>
                <div className="stat-info">
                  <span className="stat-label">Vehicle Count</span>
                  <span className="stat-value">{trafficData.vehicle_count}</span>
                </div>
              </div>
              <div className="stat-item">
                <span className="stat-icon">🤖</span>
                <div className="stat-info">
                  <span className="stat-label">ML Status</span>
                  <span className={`stat-value ${trafficData.ml_trained ? 'trained' : 'learning'}`}>
                    {trafficData.ml_trained ? '✓ Trained' : `Learning ${trafficData.samples_collected}/${trafficData.min_samples_required}`}
                  </span>
                </div>
              </div>
              <div className="stat-item">
                <span className="stat-icon">⏱️</span>
                <div className="stat-info">
                  <span className="stat-label">Status</span>
                  <span className="stat-value">Active</span>
                </div>
              </div>
            </div>

            <div className="card ml-controls-card">
              <h3>🧠 ML Controls</h3>
              <div className="ml-controls">
                <button 
                  className="control-btn train-btn"
                  onClick={handleTrainModel}
                  disabled={trafficData.samples_collected < 5}
                  title={trafficData.samples_collected < 5 ? 'Need at least 5 samples' : 'Train model now'}
                >
                  🎯 Train Model Now
                </button>
                <button 
                  className="control-btn reset-btn"
                  onClick={handleResetModel}
                  title="Reset and start fresh"
                >
                  🔄 Reset & Start Fresh
                </button>
                <div className="ml-info">
                  <small>
                    {trafficData.ml_trained 
                      ? `✓ Model trained with ${trafficData.samples_collected} samples` 
                      : `Collecting data... ${trafficData.samples_collected}/${trafficData.min_samples_required} samples`}
                  </small>
                </div>
              </div>
            </div>

            <div className="card chart-card">
              <h3>Vehicle Count Over Time</h3>
              <div className="chart-container">
                <Line data={chartData} options={chartOptions} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
