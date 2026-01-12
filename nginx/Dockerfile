# --- Etapa 1: Construir la aplicación de React ---
FROM node:18-alpine AS builder

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
COPY --from=builder /app/frontend/build /usr/share/nginx/html

# Exponer el puerto 80
EXPOSE 80

# Comando para iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]