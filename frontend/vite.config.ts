import { defineConfig } from 'vite';

export default defineConfig({
  // Ensure globe.gl (CJS/UMD) is pre-bundled correctly by Vite
  optimizeDeps: {
    include: ['globe.gl', 'three', 'topojson-client'],
  },
  // Proxy API calls so we avoid CORS entirely in dev
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
});
