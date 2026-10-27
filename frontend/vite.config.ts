import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'
const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // API_KEY is injected here, server-side, so it never ships in the browser bundle.
      '/api': { target: process.env.API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true, headers: process.env.API_KEY ? { 'x-api-key': process.env.API_KEY } : {} },
      '/health': { target: process.env.API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})