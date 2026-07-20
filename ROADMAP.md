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

### Fase 3: Pruebas y Robustez (Completado — 16 de Junio de 2026)

Refuerzo integral aplicando estándares ISTQB (EP, BVA, STT, caja blanca) y PMBOK (matriz de trazabilidad) para maximizar cobertura desde 58.0% a 63.5%, descubrir y corregir defectos reales.

-   **[x] Suite de Pruebas Integradas:**
    - Creado `gestion/tests_integrados.py` que unifica validaciones de Crédito, Ventas e Inventario.
    - Validado el funcionamiento de roles y permisos.
    - **[x] Estabilización Backend (Mayo 2026):** Suite ampliada con `tests_jefe_area.py` y `test_descarga_quimicos_tdd.py`. Resultado: **64/64 tests OK** sobre SQL Server.
    - **[x] Estabilización Backend Fase 14 (Junio 2026):** Correcciones en `test_pago_reversion.py` (`incluye_iva=False` en DetallePedido de tests, guardado de `pago_id` antes de `delete()`). Resultado: **184 tests — 0 fallos — 0 errores — 14 skipped** (tests de `BultoEmpaque`/`ConfiguracionEmpaque` obsoletos marcados con `@skipUnless`).

    - **[x] Refuerzo ISTQB + PMBOK (16 de Junio 2026):**
      - **Infraestructura reproducible:** `scripts/run_backend_tests.sh` (harness Docker con SQL Server 2022), `docker/Dockerfile.django-test` (driver ODBC 18), `.coveragerc` con `branch=True`.
      - **10 archivos de test nuevos (56 tests):** seguridad (`test_cookie_jwt_auth.py`, `test_audit_middleware.py`), vistas (`test_system_views.py`, `test_inventory_views.py`, `test_kpi_views.py`, `test_catalog_views.py`, `test_formula_views.py`), endpoints (`test_views_endpoints.py`).
      - **2 archivos profundizando servicios (11 tests):** `test_services_formula.py` (gr/L, %, fallbacks legacy, tipo desconocido), `test_descarga_quimicos_validaciones.py` (guardas de configuración).
      - **2 archivos serializers (11 tests):** `test_serializers.py` (gestion: regex acentos, dosificación > 0), `test_serializers.py` (inventory: cantidad > 0, razon_cambio ≥ 10 chars, origen ≠ destino).
      - **Defectos descubiertos y corregidos:**
        - Bug #1: `calcular_margen` en clase equivocada (`TransferenciaInterarea` → `CostoLoteProduccion`).
        - Bug #2: `DetalleFormulaViewSet.get_queryset` con `select_related('formula_color')` inexistente → HTTP 500 en todo listado. Corregido a `fase__formula`.
        - Bug #3: Descarga automática de químicos restaurada en `perform_create` (OP con fórmula + bodega_quimicos).
        - Código muerto eliminado: `empaque_service.py` + test (importaba modelos suprimidos, cero referencias externas).
        - 11 tests desactualizados arreglados (decimales a 3 lugares, envelope respuesta, `area` requerida, claves RSA entorno).
      - **Matriz PMBOK:** `docs/matriz_trazabilidad_pruebas.md` — requisito → archivo de prueba → técnica ISTQB → estado. Leyenda de ISTQB (EP, BVA, TD, STT, CB-D).
      - **Módulos grandes (2ª iteración):** `test_production_views.py` (31 tests: máquinas, OP, lotes, máquina de estados de subprocesos vía STT) y `test_movimiento_views.py` (11 tests: entradas/salidas + edición auditada). 3 bugs reales adicionales corregidos (`requisitos_materiales`, `LoteProduccion.perform_update`, `completar_detalles` — referencias residuales de Fase 14 que provocaban HTTP 500/ValueError).
      - **Exclusión de coverage:** comandos de management (`*/management/commands/*`, ~1.232 líneas de seed/stress operativo) excluidos vía `omit` — práctica estándar; el coverage mide código de aplicación.
      - **Resultado:** **379 tests — 0 fallos — 0 errores — 81.2% cobertura** (código de aplicación). Umbral `fail_under=78` en `.coveragerc`. `production_views.py` 45→73%, `inventory/views.py` 60→76%.

-   **[x] Cobertura de Pruebas Frontend (Mayo–Junio 2026):**
    - Implementación de `Smoke Tests` automatizados utilizando Vitest y Testing Library.
    - Validación estructural del 100% de los componentes de negocio (Dashboards, Modales, Formularios) totalizando 42 archivos de arquitectura core.
    - **Actualización Junio 2026:** Suite ampliada a **87 tests / 42 archivos / 0 fallos** tras correcciones de UI e incorporación de tests de comportamiento:
      - `ManageOrdenesProduccion.test.tsx`: mock de apiClient, tests de filtrado de tabla y verificación de fetch dinámico de áreas al abrir el diálogo.
      - `JefeAreaDashboard.test.tsx`: `QueryClientProvider` wrapper, mock diferenciado por endpoint, test de botón único "Nueva Máquina".

