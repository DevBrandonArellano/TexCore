FROM node:24-alpine AS builder

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
FROM nginx:alpine

# Eliminar la configuración por defecto de Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copiar nuestra configuración personalizada de Nginx
COPY nginx/nginx.conf /etc/nginx/conf.d/

# Copiar los archivos estáticos construidos desde la etapa 'builder'
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Exponer el puerto 80
EXPOSE 80

# Salud: nginx sirve el index de React. No pasa por /api/ para que una caída
# del backend no marque a nginx como enfermo (el backend tiene su propio check).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --start-interval=2s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

# Comando para iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]