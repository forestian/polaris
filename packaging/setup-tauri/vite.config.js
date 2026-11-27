import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Tauri 프론트엔드. dev 서버 고정 포트(미리보기/검증용).
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1430, strictPort: true },
  build: { outDir: 'dist', emptyOutDir: true },
})
