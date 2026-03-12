import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// En Docker use backend:8000; en host local use localhost:8000
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        host: true,
        proxy: {
            // Proxy para reportes Excel (microservicio reporting_excel)
            '/api/reporting': {
                target: 'http://localhost:8002',
                changeOrigin: true,
                secure: false,
                rewrite: (path) => path.replace(/^\/api\/reporting/, ''),
            },
            // Proxy para la API de Django (localhost en host, backend en Docker)
            '/api': {
                target: apiTarget,
                changeOrigin: true,
                secure: false,
            }
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: false,
        minify: 'terser',
        chunkSizeWarningLimit: 1600,
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (id.includes('node_modules')) {
                        return 'vendor';
                    }
                }
            }
        }
    }
})
