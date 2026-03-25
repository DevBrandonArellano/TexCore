# Roadmap de Producción para TexCore

Este documento describe la hoja de ruta para evolucionar TexCore desde su estado actual de desarrollo a un sistema robusto, optimizado y listo para un entorno de producción con un objetivo de **soportar ~50 usuarios simultáneos**.

---

### Fase 0: Estabilización del Entorno de Desarrollo (Completado)

Esta fase se centró en crear un entorno de desarrollo Docker robusto, portable y fácil de usar, sentando las bases para todo el desarrollo futuro.

-   **[x] Automatización del Arranque del Backend:**
    -   **Tarea:** Se implementó un `entrypoint.sh` que automatiza toda la secuencia de inicio: espera de la BD, creación de la BD, ejecución de migraciones y creación de directorios necesarios.
    -   **Razón:** Elimina la necesidad de pasos manuales post-inicio, haciendo que `docker-compose up` sea el único comando necesario para tener un entorno funcional.

-   **[x] Corrección de Portabilidad entre Windows y Linux:**
    -   **Tarea:** Se solucionaron errores críticos relacionados con los finales de línea (CRLF vs. LF) en los scripts de shell.
    -   **Razón:** Garantiza que el proyecto pueda ser desarrollado sin problemas tanto en Windows como en sistemas Unix-like.

-   **[x] Documentación Exhaustiva del Entorno:**
    -   **Tarea:** Se actualizó y expandió la documentación de Docker (`docker_setup.md`) y el `README.md` para reflejar la nueva arquitectura y el proceso de inicio simplificado.
    -   **Razón:** Facilita la incorporación de nuevos desarrolladores al proyecto.

---

### Fase 1: Implementación de la Arquitectura de Producción (A corto plazo)

El objetivo principal de esta fase es reemplazar los componentes de desarrollo (servidores de `runserver` y `npm start`) por una arquitectura de contenedores de alto rendimiento utilizando Gunicorn y Nginx.

-   **[x] Contenerizar el Backend para Producción:**
    -   Añadir `Gunicorn` al proyecto como el servidor de aplicaciones WSGI profesional para Django.
    -   Crear un `Dockerfile.prod` para el backend que inicie la aplicación usando Gunicorn.

-   **[x] Contenerizar el Frontend para Producción:**
    -   Utilizar el `Dockerfile` existente del frontend que ya está preparado para producción (usa `npm run build` y Nginx) para servir los archivos estáticos de React.

-   **[x] Orquestación con Docker Compose para Producción:**
    -   Crear un archivo `docker-compose.prod.yml` que defina la arquitectura de servicios para producción.
    -   Este archivo orquestará:
        1.  El servicio de base de datos (`db`).
        2.  El servicio `backend` corriendo con Gunicorn.
        3.  Un nuevo servicio `nginx` que actuará como **reverse proxy**.

-   **[x] Configurar Nginx como Reverse Proxy:**
    -   Crear la configuración de Nginx (`nginx.conf`) para que funcione como el punto de entrada principal a la aplicación.
    -   **Responsabilidades de Nginx:**
        -   Recibir todo el tráfico en el puerto 80/443.
        -   Dirigir las peticiones a la API (ej. `/api/*`) al servicio `backend` de Gunicorn.
        -   Servir directamente los archivos estáticos de la aplicación React para todas las demás peticiones.

---

### Fase 2: Optimización de Código y Base de Datos (A mediano plazo)

Con la arquitectura de producción en su lugar, el foco se mueve a optimizar el código de la aplicación para manejar la carga de manera eficiente y evitar cuellos de botella.

-   **[x] Optimización de Consultas a la Base de Datos (Querysets):**
    - Implementado `select_related` en los ViewSets críticos (`MovimientoInventario`, `PedidoVenta`, `Cliente`) para eliminar el problema N+1.
    - Complejidad de lectura reducida a O(1) con JOINs de SQL.

-   **[x] Indexación de la Base de Datos:**
    - Añadidos índices (`db_index=True`) en campos de búsqueda frecuentes como `estado`, `ruc_cedula` y `codigo`.

