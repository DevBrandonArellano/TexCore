# Módulo Internal API

Este módulo provee una capa de comunicación segura entre el backend principal y los servicios satélite externos (`scanning_service`, `reporting_excel`).

## Responsabilidades
- **Autenticación Inter-servicios**: Emisión y validación de tokens JWT (RS256) específicos para servicios.
- **Serialización de Auditoría**: Proveer datos de auditoría a los servicios satélite de forma estandarizada.
- **Endpoints Internos**: Rutas que no están expuestas al frontend, destinadas solo al consumo por otros servicios del stack.

## Seguridad
Defensa en profundidad en varias capas independientes:
- **Nginx**: `location ^~ /api/internal/ { return 404; }` en `nginx/nginx.conf` — la API interna nunca responde a través del proxy público. Los servicios satélite la llaman directo por DNS de Docker (`http://backend:8000/api/internal/v1/...`), sin pasar por nginx.
- **Autenticación**: clave privada RSA (`INTERNAL_JWT_PRIVATE_KEY`) firma tokens JWT RS256 que solo quien tiene la clave pública correspondiente (`INTERNAL_JWT_PUBLIC_KEY`) puede validar (`authentication.py`). Secretos de servicio hasheados con PBKDF2 (`ServiceCredential`, `models.py`).
- **Autorización**: `IsInternalService` + `HasScope('<scope>')` por vista (`permissions.py`) — cada endpoint exige un scope específico del `ServicePrincipal`.
- **Handshake de servicio** (`auth/token/`, `auth/refresh/`): `ServiceAuthThrottle` (10/min) + validación de que `REMOTE_ADDR` sea una IP privada/loopback (`views/auth_views.py`) — protege el camino directo `backend:8000` que el bloqueo de nginx no toca.
- **Parámetros de URL**: rutas con datos de negocio (ej. `codigo_barras`) usan patrones restrictivos (`urls.py`) alineados con la validación que ya exige el modelo en el punto de creación (ej. `gestion.models.produccion.CODIGO_LOTE_REGEX`) — un valor que el sistema permitió crear siempre matchea la ruta.
- **Red Docker** (`infrastructure/docker/docker-compose.prod.yml`, solo producción): `dmz_net` (nginx + backend + scanning) vs `internal_net` con `internal: true` (backend + db + printing + reporting_excel) — `backend` es el único puente entre ambas.
