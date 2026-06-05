# Database (SQL Server)

Contiene la configuración necesaria para el contenedor de la base de datos Microsoft SQL Server.

## Contenido
- `Dockerfile`: Imagen personalizada con herramientas de cliente (sqlcmd) preinstaladas.
- `reset_db_identities.sql`: Script de utilidad para mantenimiento de la base de datos.

## Gestión
La base de datos se orquesta vía Docker Compose. Los datos persistentes se almacenan en el volumen `mssql_data`.
