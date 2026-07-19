import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Dev proxy so the UI can call /api/* → FastAPI on port 8000
      '/tasks': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/healing': 'http://localhost:8000',
      '/knowledge': 'http://localhost:8000',
      '/mcp': 'http://localhost:8000',
    },
  },
})
