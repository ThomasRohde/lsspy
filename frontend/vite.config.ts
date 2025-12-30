import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    }
  },
  build: {
    cssCodeSplit: false,
    assetsInlineLimit: 100000000, // Inline all assets
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      }
    }
  }
})
