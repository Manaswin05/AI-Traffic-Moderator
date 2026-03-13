import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/video_feed': 'http://localhost:5000',
      '/traffic_status': 'http://localhost:5000'
    }
  }
})
