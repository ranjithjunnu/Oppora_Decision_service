import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const proxy = {
    '/api': {
      target: env.BACKEND_URL || 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (path: string) => path.replace(/^\/api/, ''),
      timeout: 180_000,
      proxyTimeout: 180_000,
    },
  };
  return { plugins: [react()], server: { port: 5173, strictPort: true, proxy }, preview: { port: 4173, strictPort: true, proxy } };
});
