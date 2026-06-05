# Módulo de Gestión (Core Business)

Este es el módulo principal de **TexCore**, encargado de la lógica de negocio central, administración de usuarios, sedes y catálogos maestros.

## Responsabilidades
- **Autenticación y Perfiles**: Gestión de usuarios, roles (Operario, Tintorero, Vendedor, etc.) y permisos basados en sedes.
- **Catálogos Maestros**: Definición de Sedes, Bodegas, Productos (químicos, telas, etc.), Clientes y Proveedores.
- **Fórmulas y Producción**: Lógica para la creación de fórmulas textiles y gestión de lotes de producción.
- **Auditoría**: Mixins y servicios para el registro de cambios (AuditableModelMixin) y trazabilidad de acciones.

## Estructura Principal
- `models.py`: Definición de la entidad de negocio principal.
- `services/`: Lógica de negocio desacoplada de las vistas.
- `views/`: Endpoints de la API (Django Rest Framework).
- `permissions.py`: Reglas de acceso basadas en la Sede del usuario.

## Comandos Útiles
```bash
python manage.py seed_data  # Poblar catálogos iniciales
```
