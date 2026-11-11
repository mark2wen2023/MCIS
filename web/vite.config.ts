import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 后端只监听 127.0.0.1:8765；前端经同源代理访问，避免 CORS。
const backend = process.env.MCIS_API ?? 'http://127.0.0.1:8765'
const proxy = { '/api': { target: backend, changeOrigin: false } }

export default defineConfig({
  plugins: [react()],
  // 页面显示的服务地址与代理目标同源（W6.1 裁定 10，不在页面写死）
  define: { __MCIS_API__: JSON.stringify(backend) },
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
  build: { chunkSizeWarningLimit: 1500 },
})
