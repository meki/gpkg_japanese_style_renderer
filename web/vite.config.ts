import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // FastAPI バックエンド (uv run uvicorn gpkg_jsr.api.app:app --port 8000) へ
      // 転送する。同一オリジン経由にすることで CORS 設定を単純化する。
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
})
