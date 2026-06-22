import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? '/OMNI_AGENT/' : '/',
  server: {
    port: 5173,
    host: true
  }
}))
