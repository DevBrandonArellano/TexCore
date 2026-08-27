/// <reference types="vitest" />
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
    },
    test: {
        environment: 'jsdom',
        setupFiles: ['./vitest.setup.ts'],
        globals: true,
        // Los dashboards grandes (Vendedor, InventoryDashboard, …) renderizan
        // mucho DOM y usan userEvent; en aislamiento tardan ~3s, pero al correr
        // toda la suite (~1000 tests en paralelo) la contención de CPU los empuja
        // sobre el default de 5s y fallaban por timeout (no por lógica). Se da
        // holgura para que la suite completa sea determinista.
        testTimeout: 20000,
        hookTimeout: 20000,
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['src/**'],
            exclude: [
                'src/components/ui/**',
                'src/components/figma/**',
                'src/**/*.test.{ts,tsx}',
                'src/**/*.d.ts',
                'src/index.tsx',
                'src/vite-env.d.ts',
                'src/lib/types.ts',
                'src/lib/mockData.ts',
                'src/lib/*.code-workspace',
                'src/types/**',
            ],
            // Objetivo del plan de testabilidad: 90% en las 4 métricas.
            // Estado (2026-08-27, cierre del plan): las 4 métricas alcanzan
            // el objetivo — statements 95.29%, branches 90.02%, functions
            // 92.05%, lines 96.45%. Piso protegido justo debajo del nivel
            // real alcanzado.
            thresholds: {
                lines: 95,
                functions: 91,
                branches: 89,
                statements: 94,
            },
        },
    }
})
