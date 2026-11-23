import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'
import {fileURLToPath} from 'node:url'
export default defineConfig({root:fileURLToPath(new URL('.',import.meta.url)),base:'./',plugins:[react()],define:{__MCIS_API__:JSON.stringify('synthetic-no-backend')},build:{outDir:'../../../.evidence-page-browser-dist',emptyOutDir:true}})
