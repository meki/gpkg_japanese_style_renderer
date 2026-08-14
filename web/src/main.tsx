import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// 意匠 (SP-06-02): CDN に依存せず自己ホストする (RQ-08-01)。日本語サブセットのみ読み込む。
import '@fontsource/yuji-syuku/japanese-400.css'
import '@fontsource/shippori-mincho/japanese-400.css'
import '@fontsource/shippori-mincho/japanese-600.css'
import '@fontsource/klee-one/japanese-400.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
