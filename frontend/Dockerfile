# ---- Etapa de Dependencias/Construcción ----
FROM node:18-alpine AS build

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar archivos de manifiesto del paquete y de bloqueo
COPY package.json package-lock.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto del código fuente de la aplicación
COPY . .

# Construir la aplicación para producción
RUN npm run build

# ---- Etapa de Producción ----
FROM nginx:alpine

# Copiar los archivos construidos desde la etapa de construcción al directorio de servicio de Nginx
COPY --from=build /app/build /usr/share/nginx/html

# Exponer el puerto 80 para el servidor Nginx
EXPOSE 80

# Comando para iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]
