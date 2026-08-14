import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // FastAPI バックエンド (uv run uvicorn gpkg_jsr.api.app:app --port 8001) へ
      // 転送する。同一オリジン経由にすることで CORS 設定を単純化する。
      // 8000 番は環境によって VS Code 等の他プロセスに使われていることがあるため
      // 8001 番を既定にしている。ポート番号を変える場合はここも合わせて変更する。
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
})