-   **[ ] Implementación de Estrategias de Caché:**
    - Proyectado el uso de Redis para endpoints de catálogos masivos.

-   **[x] Revisión de Lógica de Negocio Compleja (Dashboard):**
    - Refactorizado el Dashboard del Vendedor con diálogos detallados y lógica de beneficios dinámicos.
    - Implementada validación de límite de crédito en tiempo real.

---

### Fase 3: Pruebas y Robustez (En Progreso)

-   **[x] Suite de Pruebas Integradas:**
    - Creado `gestion/tests_integrados.py` que unifica validaciones de Crédito, Ventas e Inventario.
    - Validado el funcionamiento de roles y permisos.

-   **[ ] Pruebas de Carga y Estrés:**
    - Utilizar herramientas como `Locust` para simular 50 usuarios concurrentes.

    -   Identificar y corregir los cuellos de botella que surjan durante las pruebas.
    -   Validar que los tiempos de respuesta se mantienen aceptables bajo carga.

-   **[ ] Pruebas de Integración y End-to-End (E2E):**
    -   Escribir pruebas automatizadas que validen los flujos críticos de la aplicación en el entorno de producción.

-   **[ ] Configuración de Logging y Monitoreo para Producción:**
    -   Configurar Gunicorn y Nginx para que generen logs de acceso y errores en un formato estructurado.
    -   Centralizar los logs de todos los contenedores para facilitar la depuración.

-   **[ ] Documentación Final para Despliegue:**
    -   Crear una guía paso a paso para desplegar la aplicación en un servidor nuevo usando el archivo `docker-compose.prod.yml`.
    -   Documentar la gestión de secretos y variables de entorno en producción.

---

## Fase 4: Mejoras de Arquitectura y Seguridad (Propuestas)

Esta sección detalla una serie de mejoras propuestas basadas en un análisis detallado del código y la arquitectura, con el objetivo de aumentar la seguridad, mantenibilidad y robustez de la aplicación.

### Configuración y Seguridad

-   **[x] [CRÍTICO] Externalizar la Configuración del Frontend:**
    -   **Tarea:** Mover la URL de la API (`http://127.0.0.1:8000/api`) del código fuente a una variable de entorno (ej. `REACT_APP_API_URL`).
    -   **Razón:** Evita tener que modificar el código para cada entorno (desarrollo, producción), aumentando la flexibilidad y reduciendo errores.

-   **[x] [CRÍTICO] Mejorar la Seguridad en el Almacenamiento de Tokens:**
    -   **Tarea:** Cambiar el almacenamiento de tokens JWT de `localStorage` a cookies `HttpOnly`.
    -   **Razón:** Protege contra ataques XSS al impedir que el token sea accesible desde scripts del lado del cliente.

-   **[x] [CRÍTICO] Implementar HTTPS:**
    -   **Tarea:** Configurar Nginx para que gestione certificados SSL/TLS y fuerce todo el tráfico a través de HTTPS.
    -   **Razón:** Cifra toda la comunicación entre el cliente y el servidor, protegiendo datos sensibles como contraseñas y tokens.

### Arquitectura Frontend

-   **[x] [COMPLETADO] Implementar Arquitectura de Navegación Híbrida (URL State):**
    -   **Tarea:** Migrar el control de estado de UI crítico (paginación, filtros, pestañas) de estado de React (`useState`) a parámetros de URL (`useSearchParams`).
    -   **Razón:** Facilita que los usuarios compartan enlaces a un estado específico, posibilita el uso de botones nativos del navegador ("Atrás", "Adelante") y centraliza la fuente de verdad del componente.

-   **[x] [RECOMENDADO] Adoptar una Librería de Gestión de Estado de Servidor:**
    -   **Tarea:** Integrar una herramienta como **React Query (TanStack Query)** para manejar la obtención, cacheo y sincronización de datos con la API.
    -   **Razón:** Reduce el "prop drilling", simplifica el manejo de estados de carga/error, mejora el rendimiento y hace que los componentes sean más limpios y mantenibles.