-   **[x] Refuerzo QA Integral — internal_api, Microservicios y Frontend (10 de Julio de 2026):**
    - **Backend (`gestion`+`inventory`+`internal_api`):** 440→694 tests, cobertura 80.8%→**89.6%** (el punto de partida sube de 379 tests/81.2% al cierre de la Fase 3 el 16 de junio a 440/80.8% el 9 de julio, por las Fases 15-16 y las correcciones del 1-2 de julio en el medio). `internal_api` no se medía en absoluto (fuera de `source` en `.coveragerc` y de los jobs de CI); ahora sí. Umbral `fail_under` subido de 78 a 89.
    - **6 bugs reales corregidos** (verificados contra SQL Server real, no simulados en SQLite):
      1. `TransferenciaInterareaSerializer`: `orden_area_origen`/`orden_area_destino` anidados `read_only=True` pese a ser `NOT NULL` en el modelo → creación de transferencias interárea siempre daba 500. Corregido a `PrimaryKeyRelatedField` escribibles (detalle anidado movido a `*_detail`); actualizado el consumidor en `TransferenciasInterarea.tsx`.
      2. `TopClientesVendedorView` / `TopClientesGerencialView` (`internal_api`): alias `cliente_id` colisionaba con el atributo que Django genera para el FK `cliente` → `ValueError` garantizado en cualquier request. De paso, `total_pedidos` sumaba IDs de pedido (`Sum("id")`) en vez de contarlos (`Count("id")`).
      3. `RotacionView` / `ResumenMovimientosView` (`internal_api`): el `ORDER BY` implícito de `MovimientoInventario.Meta.ordering` rompía las consultas `GROUP BY` en SQL Server (500) — invisible en tests contra SQLite. Corregido con `.order_by()` antes de `.values().annotate()`.
      4. `export_kardex` (`reporting_excel`): decidía el status code comparando `type(error_detail).__name__` contra `"ValueError"`, pero `error_detail` ya era un `str(exc)` (siempre `'str'`) → cualquier error del SP devolvía 400 en vez de 500, enmascarando fallos reales del servidor.
    - **Código muerto eliminado:** `gestion/services.py` (`ProduccionService`, inalcanzable por import — shadowed por el paquete `gestion/services/`), `MyTokenObtainPairSerializer` (sin ningún uso en el codebase).
    - **Microservicios FastAPI** — CI de `printing-service` solo ejecutaba 1 de 4 archivos de test (ignoraba `tests/unit/*` ya escritos); arreglado. Resultado: `printing_service` **99%**, `reporting_excel` 80%→**91%**, `scanning_service` 89%→**94.2%**. Umbrales subidos a 90-95% según el caso.
    - **Frontend** — cobertura medida por primera vez (antes sin `thresholds` ni script `test:coverage`). 28 de ~42 archivos de test existentes eran "smoke tests" sin aserciones reales (`expect(true).toBe(true)`); quedan pendientes de convertir. Se añadieron **14 archivos / ~125 tests reales** donde antes había cero cobertura dedicada: `lib/axios.ts`, `lib/auth.tsx`, `lib/logger.ts`, `App.tsx` (**96%** en `lib/`); los 5 componentes de `produccion/` (**100%** de la carpeta, antes sin tests); `ManageMaquinas.tsx`, `ComponenteMezclaPanel.tsx`, `SharedKPIChart.tsx`. Suite total: **217 tests / 56 archivos / 0 fallos**, 0%→**37.4%** statements.
    - **[x] Fase 4d — Completada (13 de Julio de 2026):** el alcance real resultó ser de **36 archivos** (no ~28 — se detectó una segunda variante de smoke test, `expect(() => render(...)).not.toThrow()`, usada en los dashboards de rol principales, que el grep original no capturaba). **36 de 36 convertidos, +496 tests reales.** Encontró y corrigió un bug crítico de producción (`ui/input.tsx` sin `React.forwardRef` rompía silenciosamente el formulario de creación de fórmulas de color vía react-hook-form) y uno menor (`HistorialDespachos.tsx` no renderizaba `items_no_despachados`). Ver CHANGELOG.md del 13 de julio para el detalle completo, incluyendo 6 hallazgos reportados sin corregir.
    - **[x] Profundización de cobertura post-Fase 4d (13 de Julio de 2026):** `VendedorDashboard.tsx` (42.3%→**78.2%**), `ManageOrdenesProduccion.tsx` (42.7%→**92.2%**), `JefePlantaDashboard.tsx` (47.95%→**100%**) y `EmpaquetadoDashboard.tsx` (59.71%→**98.56%**) ya tenían tests reales pero cobertura baja; se ampliaron con +130 tests en total sin reescribir lo existente. Bug latente encontrado y corregido en la misma sesión: `EmpaquetadoDashboard.tsx` no capturaba el error de un `pipeTo()` sin `.catch()` al perder conexión con la báscula Web Serial (unhandled promise rejection).
    - **[x] Los 8 dashboards de rol restantes llevados a 90%+ (13 de Julio de 2026):** `AdminSistemasDashboard.tsx` (64.3%→**100%**), `JefeAreaDashboard.tsx` (75.5%→**97.3%**), `TintoreroDashboard.tsx` (90.5%→**100%**), `VendedorDashboard.tsx` (78.2%→**96.9%**, segunda pasada), `OperarioDashboard.tsx` (84.8%→**98.2%**), `BodegueroDashboard.tsx` (85.7%→**100%**), `DespachoDashboard.tsx` (88.4%→**98.8%**), `EjecutivosDashboard.tsx` (89.4%→**100%**) — +159 tests. **Todos los dashboards de rol del proyecto quedan por encima del 96%.** Suite frontend final: 217→**937 tests / 61 archivos**, 0 fallos. Cobertura global: 37.4%→**91.68%** statements. Ver CHANGELOG.md 13 de julio para el detalle completo (tabla por dashboard, hallazgos de código muerto, nota técnica sobre un artefacto de visualización del reporte combinado de cobertura). Candidatos opcionales para el futuro, fuera del alcance de "roles" (sub-componentes, no dashboards de rol): `StockQuimicosDashboard.tsx` (70.6%), `Login.tsx` (72.7%), `MRPDashboard.tsx` (69.7%).

-   **[ ] Pruebas de Carga y Estrés:**
    - Utilizar herramientas como `Locust` para simular 50 usuarios concurrentes.

    -   Identificar y corregir los cuellos de botella que surjan durante las pruebas.
    -   Validar que los tiempos de respuesta se mantienen aceptables bajo carga.

-   **[ ] Pruebas de Integración y End-to-End (E2E):**
    -   Escribir pruebas automatizadas que validen los flujos críticos de la aplicación en el entorno de producción.

-   **[ ] Configuración de Logging y Monitoreo para Producción:**
    -   Configurar Gunicorn y Nginx para que generen logs de acceso y errores en un formato estructurado.
    -   Centralizar los logs de todos los contenedores para facilitar la depuración.

-   **[x] Documentación Final para Despliegue:**
    -   `docs/arquitectura/GUIA_DESPLIEGUE.md`: guía paso a paso completa — pre-requisitos, generación de claves RSA, `.env` de producción, certificados SSL, levantamiento de servicios, migraciones, registro de servicios satélites, verificación, rollback y mantenimiento.
    -   `scripts/generate_rsa_keys.py`: genera el par de claves RSA 2048 para JWT en una línea compatible con `.env`.
    -   `gestion/management/commands/register_services.py`: comando `python manage.py register_services [--force]` para registrar `scanning_service` y `reporting_excel` como `ServiceCredential` en la BD.

-   **[x] Reorganización de Documentación (Junio 2026):**
    -   Toda la documentación centralizada en `docs/` con estructura por dominio: `historias-usuarios/`, `requerimientos/`, `diagramas-uml/`, `arquitectura/`, `arquitectura-bd/`, `modulos/`.
    -   Eliminados ~20 archivos redundantes o desactualizados (resúmenes de implementación, guías rápidas de revisión).
    -   Creado `docs/README.md` como índice maestro navegable.
    -   Eliminado directorio `documentation/` (legacy).
    -   `docs/arquitectura/ARQUITECTURA_SISTEMA.md`: referencia técnica definitiva de 1687 líneas con C4, ERD completo, contratos de API, ADRs.

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

Para mejorar la velocidad, fiabilidad y seguridad del ciclo de desarrollo, se implementó un pipeline de Integración Continua y Despliegue Continuo (CI/CD) utilizando GitLab y GitHub Actions.

-   **[x] Configurar el Pipeline de CI/CD (`.gitlab-ci.yml`):**
    -   Se definió el flujo de trabajo automatizado con etapas de `lint → test → build → scan → deploy → health-check → rollback`.

