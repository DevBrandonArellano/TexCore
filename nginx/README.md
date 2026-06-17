# Nginx API Gateway

Nginx actúa como el punto único de entrada (Reverse Proxy) para todo el stack de TexCore.

## Responsabilidades
- **SSL/TLS Termination**: Manejo de certificados HTTPS.
- **Ruteo**: 
    - `/` -> Frontend (Vite)
    - `/api/` -> Backend (Django/Gunicorn)
    - `/api/scanning/` -> Scanning Service
- **Servicio de Estáticos**: Entrega de archivos CSS, JS e imágenes de Django.
- **Seguridad**: Cabeceras de protección (HSTS, X-Frame-Options, etc.).
