import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Build trafia do frontend/dist i jest serwowany przez Django (index.html) oraz nginx (/static/spa/ po collectstatic).
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/spa/' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000', '/admin': 'http://127.0.0.1:8000', '/static/admin': 'http://127.0.0.1:8000' },
  },
  build: { outDir: 'dist', emptyOutDir: true },
}))
