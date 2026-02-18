# Documentación Técnica de TexCore

Bienvenido a la base de conocimiento de TexCore. Aquí encontrarás guías detalladas sobre la arquitectura, despliegue, mantenimiento y procesos de negocio del sistema.

## 📚 Índice de Contenidos

### 1. Arquitectura y Datos
*   [**Modelo de Datos y Procesos**](modelo_datos_proceso.md): Fuente de verdad sobre el esquema de base de datos (SQL Server), diagramas de flujo de negocio (Crédito, Ventas) y lógica logística (Kardex).
*   [**Recursos Algorítmicos**](recursos_algoritmicos.md): Explicación técnica sobre optimizaciones de rendimiento, índices de base de datos y solución al problema N+1 en querysets.

### 2. Infraestructura y Docker
*   [**Configuración de Docker**](docker_setup.md): Explicación detallada de la arquitectura de contenedores, volúmenes, redes y scripts de inicio (`deploy.sh`/`deploy.ps1`). Incluye sección de solución de problemas comunes.

### 3. Guías de Despliegue (Deployment)
*   [**Comandos de Producción**](comandos_produccion.md): Referencia rápida ("Cheatsheet") para operaciones comunes en servidores vivos (logs, reinicios, backups).
*   [**Despliegue en Ubuntu/Hyper-V**](guia_detallada_ubuntu_hyperv.md): Guía paso a paso para desplegar el sistema desde cero en un servidor Ubuntu virtualizado.

### 4. Seguridad y Autenticación
*   [**Troubleshooting de Autenticación**](authentication_troubleshooting.md): Guía para resolver problemas relacionados con JWT, Cookies HttpOnly y políticas CORS.

### 5. Análisis de Negocio y Roles
*   [**Manual de Roles y Permisos**](GUIA_ROLES_SISTEMA.md): Detalle de qué puede hacer cada usuario (Vendedor, Operario, Jefe de Planta, etc.) en el sistema.
*   [**Análisis Estratégico**](analisis_estrategico.md): Diagramas FODA y Causa-Raíz (Ishikawa) sobre el contexto del sector textil.

---

## 💡 ¿Por dónde empezar?

- **Para desarrolladores nuevos:** Lee [Configuración de Docker](docker_setup.md) y [Modelo de Datos](modelo_datos_proceso.md).
- **Para DevOps/SysAdmin:** Revisa [Comandos de Producción](comandos_produccion.md) y la [Guía de Despliegue](guia_detallada_ubuntu_hyperv.md).
- **Para entender el negocio:** Consulta los diagramas en [Modelo de Datos y Procesos](modelo_datos_proceso.md).
