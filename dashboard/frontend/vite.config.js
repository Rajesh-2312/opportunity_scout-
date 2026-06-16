import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Builds to ../static so the FastAPI server serves the app on http://localhost:8000
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
