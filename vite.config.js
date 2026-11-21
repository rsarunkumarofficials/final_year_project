import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'website',
    // Keep the build output free of stale hashed bundles from older builds.
    emptyOutDir: true,
    assetsDir: 'assets',
    sourcemap: false,
  },
});
