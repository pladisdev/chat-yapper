import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Load environment variables
const backendPort = process.env.PORT || 8000
const frontendPort = process.env.FRONTEND_PORT || 5173

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: parseInt(frontendPort),
    proxy: {
      '/api': `http://localhost:${backendPort}`,
      '/ws': {
        target: `ws://localhost:${backendPort}`,
        ws: true,
      },
      '/audio': `http://localhost:${backendPort}`,
    },
  },
})