-   **[x] Integrar Pruebas Automatizadas:**
    -   El pipeline ejecuta automáticamente las pruebas de todos los servicios (Django, servicios satélites FastAPI, frontend React).

-   **[x] Automatizar la Construcción de Imágenes Docker:**
    -   Se construyen y suben las imágenes al Registry de GitLab.

-   **[x] Automatizar el Despliegue en Producción:**
    -   Implementado despliegue seguro sin SSH usando el Runner local.

-   **[x] Pipeline GitHub Actions (`.github/workflows/`) — Implementado:**
    -   Workflows `ci.yml`, `cd.yml`, `rollback.yml` y `security.yml` con jobs paralelos por servicio.
    -   Quality Gate como barrera final antes de merge.
    -   CD via GHCR + SSH con rollback manual.
    -   Escaneo Trivy y SARIF en GitHub Security tab.

-   **[x] Corrección de Pipelines CI/CD (Mayo 2026):**
    -   Creado `TexCore/settings_test.py` (faltante) — los jobs `test:backend` / `backend-test` fallaban con `ModuleNotFoundError` al arrancar.
    -   **GitHub Actions:** Service container SQL Server 2022 + instalación ODBC Driver 18 en runner Ubuntu + step de espera. Fix bug Quality Gate: `docker-build-validation` con resultado `skipped` bloqueaba todo PR hacia `staging`.
    -   **GitLab CI:** Service container SQL Server 2022 con alias `sqlserver` + instalación ODBC Driver 18 adaptada a Debian (`python:3.12-slim`). Fix bug `test:dependency-audit`: dividido en `test:dependency-audit:python` (`pip-audit`) y `test:dependency-audit:node` (`npm audit`) porque `npm` no existe en `python:3.12-slim`.

---

### Fase 6: Robustecimiento de Seguridad (En Progreso)

Para mitigar riesgos de seguridad y proteger la infraestructura en un entorno expuesto a internet.