-   **[x] [RECOMENDADO] Reforzar la Seguridad de Tipos:**
    -   **Tarea:** Eliminar el uso de `any` en el código TypeScript, ajustando los serializers del backend para que devuelvan una estructura de datos predecible y actualizando los tipos del frontend en consecuencia.
    -   **Razón:** Aprovecha al máximo TypeScript para prevenir bugs en tiempo de desarrollo y mejorar la legibilidad del código.

### Arquitectura Backend

-   **[x] [RECOMENDADO] Desarrollar un Conjunto de Pruebas Automatizadas:**
    -   **Tarea:** Crear pruebas unitarias para la lógica de negocio crítica y pruebas de integración para los endpoints de la API.
    -   **Razón:** Garantiza la estabilidad del código, previene regresiones y da confianza para realizar cambios y refactorizaciones a futuro.

-   **[x] [RECOMENDADO] Estandarizar el Manejo de Errores de la API:**
    -   **Tarea:** Implementar un manejador de excepciones global en Django REST Framework para que todas las respuestas de error sigan un formato JSON consistente.
    -   **Razón:** Simplifica la gestión de errores en el frontend y crea una API más robusta y predecible.
---

### Fase 5: Automatización de Despliegues con CI/CD (Completado)

Para mejorar la velocidad, fiabilidad y seguridad del ciclo de desarrollo, se implementó un pipeline de Integración Continua y Despliegue Continuo (CI/CD) utilizando GitLab.

-   **[x] Configurar el Pipeline de CI/CD (`.gitlab-ci.yml`):**
    -   Se definió el flujo de trabajo automatizado con etapas de `build`, `test` y `deploy`.

-   **[x] Integrar Pruebas Automatizadas:**
    -   El pipeline ejecuta automáticamente las pruebas.

-   **[x] Automatizar la Construcción de Imágenes Docker:**
    -   Se construyen y suben las imágenes al Registry de GitLab.

-   **[x] Automatizar el Despliegue en Producción:**
    -   Implementado despliegue seguro sin SSH usando el Runner local.

---

### Fase 6: Robustecimiento de Seguridad (Próximo Objetivo)

Para mitigar riesgos de seguridad y proteger la infraestructura en un entorno expuesto a internet.

-   **[ ] Hardening de Nginx:**
    -   Implementar cabeceras de seguridad estrictas: `HSTS` (Strict-Transport-Security), `X-Frame-Options`, `Content-Security-Policy` (CSP).
    -   Ocultar versión del servidor (`server_tokens off`).

-   **[ ] Rate Limiting (Limitación de Tasa):**
    -   Configurar Nginx para limitar el número de peticiones por IP, previniendo ataques de fuerza bruta y DoS.

-   **[ ] Seguridad de Aplicación Django:**
    -   Forzar cookies seguras (`Secure`, `HttpOnly`, `SameSite`).
    -   Validar configuración de hosts y orígenes confiables (`CSRF_TRUSTED_ORIGINS`).

-   **[ ] Aislamiento de Red Docker:**
    -   Asegurar que la base de datos no exponga puertos al host externo, comunicándose solo a través de la red interna de Docker.

---

### Fase 7: Escalabilidad Horizontal (Futuro)

Preparar el sistema para escalar más allá de un solo servidor cuando la carga supere los 50-100 usuarios.

-   **[ ] Separación de Base de Datos:**
    -   Mover SQL Server a un servidor dedicado o servicio gestionado (como Azure SQL o AWS RDS) para liberar recursos en el nodo de aplicación.

-   **[ ] Balanceo de Carga:**
    -   Desplegar múltiples réplicas del contenedor `backend` y configurar Nginx como balanceador de carga (Load Balancer) para distribuir el tráfico.

-   **[ ] Almacenamiento Estático Externo:**
    -   Mover archivos estáticos y media (imágenes subidas por usuarios) a un servicio de almacenamiento de objetos como AWS S3 o Azure Blob Storage, servidos vía CDN.

-   **[ ] Monitoreo Avanzado:**
    -   Implementar Prometheus y Grafana para visualizar métricas de rendimiento en tiempo real (CPU, RAM, latencia de peticiones).

---

### Fase 8: Módulo de Despacho y Microservicios (En Progreso)

