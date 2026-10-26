FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS builder

# Establecer el directorio de trabajo para la construcción del frontend
WORKDIR /app/frontend

# Copiar los archivos de manifiesto y de bloqueo del frontend
COPY frontend/package.json frontend/package-lock.json ./

# Instalar dependencias del frontend
RUN npm install

# Copiar todo el código fuente del frontend
COPY frontend/ ./

# Construir la aplicación para producción
RUN npm run build


# --- Etapa 2: Configurar el servidor Nginx ---
FROM nginx:alpine@sha256:df221db836e1754089190208cee7eeda94f233197056426eda74a43ab1abeac2

# Eliminar la configuración por defecto de Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copiar nuestra configuración personalizada de Nginx como plantilla: al arrancar, el
# entrypoint de la imagen la pasa por envsubst y la deja en /etc/nginx/conf.d/texcore.conf.
# El filtro limita la sustitución a NGINX_* para no tocar $host, $request_uri, etc.
COPY nginx/nginx.conf /etc/nginx/templates/texcore.conf.template
ENV NGINX_ENVSUBST_FILTER=^NGINX_
# RNF-01: 1 = el puerto 80 responde 301 hacia HTTPS. Producción lo activa en
# docker-compose.prod.yml; en desarrollo se sirve también por HTTP.
ENV NGINX_REDIRIGIR_HTTP=0

# Copiar los archivos estáticos construidos desde la etapa 'builder'
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 80 443

# Salud: nginx sirve el index de React. No pasa por /api/ para que una caída
# del backend no marque a nginx como enfermo (el backend tiene su propio check).
# Sondea por HTTPS porque en producción el puerto 80 solo redirige; el certificado
# es propio y la sonda es local, por eso no se verifica.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --start-interval=2s --retries=3 \
    CMD wget -q --no-check-certificate -O /dev/null https://127.0.0.1/ || exit 1

# Comando para iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]