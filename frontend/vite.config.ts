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
            // Objetivo del plan de cobertura QA: 90%. Estado (2026-07-10) tras
            // cerrar las Fases 4a-4c: lib/ (96%), produccion/ (100% de la
            // carpeta), y 3 componentes sueltos con tests reales de
            // comportamiento (no smoke). Piso protegido justo debajo del nivel
            // real alcanzado (statements ~37%). Pendiente — Fase 4d: convertir
            // los ~28 smoke tests de los dashboards grandes (VendedorDashboard,
            // EjecutivosDashboard, AdminSistemasDashboard, etc.) en tests
            // reales; subir este piso progresivamente a medida que se cierre.
            thresholds: {
                lines: 37,
                functions: 22,
                branches: 27,
                statements: 34,
            },
        },
    }
})
