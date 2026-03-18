import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/session': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,   // proxy WebSocket upgrades too
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../api/static',
    emptyOutDir: true,
  },
});
