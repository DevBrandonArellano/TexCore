import axios from 'axios';
import { createLogger } from './logger';

// RFC 5424 — logger de la capa HTTP del frontend (Facility 20 / local4)
const logger = createLogger('texcore-axios');

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => {
    // RFC 5424 — INFO por cada respuesta exitosa (solo en DEBUG para evitar flood)
    if (import.meta.env.DEV) {
      logger.debug('HTTP response', {
        method: response.config.method?.toUpperCase() ?? '-',
        url: response.config.url ?? '-',
        status: response.status,
      });
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const status: number = error.response?.status ?? 0;
    const url: string = originalRequest?.url ?? 'unknown';

    if (
      status === 401 &&
      !originalRequest._retry &&
      !url.endsWith('/token/') &&
      !url.endsWith('/token/refresh/') &&
      !url.endsWith('/profile/')
    ) {
      originalRequest._retry = true;

      try {
        await apiClient.post('/token/refresh/');
        logger.notice('Token renovado exitosamente', { url });
        return apiClient(originalRequest);
      } catch (refreshError) {
        // RFC 5424 — CRITICAL: sesión expirada, usuario debe re-autenticarse
        logger.critical('Sesión expirada — el usuario debe re-autenticarse', {
          url,
          reason: 'refresh_token_invalid',
        });
        // IMPORTANTE: No usamos window.location.href='/login' aquí porque 
        // provoca un recargo completo de la SPA y un bucle infinito si la
        // petición de perfil al arranque también falla con 401.
        // El AuthProvider detectará que no hay perfil y mostrará el Login automáticamente.
        return Promise.reject(refreshError);
      }
    }

    // RFC 5424 — severidad según código HTTP
    if (status >= 500) {
      logger.error('Error de servidor en API', {
        url,
        status: String(status),
        method: originalRequest?.method?.toUpperCase() ?? '-',
      });
    } else if (status >= 400) {
      logger.warning('Error de cliente en API', {
        url,
        status: String(status),
        method: originalRequest?.method?.toUpperCase() ?? '-',
      });
    } else if (status === 0) {
      logger.error('Sin respuesta del servidor (red o CORS)', {
        url,
        method: originalRequest?.method?.toUpperCase() ?? '-',
      });
    }

    return Promise.reject(error);
  }
);

export default apiClient;
