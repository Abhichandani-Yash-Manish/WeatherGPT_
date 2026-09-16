import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

/* The CSP probe is a development page, not a product surface: it has its own config so it cannot
   enter the production input list. Build it with: npm run build:probe  (output web/dist-probe). */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { fs: { allow: ['..'] } },
  build: {
    outDir: '../web/dist-probe',
    emptyOutDir: true,
    assetsInlineLimit: 0,
    rollupOptions: { input: { probe: 'probe.html' } },
  },
});
