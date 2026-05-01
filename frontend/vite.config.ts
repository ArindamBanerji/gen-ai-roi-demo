import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load root .env (one level up from frontend/) — BACKEND_PORT is written
  // by uvicorn on every startup, so the proxy always follows the backend.
  const env = loadEnv(mode, '../', '')
  const backendPort = env.BACKEND_PORT || '8001'
  const s2pBackendPort = env.S2P_BACKEND_PORT || '8002'
  const frontendPort = parseInt(env.FRONTEND_PORT || '5173')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: frontendPort,
      host: true, // Allow all hosts (needed for ngrok)
      allowedHosts: ['.ngrok-free.app', '.ngrok.io', 'localhost'], // Allow ngrok domains
      proxy: {
        '/api/s2p/preview': {
          target: `http://localhost:${s2pBackendPort}`,
          changeOrigin: true,
        },
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
