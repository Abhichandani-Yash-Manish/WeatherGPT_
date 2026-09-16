import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

/* The build lands in web/dist and is served by the loopback workspace server, which injects the
   session token into the built HTML. No CDN, no inline script: the CSP keeps script-src self and the
   audit reads the served bundle, so the manifest is emitted for hash-checking. */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { fs: { allow: ['..'] } },
  build: {
    outDir: '../web/dist',
    emptyOutDir: true,
    manifest: true,
    assetsInlineLimit: 0,
    sourcemap: false,
    rollupOptions: {
      input: { main: 'index.html' },
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
        },
      },
    },
  },
});
