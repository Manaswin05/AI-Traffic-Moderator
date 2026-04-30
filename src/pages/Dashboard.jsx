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
    vehicle_count: 0
  })

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
        const response = await axios.get('/traffic_status')
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

  return (
    <div className="dashboard">
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
                <span className="stat-icon">⏱️</span>
                <div className="stat-info">
                  <span className="stat-label">Status</span>
                  <span className="stat-value">Active</span>
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