Esta fase introduce un sistema completo de gestión de despachos con arquitectura de microservicios, permitiendo el escaneo de códigos de barras/QR, validación en tiempo real, y trazabilidad completa de los despachos.

#### Implementado ✅

-   **[x] Microservicio de Escaneo (`scanning_service`):**
    -   **Tarea:** Crear un microservicio independiente en FastAPI para validar códigos de lotes escaneados.
    -   **Implementación:**
        - Servicio FastAPI con endpoint `/scanning/validate` para validación de lotes.
        - Conexión directa a la base de datos usando SQLAlchemy.
        - Modelos ORM para `Producto`, `Bodega`, `LoteProduccion` y `StockBodega`.
        - Dockerizado con su propio `Dockerfile` y `requirements.txt`.
        - Integrado en `docker-compose.prod.yml` como servicio independiente.
    -   **Razón:** Desacoplar la lógica de escaneo del backend principal, permitiendo escalabilidad independiente y mejor mantenibilidad.

-   **[x] Configuración de Nginx como API Gateway:**
    -   **Tarea:** Configurar Nginx para enrutar peticiones al microservicio de escaneo.
    -   **Implementación:**
        - Añadido bloque `location /api/scanning/` en `nginx.conf`.
        - Proxy pass hacia el servicio `scanning:8001`.
        - Nginx actúa como punto de entrada único para todos los servicios.
    -   **Razón:** Centralizar el acceso a todos los servicios backend a través de un único punto de entrada.

-   **[x] Modelos de Historial de Despacho:**
    -   **Tarea:** Crear modelos Django para registrar el historial completo de despachos.
    -   **Implementación:**
        - `HistorialDespacho`: Registro maestro con fecha, usuario, pedidos, totales y observaciones.
        - `DetalleHistorialDespacho`: Detalle de cada lote despachado con peso y flag de devolución.
        - Migración `0006_add_historial_despacho.py` creada y aplicada.
    -   **Razón:** Mantener trazabilidad completa de todos los despachos para auditoría y análisis.

-   **[x] Integración del Historial en el Proceso de Despacho:**
    -   **Tarea:** Actualizar `ProcessDespachoAPIView` para registrar automáticamente el historial.
    -   **Implementación:**
        - Creación de `HistorialDespacho` al inicio de la transacción.
        - Registro de cada lote en `DetalleHistorialDespacho`.
        - Actualización de `MovimientoInventario.documento_ref` con ID del despacho.
        - Cálculo automático del peso total despachado.
    -   **Razón:** Automatizar el registro del historial sin intervención manual, garantizando consistencia.

-   **[x] Actualización del Frontend de Despacho:**
    -   **Tarea:** Modificar `DespachoDashboard.tsx` para usar el nuevo microservicio.
    -   **Implementación:**
        - Cambio de endpoint de validación de `/inventory/validate-lote/` a `/scanning/validate`.
        - Mantenimiento de la interfaz de escaneo multi-orden.
        - Validación de cliente único por despacho.
    -   **Razón:** Aprovechar el nuevo microservicio de escaneo para mejor rendimiento y escalabilidad.

#### Próximas Tareas 📋

-   **[x] API de Consulta de Historial de Despachos:**
    -   **Tarea:** Crear endpoints REST para consultar el historial de despachos.
    -   **Implementación:**
        - Endpoints `GET /api/inventory/historial-despachos/` para listar.
        - Filtros por fecha integrados (`fecha_desde`, `fecha_hasta`).
        - Optimización N+1 con `select_related` y `prefetch_related`.
    -   **Razón:** Permitir consultas eficientes del historial desde el frontend.

-   **[x] Vista de Historial de Despachos en el Frontend:**
    -   **Tarea:** Crear componente React para visualizar el historial de despachos.
    -   **Implementación:**
        - Componente `HistorialDespachos.tsx` con navegación híbrida.
        - Modal de detalles para ver lotes y pedidos asociados.
        - Paginación y filtros sincronizados con la URL.
    -   **Razón:** Dar visibilidad completa del historial de despachos a los usuarios.

