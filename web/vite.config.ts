/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// The built UI ships inside the Python package, served by FastAPI.
// `npm run dev` proxies /api to the server started with `uv run hotas-kneeboard --no-browser`.
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../hotas_kneeboard/web',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8642' },
  },
  test: {
    environment: 'jsdom',
  },
})
