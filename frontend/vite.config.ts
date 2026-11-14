/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev only: forward same-origin /api calls to the local FastAPI app.
// Override with PERIGEE_API_PROXY=http://127.0.0.1:8001 when another server owns 8000.
const apiTarget = process.env.PERIGEE_API_PROXY ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': { target: apiTarget, changeOrigin: false } },
  },
  preview: {
    proxy: { '/api': { target: apiTarget, changeOrigin: false } },
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
});