-   **[ ] Funcionalidad de Devoluciones (Returns):**
    -   **Tarea:** Implementar el proceso completo de devolución de mercancía.
    -   **Backend:**
        - Endpoint `POST /api/inventory/procesar-devolucion/`.
        - Validar que los lotes pertenezcan a un despacho previo.
        - Crear `MovimientoInventario` tipo `DEVOLUCION`.
        - Actualizar `StockBodega` incrementando la cantidad devuelta.
        - Crear registro en `DetalleHistorialDespacho` con `es_devolucion=True`.
    -   **Frontend:**
        - Interfaz de escaneo similar al despacho pero para devoluciones.
        - Selección del despacho original (opcional, para validación).
        - Confirmación visual de items devueltos.
    -   **Razón:** Completar el ciclo de vida del despacho permitiendo gestionar devoluciones.

-   **[ ] Validación de Items No Despachados:**
    -   **Tarea:** Implementar alertas para identificar items de pedidos que no fueron despachados.
    -   **Implementación:**
        - Comparar items del pedido vs. lotes escaneados antes de finalizar.
        - Mostrar advertencia si hay discrepancias.
        - Permitir al usuario confirmar despacho parcial o cancelar.
    -   **Razón:** Evitar despachos incompletos no intencionales.

-   **[ ] Generación y Reimpresión de Documentos:**
    -   **Tarea:** Implementar generación automática de documentos PDF para despachos.
    -   **Funcionalidades:**
        - Generar PDF con detalle del despacho (lista de lotes, pesos, cliente, etc.).
        - Almacenar referencia al documento en `HistorialDespacho`.
        - Endpoint para regenerar/reimprimir documentos desde el historial.
    -   **Razón:** Proporcionar documentación física/digital de cada despacho.

-   **[ ] Dashboard de Métricas de Despacho:**
    -   **Tarea:** Crear vista analítica de despachos.
    -   **Métricas sugeridas:**
        - Total de despachos por período.
        - Peso total despachado.
        - Tasa de devoluciones.
        - Despachos por usuario/bodega.
        - Gráficos de tendencias.
    -   **Razón:** Proporcionar insights sobre la operación de despachos.

---

### Fase 9: Reactivación y Optimización de Roles Operativos (Completado)

Esta fase, ejecutada en paralelo o secuencialmente a las anteriores, se centró en devolver la funcionalidad completa a los roles operativos críticos (`Jefe de Área` y `Operario`) que habían sido desactivados temporalmente durante la estabilización inicial.

-   **[x] Rol y Dashboard de Jefe de Área:**
    -   **Tarea:** Rehabilitar y potenciar el panel de control para la gestión de maquinaria y asignación de órdenes.
    -   **Logros:**
        -   Visualización en tiempo real de la carga de cada máquina (Producción/Capacidad).
        -   Flujo completo de asignación de órdenes a operarios específicos.
        -   Gestión de estados de maquinaria (Operativa, Mantenimiento, Inactiva).
        -   Resolución de permisos de escritura (`403 Forbidden`) para garantizar autonomía operativa.

-   **[x] Rol y Dashboard de Operario (Nuevo):**
    -   **Tarea:** Crear una interfaz simplificada para el personal de planta.
    -   **Logros:**
        -   Vista filtrada: Los operarios solo ven las órdenes que se les han asignado.
        -   Registro "One-Click": Ingreso rápido de peso neto y unidades producidas desde la misma tarjeta de la orden.
        -   Visualización clara de instrucciones técnicas (Fórmula, Observaciones).

-   **[x] Seguridad y Permisos Granulares:**
    -   **Tarea:** Refinar el modelo de permisos para equilibrar seguridad y usabilidad.
    -   **Logros:**
        -   **Lectura Universal Autenticada:** Se estandarizó el acceso de lectura a catálogos clave (Máquinas, Productos) para evitar bloqueos en dashboards.
        -   **Escritura Basada en Roles:** Se implementaron verificaciones explícitas de grupo (`jefe_area`, `jefe_planta`, `admin_sistemas`) en el backend, superando las limitaciones del sistema de permisos por defecto de Django en ciertos contextos.