-   **[x] Hardening de Nginx:**
    -   `server_tokens off` — Nginx ya no expone su versión en headers ni páginas de error.
    -   Cabeceras en bloque HTTP: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`.
    -   Bloque HTTPS: añade `Strict-Transport-Security: max-age=31536000; includeSubDomains`.

-   **[x] Rate Limiting (Limitación de Tasa):**
    -   `login_zone`: 5 req/min por IP en `/api/token/` con burst de 3.
    -   `refresh_zone`: 10 req/min por IP en `/api/token/refresh/` con burst de 5.
    -   `api_zone`: 100 req/s por IP en `/api/` con burst de 200.

-   **[ ] Seguridad de Aplicación Django:**
    -   Forzar cookies seguras (`Secure`, `HttpOnly`, `SameSite`).
    -   Validar configuración de hosts y orígenes confiables (`CSRF_TRUSTED_ORIGINS`).

-   **[x] Aislamiento de Red Docker:**
    -   `docker-compose.prod.yml`: BD expone solo internamente vía `expose: ["1433"]`, sin `ports`.
    -   `docker-compose.yml` (dev): puerto 1433 restringido a loopback (`127.0.0.1:1433:1433`).
    -   `scanning` y `reporting_excel` en producción también usan solo `expose`, sin `ports`.

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

### Fase 8: Módulo de Despacho y Servicios Satélites (En Progreso)

Esta fase introduce un sistema completo de gestión de despachos con arquitectura de servicios satélites, permitiendo el escaneo de códigos de barras/QR, validación en tiempo real, y trazabilidad completa de los despachos.

#### Implementado ✅

-   **[x] Servicio Satélite de Escaneo (`scanning_service`):**
    -   **Tarea:** Crear un servicio satélite independiente en FastAPI para validar códigos de lotes escaneados.
    -   **Implementación:**
        - Servicio FastAPI con endpoint `/scanning/validate` para validación de lotes.
        - ~~Conexión directa a la base de datos usando SQLAlchemy.~~ → **Migrado a API Interna (ver Fase 13):** consume `GET /api/internal/v1/scanning/lotes/{codigo}/validate/` con JWT RS256. Sin dependencia de BD.
        - Modelos de dominio puros (dataclasses Python): `Producto`, `Bodega`, `LoteProduccion`, `StockBodega`.
        - Dockerizado con su propio `Dockerfile` y `requirements.txt`.
        - Integrado en `docker-compose.prod.yml` como servicio independiente.
    -   **Razón:** Desacoplar la lógica de escaneo del backend principal, permitiendo escalabilidad independiente y mejor mantenibilidad.

-   **[x] Configuración de Nginx como API Gateway:**
    -   **Tarea:** Configurar Nginx para enrutar peticiones al servicio satélite de escaneo.
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
    -   **Tarea:** Modificar `DespachoDashboard.tsx` para usar el nuevo servicio satélite.
    -   **Implementación:**
        - Cambio de endpoint de validación de `/inventory/validate-lote/` a `/scanning/validate`.
        - Mantenimiento de la interfaz de escaneo multi-orden.
        - Validación de cliente único por despacho.
    -   **Razón:** Aprovechar el nuevo servicio satélite de escaneo para mejor rendimiento y escalabilidad.

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

-   **[x] Funcionalidad de Reversión de Despachos (Completado — Marzo 2026):**
    -   **Tarea:** Implementar el proceso completo de reversión de despachos con restauración automática de stock.
    -   **Backend:**
        - `DespachoReversionService` con `revertir_despacho()` transaccional (`@transaction.atomic`).
        - Restauración de stock en bodegas origen + reversa de `DescargaQuimicoOP`.
        - `MovimientoInventario` tipo `DEVOLUCION` creado para auditoría.
        - `PedidoVenta` revertidos a estado `pendiente`.
        - Endpoints: `DELETE /api/inventory/historial-despachos/{id}/` y `POST /historial-despachos/{id}/revertir/`.
    -   **Frontend:**
        - Botón Revertir (rojo) en `HistorialDespachos.tsx` con modal de confirmación.
        - TextArea obligatorio para justificación + advertencia visual del peso a restaurar.
        - Toast notifications para éxito/error.
    -   **Razón:** Completar el ciclo de vida del despacho con reversión atómica y auditoría completa.

-   **[x] Validación de Items No Despachados:**
    -   **Tarea:** Implementar alertas para identificar items de pedidos que no fueron despachados.
    -   **Implementación:**
        - `ProcessDespachoAPIView._calcular_incompletos()`: compara `DetallePedido.peso` por producto vs. stock de lotes escaneados antes de la transacción.
        - HTTP 409 con `items_incompletos: {producto: {requerido, escaneado, faltante}}` si hay discrepancia y no se confirmó.
        - Modal de confirmación en `DespachoDashboard.tsx` con tabla de faltantes por producto (kg requerido / escaneado / faltante). Botones: "Cancelar — seguir escaneando" o "Despachar de todas formas".
        - Reenvío con `confirmar_incompleto: true` — el backend procede y persiste `items_no_despachados` en `HistorialDespacho` (campo `JSONField`, migración `0028`).
        - El historial expone `items_no_despachados` en el serializer para trazabilidad.
    -   **Razón:** Evitar despachos incompletos no intencionales; registrar despachos parciales con trazabilidad completa.

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
        -   **Sincronización de Inventario**: Al modificar o rechazar lotes, se ajusta automáticamente el consumo de químicos y materiales, así como el progreso total de la OP.

-   **[x] Rol y Dashboard de Jefe de Planta (Alineado con InfoTint):**
    -   **Tarea:** Adaptar el flujo de creación de OP al modelo de separación de responsabilidades.
    -   **Logros:**
        -   Simplificación del formulario de creación de Órdenes de Producción.
        -   Delegación de la asignación de máquinas al *Jefe de Área* y fórmulas al *Tintorero*.
        -   Asignación automática de la sede de origen según el perfil del usuario activo.
        -   Rediseño responsive a doble columna (`max-h-[90vh]`) para adaptarse a cualquier pantalla.
        -   **Gestión de Prioridades**: Implementación de niveles de urgencia (`baja`, `normal`, `alta`, `urgente`) visibles directamente en la tabla principal con alertas visuales.

-   **[x] Seguridad y Permisos Granulares:**
    -   **Tarea:** Refinar el modelo de permisos para equilibrar seguridad y usabilidad.
    -   **Logros:**
        -   **Lectura Universal Autenticada:** Se estandarizó el acceso de lectura a catálogos clave (Máquinas, Productos) para evitar bloqueos en dashboards.
        -   **Escritura Basada en Roles:** Se implementaron verificaciones explícitas de grupo (`jefe_area`, `jefe_planta`, `admin_sistemas`) en el backend, superando las limitaciones del sistema de permisos por defecto de Django en ciertos contextos.

---

### Fase 10: Robustecimiento de Lógica de Negocio mediante TDD (Completado — Mayo 2026)

Esta fase se centró en blindar los procesos críticos de inventario químico y pagos mediante desarrollo guiado por pruebas (TDD), eliminación de deuda técnica de infraestructura y corrección de bugs de precisión en SQL Server.

-   **[x] Service Layer — Descarga de Químicos (`DescargaQuimicosService`):**
    -   Corrección de `TypeError`: el servicio pasaba `producto_id` (int) en lugar del objeto `producto` a `safe_get_or_create_stock`.
    -   Sincronización de precisión decimal: `.quantize(Decimal('0.01'))` aplicado en todas las descargas y reversiones para evitar `DataError` en SQL Server.
    -   Suite TDD permanente: `gestion/tests/test_descarga_quimicos_tdd.py` con cobertura del ciclo de vida completo, validada contra SQL Server.

-   **[x] Corrección de Bugs Críticos en `views.py`:**
    -   `perform_update`: import faltante de `rest_framework.exceptions.ValidationError` que causaba `NameError` en runtime — añadido a la cabecera del módulo.
    -   `OrdenProduccionViewSet.get_permissions()`: sobreescribía los permisos del decorador `@action`, ignorando `IsTintoreroOrAdmin` para `stock_quimicos` → 403 para rol `tintorero`. Caso añadido explícitamente.
    -   `stock_quimicos` endpoint: `.values()` retornaba claves `'producto__id'` (doble guión). Refactorizado con `.annotate()` + `.values('producto_id', ...)`.
    -   `rechazar` lote: `LoteProduccion.peso_neto_producido` puede tener >2 decimales; `MovimientoInventario.cantidad` acepta solo 2. Se aplicó `.quantize(Decimal('0.01'))` en los 4 puntos del método.

-   **[x] Reversión de Pagos (`PagoReversionService`):**
    -   Nuevo servicio transaccional para deshacer `PagoCliente` y restaurar `saldo_pendiente` del cliente.
    -   Justificación obligatoria registrada en `AuditLog`.
    -   `PaymentReconciler` disparado automáticamente post-reversión para re-reconciliar via FIFO.
    -   Endpoints: `POST /api/pagos-cliente/{id}/revertir/` y `DELETE /api/pagos-cliente/{id}/`.
    -   Frontend: botón Revertir con modal de confirmación en `VendedorDashboard.tsx`.

-   **[x] Estabilización de Infraestructura de Tests:**
    -   Eliminación de `TexCore/test_settings.py` y `TexCore/settings_test.py` para evitar uso accidental de SQLite no soportado.
    -   Corrección de multi-tenancy en `setUp`: inyección de `sede=self.sede` y `area=self.area` en `create_user`.
    -   Sincronización de `factories.py` con modelos actuales (campo `nivel_precio` en Clientes, `location` en Sedes).
    -   Migración `0051_fix_token_blacklist_mssql` trackeada en git y sincronizada en el contenedor Docker.
    -   Documentación del problema de montaje de volumen Docker (`/app` vs `/home/appuser/app`) con solución via `docker cp`.
    -   **Resultado final: 64/64 tests OK sobre SQL Server (120.696s).**

---

### Fase 11: Refactorización Arquitectónica y Tareas Asíncronas (Completado — Mayo 2026)

-   **[x] Refactorización de `gestion/views.py`:** 
    -   Extracción de lógica de negocio a módulos `gestion/services/`.
    -   División de vistas monolíticas en `gestion/views/` por dominio (`core`, `sales`, `production`, `catalog`, etc.).
    -   Implementación de `RegistroLoteService` para desacoplar la lógica de producción de la API.

-   **[x] Integración de Redis + Celery:**
    -   Arquitectura de tareas asíncronas para evitar bloqueo de workers Gunicorn.
    -   Implementación de `async_export_report` para exportaciones pesadas.
    -   Soporte para cálculo de MRP en background.

-   **[ ] OpenTelemetry:** Trazabilidad distribuida entre el monolito y los servicios satélites para observabilidad en producción.

-   **[ ] `saldo_resultante` via window function:** Calcular el saldo del Kardex con `SUM() OVER (PARTITION BY ...)` en lugar del valor desnormalizado, para eliminar riesgo de inconsistencias al editar movimientos.

---

### Fase 12: Control de Mermas y Excelencia Operativa (En Progreso)

Esta fase tiene como objetivo elevar a TexCore de un sistema de registro a un Sistema de gestión de órdenes de producción de manufactura que proporcione visibilidad financiera y de eficiencia operativa.

#### Implementado ✅ (Mayo–Junio 2026)

-   **[x] Registro de Mermas en Producción:**
    -   Modificación de `LoteProduccion` para incluir `peso_merma` y motivos categorizados.
    -   Actualización del Kardex para registrar movimientos de tipo `MERMA`.
    -   Interfaz para operarios en `OperarioDashboard` para ingreso rápido de desperdicios.
-   **[x] Trazabilidad Inversa (Genealogía):**
    -   Endpoint para consultar el historial completo de un lote (Materia Prima -> Máquina -> Operario -> Químicos Consumidos).
-   **[x] Auditoría en Logs (RFC 5424):**
    -   Inyección de datos estructurados en logs de backend para eventos de producción y calidad.
-   **[x] Merma Vendible por Máquina (Junio 2026 — ver Fase 14):**
    -   `Maquina.producto_merma` + `Maquina.bodega_merma`: la merma se convierte en producto vendible en stock con trazabilidad completa en Kardex (`documento_ref='MERMA-*'`, COBIT MEA01).

#### Próximas Tareas 📋

-   **[ ] Costeo Dinámico de Producción:**
    -   **Tarea:** Implementar un motor de costos que calcule el valor real de un `LoteProduccion` sumando: Costo MP (Kardex) + Costo Químicos (Descarga) + Costo Operativo (Tiempo).
    -   **Objetivo:** Permitir a la gerencia ver el Margen de Utilidad Bruta antes del despacho.
-   **[ ] Dashboard de Eficiencia (OEE):**
    -   **Tarea:** Crear una vista gerencial para el `Jefe de Área` que muestre el OEE (Overall Equipment Effectiveness) combinando Disponibilidad, Rendimiento y Calidad usando los movimientos `MERMA-*` del Kardex.
    -   **Objetivo:** Identificar las máquinas y operarios que generan más merma o tiempos muertos.
-   **[ ] Control de Tiempos Muertos:**
    -   **Tarea:** Permitir a los operarios registrar "Pausas" justificadas (ej: limpieza, falla eléctrica) para separar el tiempo productivo del inactivo.

---

### Fase 13: Independencia Total de Microservicios — API Interna JWT RS256 (Completado — Mayo 2026)

Esta fase elimina el acoplamiento de base de datos entre los microservicios (`scanning_service`, `reporting_excel`) y la base de datos `texcore_db`. A partir de ahora, cada microservicio es un **cliente HTTP del backend Django**, siguiendo el patrón **Database-per-Service** con autenticación por **Service Tokens RS256**.

#### Implementado ✅ (27 Mayo 2026)

-   **[x] Nueva app Django `internal_api`:**
    -   **ServiceCredential (ISO 27001 A.9.2):** Identidades de servicio con `secret_hash` bcrypt y `allowed_scopes`. Tabla `internal_service_credential`.
    -   **JWTServiceAuthentication:** Backend DRF con validación Bearer RS256; retorna `ServicePrincipal` como `request.user`.
    -   **IsInternalService + HasScope (COBIT DSS06):** Permisos granulares por scope (`lotes:read`, `reports:read`).
    -   **AuditLogger (RFC 5424):** Logging estructurado para todos los accesos internos.
    -   **20 endpoints bajo `/api/internal/v1/`:** 2 de autenticación, 1 de escaneo, 17 de reportes.
    -   **`seed_service_credentials`:** Command idempotente para crear credenciales desde variables de entorno. Ejecutado en `entrypoint.sh` tras `migrate`.

-   **[x] `scanning_service` — Eliminación de SQLAlchemy:**
    -   Eliminados: `src/database.py`, `src/models.py`, dependencias `sqlalchemy` y `pyodbc`.
    -   Nuevos: `src/domain/models.py` (dataclasses puras), `src/infrastructure/jwt_token_manager.py`, `src/infrastructure/django_client.py` (`DjangoApiClient` con circuit breaker de 3 errores y caché de stock).
    -   `depends_on` migrado de `db` a `backend (service_healthy)`.

-   **[x] `reporting_excel` — Eliminación de pyodbc:**
    -   Eliminados: `src/database.py`, `src/repositories/sql_repository.py`, dependencia `pyodbc`.
    -   Nuevos: `src/infrastructure/jwt_token_manager.py`, `src/infrastructure/django_client.py` (`DjangoReportRepository` con `_SP_MAPPING` de 18 entradas SP→REST).
    -   Middleware JWT Bearer reemplaza `X-Internal-Key`.

-   **[x] Fix de Seguridad — Token Type Confusion (MEDIUM, ISO 27001 A.9.4):**
    -   `reporting_excel` middleware ahora valida `type == "service_access"` e `iss == "texcore"` tras el decode RS256, rechazando refresh tokens usados como access tokens.

-   **[x] Infraestructura:**
    -   `docker-compose.yml`: variables `DB_*` removidas de microservicios; `INTERNAL_JWT_PRIVATE_KEY`, `INTERNAL_JWT_PUBLIC_KEY`, `SCANNING_SERVICE_SECRET`, `REPORTING_SERVICE_SECRET` añadidas.
    -   `.env.example` actualizado con guía de generación de claves RSA.
    -   `entrypoint.sh`: paso `seed_service_credentials` añadido.

-   **[x] Pruebas (ISTQB — EP + BVA + STT):**
    -   8 suites de tests nuevas cubriendo `internal_api` (modelos, auth, views) y adaptadores HTTP de ambos microservicios con mocks `respx`.

-   **[x] Proxy de Reportes migrado a JWT RS256 dinámico (Junio 2026):**
    -   `JWTServiceAuthentication.generate_token()` — nuevo método estático que centraliza la generación de tokens RS256 con scopes explícitos (ISO 27001 A.9.4).
    -   `ReportingProxyView` genera token `Bearer` en cada llamada al microservicio; `REPORTING_INTERNAL_KEY` eliminado del sistema.
    -   Nginx: bloque `location /api/reporting/` comentado en ambos servidores — las peticiones de reportes pasan ahora por el backend Django como proxy autenticado con JWT.
    -   **Resultado:** ningún componente del sistema usa secrets estáticos para comunicación interna.

-   **[x] Limpieza completa de `REPORTING_INTERNAL_KEY` en todo el stack (Junio 2026):**
    -   Eliminada de `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`, `.env.test`.
    -   Eliminada de los pipelines CI/CD: `.gitlab-ci.yml`, `.github/workflows/ci.yml` y `.github/workflows/cd.yml` migrados a `INTERNAL_JWT_PRIVATE_KEY` / `INTERNAL_JWT_PUBLIC_KEY`.
    -   Tests de `reporting_excel` migrados de `X-Internal-Key` a `Authorization: Bearer` con fixture `bypass_jwt` que parchea `jwt.decode` para entornos de test sin claves RSA reales.
    -   **Resultado:** cero referencias a `REPORTING_INTERNAL_KEY` en el repositorio.

-   **[x] Tests de microservicios estabilizados post-Fase 13/14 (Junio 2026):**
    -   `scanning_service`: `get_validation_service` re-expuesta como `Depends()` para tests; mocks unitarios alineados con `producto_salida` (Fase 14); `httpx` pineado a `<0.28` para compatibilidad con TestClient. **33/33 tests OK.**
    -   `reporting_excel`: conftest reescrito con setup de env antes de import y mocks de `DjangoReportRepository.execute_sp`. **27/27 tests OK.**

---

### Fase 14: Producción Flexible — Transformación, Mezcla de Lotes y Merma Vendible (Completado — Junio 2026)

Esta fase convierte TexCore en un Sistema de gestión de órdenes de producción de manufactura textil verdaderamente configurable: cada empresa define su propio flujo de transformación de productos, puede mezclar múltiples lotes de entrada, y registra la merma como un producto vendible. Controles alineados a **ISO 27001 A.9.4, A.12.4** y **COBIT DSS06, MEA01**.

#### Implementado ✅ (1 Junio 2026)

-   **[x] Modelo de Transformación en `OrdenProduccion`:**
    -   `producto` → `producto_entrada` + nuevo `producto_salida`: cada OP define explícitamente qué producto consume y cuál genera.
    -   `bodega` → `bodega_entrada` + nuevo `bodega_salida`: trazabilidad completa del flujo de stock entre bodegas.
    -   Migraciones `0060`–`0064`: RenameField atómico + AddField + backfill de datos existentes.

-   **[x] Mezcla de Lotes (`ComponenteMezclaOP`):**
    -   Nuevo modelo que define la receta de mezcla por OP (ej: 50% algodón + 50% poliéster): `orden`, `producto`, `bodega`, `porcentaje`, `cantidad_kg`.
    -   `CheckConstraint`: `porcentaje` en rango (0, 100]. COBIT DSS06: `SUM(porcentaje) == 100` validado en serializer y service.
    -   Auditoría automática vía `AuditableModelMixin` (ISO 27001 A.12.4).

-   **[x] Trazabilidad de Consumo (`ConsumoLoteDetalle`):**
    -   Nuevo modelo **inmutable** que registra qué lote de origen se consumió y en qué cantidad al producir un lote de mezcla.
    -   Solo puede eliminarse mediante el endpoint `rechazar/` con justificación obligatoria — sin UPDATE directo (ISO 27001 A.12.4).
    -   Campo `genera_nuevo_lote` para distinguir transformaciones reales de simples reasignaciones de lote.

-   **[x] Merma Vendible por Máquina (`MermaStockService`):**
    -   `Maquina` ahora tiene `producto_merma` y `bodega_merma`: cada empresa configura qué tipo de desperdicio genera cada máquina.
    -   `MermaStockService.registrar()` — si `peso_merma > 0` y la máquina tiene merma configurada, crea `StockBodega` vendible y `MovimientoInventario(tipo=PRODUCCION)` con `documento_ref='MERMA-{codigo}'` para KPIs de eficiencia (COBIT MEA01).
    -   `MermaStockService.revertir()` — reversión atómica de la merma al rechazar un lote.

-   **[x] Bodegas Intermedias por Máquina — `Maquina.bodega_entrada` / `Maquina.bodega_salida` (Junio 2026):**
    -   Dos nuevas FK opcionales en `Maquina` que definen rutas de stock específicas por estación de trabajo, con prioridad sobre las bodegas de la OP.
    -   `RegistroLoteService` resuelve la máquina antes de calcular bodegas y aplica las bodegas de la máquina si están configuradas — habilita flujos de transformación con bodegas intermedias.
    -   `MaquinaSerializer` expone `bodega_entrada_nombre` y `bodega_salida_nombre` como campos de solo lectura.
    -   Migración `0066_maquina_bodega_entrada_maquina_bodega_salida_and_more` creada.

-   **[x] `ConsumoMezclaService` (SRP):**
    -   Valida `sum(cantidad_kg) == consumo_total ± 0.01 kg` (COBIT DSS06). Descuenta stock de cada lote origen con `select_for_update()`. Rollback automático si stock insuficiente.
    -   `revertir()` restaura el stock de todos los componentes de la mezcla.

-   **[x] `RegistroLoteService` actualizado:**
    -   Usa `producto_entrada/bodega_entrada` para consumo y `producto_salida/bodega_salida` para producción.
    -   Delega mezcla a `ConsumoMezclaService` y merma vendible a `MermaStockService` (SRP).
    -   Compatibilidad hacia atrás con OPs existentes.

-   **[x] API — Nuevos endpoints:**
    -   `GET/POST/PATCH/DELETE /api/componentes-mezcla/` — CRUD de receta de mezcla (`IsJefeAreaOrAdmin`).
    -   `GET /api/consumo-lote-detalle/` — Lectura de trazabilidad de consumo (inmutable desde API).
    -   `POST /api/lotes-produccion/{id}/rechazar/` — Actualizado: revierte mezcla y merma vendible antes del stock.

-   **[x] Frontend — Nuevos componentes y actualizaciones:**
    -   `ManageMaquinas.tsx` (nuevo) — CRUD completo de máquinas con sección "Merma Vendible" (producto + bodega). AlertDialog con justificación obligatoria.
    -   `ComponenteMezclaPanel.tsx` (nuevo) — CRUD de receta de mezcla con barra visual de porcentajes, validación `sum=100%` en tiempo real.
    -   `ManageOrdenesProduccion.tsx` — Formulario OP con 4 selectores: `producto_entrada`, `bodega_entrada`, `producto_salida`, `bodega_salida`.
    -   `OperarioDashboard.tsx` — Sección de consumos de mezcla al registrar lotes.
    -   `ManageProductos.tsx` — Tipo `merma` + filtro por tipo.
    -   `frontend/src/types/produccion.ts` (nuevo) — Interfaces TypeScript completas para toda la funcionalidad.

-   **[x] Pruebas TDD (ISTQB — EP + BVA + STT):**
    -   `test_merma_stock_service.py` — 6 tests: máquina con/sin merma, peso=0 (BVA), peso mínimo (BVA), movimiento Kardex, reversión (STT).
    -   `test_consumo_mezcla_service.py` — 7 tests: mezcla válida, ConsumoLoteDetalle, suma incorrecta (BVA), stock insuficiente + rollback, movimientos Kardex, reversión restaura stock y elimina detalles (STT).
    -   `test_registro_lote_transformacion.py` — 3 tests: transformación simple, merma vendible, transición de estados (STT).
    -   `factories.py` — 7 nuevas factories: `MaquinaFactory`, `MaquinaConMermaFactory`, `OrdenProduccionFactory`, `ComponenteMezclaOPFactory`, `LoteProduccionFactory`, `ConsumoLoteDetalleFactory`, `StockBodegaFactory`.

#### Próximas Tareas 📋

-   **[x] Validación en Docker:** Ejecutar `migrate` y suite de tests sobre SQL Server cuando Docker esté disponible.
-   **[x] Consistencia `producto_salida`:** Referencias residuales a `orden_produccion.producto` corregidas en `scanning_views`, `reporting_views`, `inventory/views`, `empaque_service`, `production_views`, `scanning_service` y fixtures de tests.
-   **[ ] Dashboard de Eficiencia por Merma (COBIT MEA01):** Vista en `JefeAreaDashboard` con KPIs de merma por máquina usando `documento_ref='MERMA-*'` del Kardex.
-   **[ ] Costeo Dinámico de Producción:** Motor de costos que suma Costo MP + Costo Químicos + Costo Operativo por lote.

---

### Fase 13: Independencia Total de Servicios Satélites — API Interna JWT RS256 (Completado — Mayo 2026)

Esta fase elimina el acoplamiento de base de datos entre los servicios satélites (`scanning_service`, `reporting_excel`) y la base de datos `texcore_db`. A partir de ahora, cada servicio satélite es un **cliente HTTP del backend Django**, siguiendo el patrón **Database-per-Service** con autenticación por **Service Tokens RS256**.

#### Implementado ✅ (27 Mayo 2026)

-   **[x] Nueva app Django `internal_api`:**
    -   **ServiceCredential (ISO 27001 A.9.2):** Identidades de servicio con `secret_hash` bcrypt y `allowed_scopes`. Tabla `internal_service_credential`.
    -   **JWTServiceAuthentication:** Backend DRF con validación Bearer RS256; retorna `ServicePrincipal` como `request.user`.
    -   **IsInternalService + HasScope (COBIT DSS06):** Permisos granulares por scope (`lotes:read`, `reports:read`).
    -   **AuditLogger (RFC 5424):** Logging estructurado para todos los accesos internos.
    -   **20 endpoints bajo `/api/internal/v1/`:** 2 de autenticación, 1 de escaneo, 17 de reportes.
    -   **`seed_service_credentials`:** Command idempotente para crear credenciales desde variables de entorno. Ejecutado en `entrypoint.sh` tras `migrate`.

-   **[x] `scanning_service` — Eliminación de SQLAlchemy:**
    -   Eliminados: `src/database.py`, `src/models.py`, dependencias `sqlalchemy` y `pyodbc`.
    -   Nuevos: `src/domain/models.py` (dataclasses puras), `src/infrastructure/jwt_token_manager.py`, `src/infrastructure/django_client.py` (`DjangoApiClient` con circuit breaker de 3 errores y caché de stock).
    -   `depends_on` migrado de `db` a `backend (service_healthy)`.

-   **[x] `reporting_excel` — Eliminación de pyodbc:**
    -   Eliminados: `src/database.py`, `src/repositories/sql_repository.py`, dependencia `pyodbc`.
    -   Nuevos: `src/infrastructure/jwt_token_manager.py`, `src/infrastructure/django_client.py` (`DjangoReportRepository` con `_SP_MAPPING` de 18 entradas SP→REST).
    -   Middleware JWT Bearer reemplaza `X-Internal-Key`.

-   **[x] Fix de Seguridad — Token Type Confusion (MEDIUM, ISO 27001 A.9.4):**
    -   `reporting_excel` middleware ahora valida `type == "service_access"` e `iss == "texcore"` tras el decode RS256, rechazando refresh tokens usados como access tokens.

-   **[x] Infraestructura:**
    -   `docker-compose.yml`: variables `DB_*` removidas de servicios satélites; `INTERNAL_JWT_PRIVATE_KEY`, `INTERNAL_JWT_PUBLIC_KEY`, `SCANNING_SERVICE_SECRET`, `REPORTING_SERVICE_SECRET` añadidas.
    -   `.env.example` actualizado con guía de generación de claves RSA.
    -   `entrypoint.sh`: paso `seed_service_credentials` añadido.

-   **[x] Pruebas (ISTQB — EP + BVA + STT):**
    -   8 suites de tests nuevas cubriendo `internal_api` (modelos, auth, views) y adaptadores HTTP de ambos servicios satélites con mocks `respx`.

-   **[x] Proxy de Reportes migrado a JWT RS256 dinámico (Junio 2026):**
    -   `JWTServiceAuthentication.generate_token()` — nuevo método estático que centraliza la generación de tokens RS256 con scopes explícitos (ISO 27001 A.9.4).
    -   `ReportingProxyView` genera token `Bearer` en cada llamada al microservicio; `REPORTING_INTERNAL_KEY` eliminado del sistema.
    -   Nginx: bloque `location /api/reporting/` comentado en ambos servidores — las peticiones de reportes pasan ahora por el backend Django como proxy autenticado con JWT.
    -   **Resultado:** ningún componente del sistema usa secrets estáticos para comunicación interna.

-   **[x] Limpieza completa de `REPORTING_INTERNAL_KEY` en todo el stack (Junio 2026):**
    -   Eliminada de `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`, `.env.test`.
    -   Eliminada de los pipelines CI/CD: `.gitlab-ci.yml`, `.github/workflows/ci.yml` y `.github/workflows/cd.yml` migrados a `INTERNAL_JWT_PRIVATE_KEY` / `INTERNAL_JWT_PUBLIC_KEY`.
    -   Tests de `reporting_excel` migrados de `X-Internal-Key` a `Authorization: Bearer` con fixture `bypass_jwt` que parchea `jwt.decode` para entornos de test sin claves RSA reales.
    -   **Resultado:** cero referencias a `REPORTING_INTERNAL_KEY` en el repositorio.

-   **[x] Tests de servicios satélites de datos y reportes (Junio 2026):**
    -   `scanning_service`: `get_validation_service` re-expuesta como `Depends()` para tests; mocks unitarios alineados con `producto_salida` (Fase 14); `httpx` pineado a `<0.28` para compatibilidad con TestClient. **33/33 tests OK.**
    -   `reporting_excel`: conftest reescrito con setup de env antes de import y mocks de `DjangoReportRepository.execute_sp`. **27/27 tests OK.**

---

### Fase 15: Auditoría Local por Servicio Satélite — SQLite + SOLID + RFC 5424 (Completado — Junio 2026)

Esta fase implementa el sistema de auditoría local para los tres servicios satélites FastAPI (`scanning_service`, `printing_service`, `reporting_excel`), cumpliendo con **ISO 27001 A.10 / A.12.4** y **COBIT MEA01**. Cada servicio satélite persiste sus eventos en una BD SQLite local independiente (Database-per-Service extendido a la capa de auditoría), sin depender del backend Django.

#### Implementado ✅ (22 Junio 2026)

-   **[x] Arquitectura de auditoría (idéntica en los 3 servicios):**
    -   `src/database/engine.py` — SQLite async + WAL + PRAGMAs + `os.chmod(0o600)` (ISO 27001 A.10).
    -   `src/database/models.py` — Tabla ORM con índices selectivos (< 500 ms por INSERT).
    -   `src/database/repository.py` — `IAuditRepository` (Protocol) + `AuditRepository` (clase, DIP/SRP). `BackgroundTasks` de FastAPI para escrituras no bloqueantes.

-   **[x] `scanning_service`:** `ScanAuditLog` (11 campos), `build_scan_record()`, **12 tests ISTQB**.
-   **[x] `printing_service`:** `PrintAuditLog` (9 campos), routers `pdf.py`/`zpl.py` migrados a `Depends(get_audit_repo)`, **14 tests ISTQB**.
-   **[x] `reporting_excel`:** `ReportAuditLog` (9 campos), **15 endpoints migrados** a patrón DIP, **12 tests ISTQB**.

-   **[x] Seguridad SQLite (ISO 27001 A.10/A.12.4):**
    -   `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`.
    -   `os.chmod(db_path, 0o600)` — solo el proceso del contenedor puede leer/escribir.

-   **[x] Correcciones Pipeline CI/CD (post-implementación):**
    -   Docker path corregido en `ci.yml`/`cd.yml` (`Dockerfile.prod` en raíz → `infrastructure/docker/`).
    -   `pytest-asyncio` añadido a `printing_service` y `reporting_excel` (necesario para `@pytest.mark.asyncio`).
    -   `pytest.ini` creado con `asyncio_mode = auto` en los 3 servicios.
    -   Validación de formato inválido en 18 endpoints de `reporting_excel` (400 en vez de 500 para formato no soportado).
    -   Cobertura `reporting_excel` elevada de 79.35% → **80.07%** con 6 tests BVA nuevos.

| Métrica | Valor |
|---------|-------|
| Tests ISTQB nuevos (auditoría) | **38** (14 + 12 + 12) |
| Endpoints migrados a DIP | **17** |
| Tablas SQLite de auditoría | **3** |

---

### Fase 16: Trazabilidad Granular de Transformaciones en Cadena de Producción (Completado — Junio 2026)

Esta fase convierte el módulo de producción en un sistema de trazabilidad máquina-a-máquina: cada paso de transformación (entrada → máquina → salida + merma) se registra formando una cadena que puede cruzar múltiples áreas de producción. Controles alineados a **ISO 27001 A.12.4** y **COBIT MEA01**.

#### Implementado ✅ (23 Junio 2026)

-   **[x] Modelo `TransformacionProducto` + migración `0073`:**
    -   Campos: `orden_produccion`, `producto_entrada → producto_salida`, `maquina`, `operario`, `peso_entrada`, `peso_salida`, `merma` (calculada en `clean()`), `numero_secuencia`, `estado` (`completada`/`rechazada`), `observaciones`.
    -   `UniqueConstraint(orden_produccion, numero_secuencia)` + `CheckConstraint(merma >= 0)`.
    -   Auditoría completa vía `AuditableModelMixin` (ISO 27001 A.12.4).

-   **[x] `TransformacionService` (SOLID, atómico, RFC 5424):**
    -   `@transaction.atomic` + `select_for_update()` — concurrencia segura.
    -   Validación de continuidad de cadena: `producto_entrada` debe coincidir con `producto_salida` de la transformación anterior.
    -   Aislamiento por área Y por sede — operarios solo pueden registrar en su área/sede.

-   **[x] `TrazabilidadService`:**
    -   Timeline completo con merma acumulada (%) desde el primer peso de entrada.
    -   Filtra transformaciones rechazadas. Detección de ciclos (conjunto `visited`).
    -   Cruza áreas via `TransferenciaInterarea` para reconstruir la cadena multi-área.

-   **[x] 3 nuevos endpoints en `/api/ordenes-produccion/{id}/`:**
    -   `POST registrar-transformacion/` — crea transformación (Operario/JefeArea).
    -   `GET transformaciones/` — lista transformaciones de la orden.
    -   `GET trazabilidad/` — árbol completo con merma acumulada %.

-   **[x] Frontend — Nuevos componentes y actualización de dashboards:**
    -   `RegistrarTransformacion.tsx` — Dialog: producto salida, máquina, pesos, observaciones. Merma en tiempo real.
    -   `TrazabilidadProducto.tsx` — `NivelTrazabilidad` recursivo con merma acumulada. `allowRegister` prop para habilitar registro.
    -   `OperarioDashboard.tsx`: grilla 2 botones (Avance + Transformación).
    -   `JefeAreaDashboard.tsx`: sección "Producción en Curso — Trazabilidad" con `allowRegister`.
    -   `ManageOrdenesProduccion.tsx` (Jefe Planta): trazabilidad embebida read-only en `OrdenDetalleSheet`.

-   **[x] Pruebas TDD (ISTQB — EP, BVA, caja blanca/negra, RBAC, integración):**
    -   42 tests nuevos: modelo, servicio, timeline y endpoints. **284 tests totales — 0 fallos.**

-   **[x] Correcciones de entorno (24 Junio 2026):**
    -   `.env` creado con orígenes Vite `:5173`.
    -   `manage.py` prioridad de carga invertida (`.env` primero, `.env.test` como fallback CI).
    -   `.env.example` completado (`CSRF_TRUSTED_ORIGINS` + ports corregidos).
    -   `docker-compose.windows.yml` variables fail-fast añadidas al backend.
    -   `deploy.ps1` con detección automática Docker Compose v1/v2.

---

### Fase 17: Células de Manufactura Flexibles y Gestión Multi-Línea para Jefe de Área (Completado — Julio 2026)

Esta fase habilita al Jefe de Área la gestión de múltiples líneas de producción (Células de Manufactura Flexibles) dentro de su área, optimizando la asignación de máquinas y respetando los principios de ISA-95 y Teoría de Restricciones (TOC).

#### Implementado ✅ (20 Julio 2026)

-   **[x] Modelo `LineaProduccion` + Migración `0074`:**
    -   Campos: `nombre`, `descripcion`, `area` (FK), `estado` (`activa`/`inactiva`), `maquinas` (M2M).
    -   Constraint `unique_together = ('nombre', 'area')`.
    -   Control de capacidad (TOC): La línea es una agrupación organizativa. Las colas y capacidades se calculan a nivel de **Área** para permitir máquinas compartidas entre líneas sin duplicación de capacidad fantasma.

-   **[x] API ViewSet & Serializers (`production_views.py` / `serializers.py`):**
    -   `LineaProduccionViewSet`: Endpoint `/api/lineas-produccion/` con filtrado y aislamiento estricto por Sede y Área.
    -   `LineaProduccionSerializer`: Validación de pertenencia de máquinas al área y cálculo del atributo dinámico `compartida`.

-   **[x] Frontend — Componente `ManageLineas.tsx` & Dashboard:**
    -   `ManageLineas.tsx`: CRUD completo de líneas de producción, asignación/desasignación de máquinas mediante checkboxes, badges de estado y toasts de feedback.
    -   Integración directa en `JefeAreaDashboard.tsx` para control operativo del Jefe de Área.

-   **[x] Cobertura de Pruebas & Documentación:**
    -   Suite de pruebas frontend `ManageLineas.test.tsx` (16/16 tests de comportamiento pasando al 100%).
    -   Pruebas backend en `test_lineas_produccion.py`.
    -   Actualización del flujo `.agent/workflows/jefe-area.md` y `docs/historias-usuarios/ROLES_Y_PERMISOS.md`.

