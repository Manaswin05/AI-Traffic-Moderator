import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy API calls to Flask backend during local development
    proxy: {
      '/video_feed': 'http://localhost:5000',
      '/traffic_status': 'http://localhost:5000',
      '/set_video_source': 'http://localhost:5000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
