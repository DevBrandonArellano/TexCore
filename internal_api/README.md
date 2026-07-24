# Módulo Internal API

Este módulo provee una capa de comunicación segura entre el backend principal y los servicios satélite externos (`scanning_service`, `reporting_excel`).

## Responsabilidades
- **Autenticación Inter-servicios**: Emisión y validación de tokens JWT (RS256) específicos para servicios.
- **Serialización de Auditoría**: Proveer datos de auditoría a los servicios satélite de forma estandarizada.
- **Endpoints Internos**: Rutas que no están expuestas al frontend, destinadas solo al consumo por otros servicios del stack.

## Seguridad
Utiliza una clave privada RSA para firmar tokens que solo los servicios satélite con la clave pública correspondiente pueden validar.
