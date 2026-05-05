# Changelog

## Mayo 2026

### 4 de Mayo de 2026

#### Implementación de Sistema de Reversión de Pagos para Rol Vendedor

Se ha completado la implementación de un sistema de reversión de pagos (abonos) que permite deshacer pagos registrados y restaurar automáticamente la deuda del cliente al monto anterior, siguiendo los mismos patrones arquitectónicos del sistema de reversión de despachos.

**Características Implementadas:**

- **Service Layer (`gestion/services/pago_reversion.py` - NUEVO)**:
    - `PagoReversionService` con método transaccional para reversión de pagos
    - `revertir_pago()` — Elimina PagoCliente y restaura saldo_pendiente del cliente
    - Justificación obligatoria registrada en auditoría (AuditLog)
    - @transaction.atomic garantiza consistencia ("todo o nada")
    - Cálculo automático: saldo_anterior_pago = saldo_actual + monto_pago

- **Backend Views (gestion/views.py - ACTUALIZADO)**:
    - `PagoClienteViewSet` — Método `destroy()` validación de justificación
    - @action `revertir` — POST /pagos-cliente/{id}/revertir/ (endpoint amigable)
    - DELETE /pagos-cliente/{id}/ también soportado con justificación en body
    - HTTP 400 si justificación falta, HTTP 204 si éxito
    - Trigger automático de PaymentReconciler post-reversión

- **Frontend UI (VendedorDashboard.tsx - ACTUALIZADO)**:
    - Botón 🔄 Revertir (rojo) en tabla de pagos/abonos
    - Modal de confirmación con TextArea obligatorio para justificación (mín. 5 caracteres)
    - Advertencia visual: "Esta acción restaurará la deuda del cliente al monto anterior"
    - Muestra fecha, monto y método de pago a revertir
    - Estado de carga con spinner durante reversión
    - Toast notifications para éxito/error

- **Lógica de Reversión Simplificada** (FIFO automático):
    - No hay mapeo explícito pago → factura (sistema usa FIFO automático)
    - Pagos son registros de control, no ligados a facturas específicas
    - Reversión solo restaura deuda: saldo = saldo_actual + monto_pago
    - FIFO reconciliación manejada por PaymentReconciler post-reversión

- **Testing de Integración**:
    - 4 test cases en `gestion/tests/test_pago_reversion.py`
    - Test 1: Validar restauración correcta de deuda del cliente
    - Test 2: Justificación obligatoria (ValueError si vacía)
    - Test 3: Múltiples pagos, reversión selectiva de uno
    - Test 4: Transaccionalidad garantizada (eliminación atómica)
    - Tests API: endpoint requiere justificación (HTTP 400 si vacía)

- **Auditoría Completa**:
    - AuditLog creado en eliminación de PagoCliente
    - Justificación registrada en auditlog.justificacion
    - Usuario registrado en auditlog.usuario
    - Timestamp automático

**Patrones SOLID Aplicados:**
- **SRP**: PagoReversionService solo gestiona reversión
- **OCP**: Service extensible para diferentes estrategias sin modificar core
- **LSP**: PagoCliente respeta contrato de auditoría (AuditLog)
- **ISP**: ViewSet expone endpoints relevantes (revertir/consultar)
- **DIP**: Service depende de abstracciones, no de implementaciones concretas

**Arquitectura Consistente:**
- Mismo patrón Service Layer + ViewSet que DespachoReversionService
- Mismo patrón Modal + justificación que HistorialDespachos.tsx
- Transaccionalidad garantizada con @transaction.atomic
- PaymentReconciler trigger automático post-reversión

## Marzo 2026

### 4 de Marzo de 2026

#### Implementación de Sistema de Reversión de Despachos con Restauración Automática de Stock

Se ha completado la implementación de un sistema robusto de reversión de despachos que permite deshacer envíos y restaurar automáticamente todo el stock de químicos a las bodegas de origen, siguiendo los mismos patrones arquitectónicos del sistema de descarga automática de químicos.

**Características Implementadas:**

- **Service Layer (`inventory/services/despacho_reversion.py` - NUEVO)**:
    - `DespachoReversionService` con métodos transaccionales para reversión completa
    - `revertir_despacho()` — Restaura stock en bodegas origen + revierte descargas químicas
    - `_revertir_descargas_quimicas()` — Marca DescargaQuimicoOP como 'revertida'
    - Justificación obligatoria registrada en auditoría
    - @transaction.atomic garantiza consistencia ("todo o nada")

- **Backend Views (inventory/views.py - ACTUALIZADO)**:
    - `HistorialDespachoViewSet` cambio: ReadOnlyModelViewSet → ModelViewSet
    - Método `destroy()` — DELETE con validación de justificación (HTTP 400 si falta)
    - @action `revertir` — POST /historial-despachos/{id}/revertir/ (alternativa amigable)
    - Ambos endpoints retornan estadísticas: movimientos_creados, lotes_revertidos

- **Frontend UI (HistorialDespachos.tsx - ACTUALIZADO)**:
    - Botón 🔄 Revertir (rojo) en tabla de despachos
    - Modal de confirmación con TextArea obligatorio para justificación
    - Advertencia visual: "Se restaurarán X kg a bodegas"
    - Estado de carga con spinner durante reversión
    - Toast notifications para éxito/error

- **Restauración Automática**:
    - Stock restaurado a valor original en bodega origen
    - MovimientoInventario tipo='DEVOLUCION' creado para auditoría
    - DescargaQuimicoOP marcadas como 'revertida' con justificación
    - PedidoVenta revertidos a estado 'pendiente' (disponibles para nuevo despacho)
    - Todas las operaciones transaccionales con rollback automático en error

- **Testing de Integración**:
    - 4 test cases en `inventory/tests/test_despacho_reversion.py`
    - Test 1: Validar restauración correcta de cantidades
    - Test 2: Justificación obligatoria (ValueError si vacía)
    - Test 3: PedidoVenta revierte a 'pendiente'
    - Test 4: Transaccionalidad garantizada (rollback en error)

- **Documentación Completa**:
    - `DOCUMENTACION_REVERSION_DESPACHO.md` — Especificación técnica detallada
    - `RESUMEN_IMPLEMENTACION_REVERSION_DESPACHO.md` — Resumen ejecutivo
    - `GUIA_RAPIDA_REVERSION_DESPACHO.md` — Quick reference para usuarios

**Principios SOLID Aplicados:**
- SRP: Service layer aislada para lógica de reversión
- OCP: Extensible para diferentes estrategias sin modificar core
- DIP: Depende de abstracciones (safe_get_or_create_stock), no concretos
- ISP: Endpoints separados para lecturas vs. escrituras

**Patrones de Diseño:**
- Service Layer — Separación lógica de negocio
- Template Method — Secuencia fija con pasos delegados
- Audit Trail — MovimientoInventario DEVOLUCION inmutable
- Transactional Script — @transaction.atomic garantiza consistencia

**Arquitectura Verificada:**
- ✅ Reversión bidireccional: Dispatch → Stock + DescargaQuimicoOP
- ✅ Justificación registrada en múltiples niveles (API, Frontend, DB)
- ✅ Thread-safe: Usa savepoints para acceso concurrente
- ✅ Idempotente: Campo es_devolucion=True previene dobles reversiones
- ✅ Permiso-basado: IsDespachoWriter requerido

---

### 10 de Marzo de 2026

#### Implementación de Arquitectura de Navegación Híbrida y Refactorización Core

Se ha completado una mejora arquitectónica significativa en el frontend para adoptar un modelo de Navegación Híbrida, junto con refactorizaciones críticas en la base de datos y la interfaz de usuario.

**Características Implementadas:**

- **Arquitectura de Navegación Híbrida (Frontend)**:
    - Transición de estado local (`useState`) a estado en URL mediante `react-router-dom` (`useSearchParams`).
    - Las vistas de datos ahora sincronizan paginación, filtros de búsqueda, ordenamiento y pestañas activas directamente con la URL (ej. `?page=2&tab=pedidos`).
    - Permite a los usuarios utilizar los botones nativos del navegador ("Atrás/Adelante") y compartir enlaces exactos a estados específicos de la interfaz.
    - Componentes refactorizados para escuchar la URL como única fuente de verdad, optimizando re-renders y peticiones a la API.
- **Refactorización de Base de Datos y Lógica de Negocio (Backend)**:
    - **Cálculos de IVA**: Ajuste y optimización de las rutinas de cálculo de impuestos en el backend.
    - **Limpieza de Esquema**: Eliminación del campo obsoleto `pedidos_ids` en `MovimientoInventario` y sus migraciones correspondientes, simplificando la estructura de datos.
    - **Validación y Pruebas**: Adaptación de la suite de pruebas automatizada (`tests_integrados.py` y demás) a la nueva lógica de base de datos, garantizando la estabilidad tras la limpieza.
- **Mejoras de UI y Experiencia de Usuario**:
    - **Dashboard de Tintorero**: Resolución de problemas visuales severos (superposición de elementos de interfaz en el ingreso de químicos).
    - **Componente de Fórmulas**: Refactorización estructural de `FormulaQuimica.tsx` para mejorar la organización del código y prevenir la superposición de botones de acción ("Cancelar", "Agregar Formula", "Agregar Insumos Químicos").
- **Historial de Despachos (Módulo de Inventario)**:
    - Implementación de API RESTFul para consulta de despachos pasados, optimizada para evitar N+1 queries.
    - Nuevo componente frontend `HistorialDespachos.tsx` con soporte para filtros de fecha y paginación vía URL.
    - Modal detallado para la inspección de lotes y pedidos asociados a cada salida.
- **Verificación de Seguridad y RBAC (Control de Acceso)**:
    - Creación de una matriz de pruebas unitarias (`test_roles_rbac.py`) para validar el acceso de 11 roles operativos diferentes.
    - Implementación de clases de permisos granulares (`IsDespachoReader`, `IsDespachoWriter`) para restringir acciones sensibles (como procesar despachos) a roles de ejecución únicamente.
    - Integración de la suite de pruebas de seguridad en la tubería global de integración continua.
- **Infraestructura y Estabilidad**:
    - **Resolución de Error 502 Bad Gateway**: Diagnóstico y reparación de fallos de comunicación entre el proxy inverso Nginx y el backend.
    - Fusión exitosa de los cambios de desarrollo (`featchanges`) al entorno de pruebas (`staging`), incluyendo resolución de conflictos en modelos y migraciones.

---

## Febrero 2026

### 18 de Febrero de 2026

#### Reactivación y Potenciación de Módulos Operativos (Jefe de Área y Operario)

Se ha completado la implementación funcional de los roles de "Jefe de Área" y "Operario", resolviendo problemas críticos de permisos y estableciendo un flujo de trabajo de producción de extremo a extremo (Assignación -> Ejecución).

**Características Implementadas:**

- **Rol Jefe de Área (Optimizado)**:
    - **Resolución de Permisos (Fix 403)**: Se ajustaron las políticas de seguridad en el backend (`views.py`) para permitir a los jefes de área gestionar máquinas y órdenes sin restricciones excesivas de Django Model Permissions.
    - **Cálculo Real de Carga de Máquina**: Implementación de lógica en tiempo real que compara la producción del turno vs. la capacidad teórica de la máquina para mostrar un % de carga real.
    - **Mejoras de UI/UX**: Visualización destacada de "Observaciones" (notas del Jefe de Planta) y detalles técnicos (Fórmula, Peso Requerido) en las tarjetas de asignación.

- **Rol Operario (Nuevo Dashboard)**:
    - **Panel de Ejecución Simplificado**: Interfaz limpia diseñada para planta, mostrando solo las Órdenes de Producción asignadas específicamente al usuario logueado.
    - **Registro Rápido de Lotes**: Funcionalidad "One-Click" para registrar avance (Peso Neto + Unidades) directamente desde la tarjeta de la orden.
    - **Filtrado de Seguridad**: El backend ahora filtra automáticamente las órdenes, asegurando que cada operario solo vea su trabajo asignado.

- **Seguridad**:
    - **Estandarización de Lectura**: Se abrieron permisos de lectura (`list`/`retrieve`) para usuarios autenticados en modelos clave (Máquina, OrdenProducción), facilitando la integración de dashboards.
    - **Escritura Controlada**: Se reforzaron los permisos de escritura para garantizar que solo roles de liderazgo puedan alterar la configuración de máquinas o asignaciones.

### 13 de Febrero de 2026

#### Optimización de Impresión y Ventas (Microservicio de Impresión)

Se ha implementado una arquitectura de microservicios para la generación de documentos PDF (Notas de Venta) y etiquetas ZPL, desacoplando esta lógica del núcleo principal y añadiendo mejoras al módulo de Vendedores.

**Características Implementadas:**

- **Microservicio de Impresión (Printing Service)**:
    - Nuevo contenedor Docker (`printing`) basado en FastAPI.
    - Generación de PDF de Notas de Venta con diseño profesional y logo dinámico de la Sede/Empresa.
    - Generación de Código ZPL para etiquetado de productos terminados.
    - Comunicación interna REST API con el backend Django.
- **Reconciliación Automática de Pagos**:
    - Implementación de lógica FIFO (First In, First Out) en `gestion/utils.py`.
    - Detección automática de pagos: el sistema marca automáticamente los pedidos como "Pagados" utilizando el saldo disponible del cliente.
    - Actualización en tiempo real del estado de deuda en el Dashboard de Vendedor.
- **Dashboard de Vendedor**:
    - Descarga directa de PDF desde el navegador (`download_pdf`).
    - Visualización clara del estado de pago ("Pendiente" vs "Pagado") con estilos visuales mejorados.
    - Historial de transacciones y abonos integrado.

### 10 de Febrero de 2026

#### Implementación del Módulo de Empaquetado y Despacho

Se ha completado el ciclo de producción con la integración del módulo final de Empaquetado, permitiendo la transformación de órdenes de producción en unidades logísticas listas para despacho.

**Características Implementadas:**

- **Nuevo Rol y Dashboard**: Se creó el rol `Empaquetado` con un dashboard dedicado (`EmpaquetadoDashboard`) optimizado para pantallas táctiles y estaciones de trabajo en planta.
- **Gestión de Lotes de Producto Terminado**:
    - Registro de peso bruto, tara y cálculo automático de peso neto.
    - Selección de tipo de presentación (Caja, Funda, Cono, Rollo).
    - Generación y simulación de impresión de etiquetas ZPL para impresoras Zebra.
- **Validaciones de Negocio**:
    - Backend (`serializers.py`): Validación estricta de que el peso neto sea positivo y coherente.
    - Frontend (`zod`): Validación de formularios en tiempo real para evitar errores de ingreso de datos.
- **Infraestructura Git**:
    - Consolidación del flujo de trabajo en ramas `master` (producción) y `staging` (pruebas), eliminando ramas temporales de características.

---

## Enero 2026

### 26 de Enero de 2026

#### Implementación de Pipeline CI/CD Completo

Se ha implementado un flujo de trabajo de Integración y Despliegue Continuo (CI/CD) robusto utilizando GitLab CI.

**Características Implementadas:**

- **Build & Push**: Las imágenes de Docker ahora se construyen en el runner de CI y se almacenan en el GitLab Container Registry, mejorando la consistencia y velocidad de despliegue.
- **Despliegue Automatizado**: El servidor de producción descarga y ejecuta las imágenes pre-construidas.
- **Rollback Manual**: Se añadió una capacidad de "vuelta atrás" (rollback) manual que permite revertir el servidor a la versión inmediatamente anterior con un solo clic en GitLab.
- **Health Checks**: Verificación automática de disponibilidad post-despliegue.

---

## Diciembre 2025

### 22 de Diciembre de 2025

#### Estabilización del Entorno de Desarrollo Docker

Se realizó una refactorización completa del entorno de Docker para solucionar problemas críticos de arranque, portabilidad y fiabilidad, resultando en un proceso de inicio de un solo comando (`docker-compose up`).

**Problemas Resueltos:**

1.  **Error de Finales de Línea en Scripts (`bash\r`):**
    - Se corrigieron los finales de línea de Windows (CRLF) en los scripts `entrypoint.sh` y `wait-for-it.sh`, que causaban fallos al ejecutarse en el contenedor Linux. Se documentó la solución para futuros desarrolladores en Windows.

2.  **Automatización de la Creación de la Base de Datos:**
    - Anteriormente, la base de datos `texcore_db` no se creaba automáticamente, lo que provocaba errores de conexión (Error 4060 en SQL Server) y que las migraciones se ejecutaran en la base de datos `master` incorrecta.
    - Se implementó la ejecución del script `create_db.py` desde el `entrypoint.sh` del backend para garantizar que la base de datos se cree de forma automática antes de aplicar las migraciones.

3.  **Fiabilidad del Inicio:**
    - Se corrigió el script `wait-for-it.sh` para que manejara correctamente los argumentos y no fallara.
    - Se añadió la creación automática del directorio de logs (`/app/logs`) para prevenir errores de la aplicación Django al iniciar.

**Estado Actual:**

- El entorno de desarrollo es completamente estable.
- El comando `docker-compose up` ahora levanta, inicializa (crea la BD, aplica migraciones) y ejecuta todo el stack de la aplicación sin necesidad de pasos manuales adicionales.
- Se ha mejorado significativamente la experiencia del desarrollador y la portabilidad del proyecto.

## Noviembre 2025

### 13 de Noviembre de 2025

#### Correcciones y Mejoras de Estabilidad

Se realizó una sesión intensiva de depuración y refactorización para estabilizar la aplicación y asegurar la correcta persistencia de los datos.

**Problema Inicial:**

- Las operaciones CRUD (Crear, Leer, Actualizar, Eliminar) en el módulo de gestión de usuarios no persistían los datos después de reiniciar el servidor o cerrar sesión.

**Proceso de Depuración y Soluciones:**

1.  **Refactorización del Estado del Frontend:**
    - Se diagnosticó que el estado se manejaba localmente en el componente `ManageUsers` y no se comunicaba con el backend.
    - Se refactorizó la lógica para centralizar el estado y las llamadas a la API en el componente padre `AdminSistemasDashboard`, pasando los datos y las funciones como `props` al componente hijo.

2.  **Resolución de Problemas de Compilación:**
    - Se encontró y corrigió una versión inválida (`0.0.0`) del paquete `react-scripts` en `frontend/package.json`, que impedía que el servidor de desarrollo se iniciara correctamente.
    - La actualización de `react-scripts` reveló una gran cantidad de errores de tipo (TypeScript) en todo el proyecto debido a un chequeo más estricto.
    - Se corrigió un error de sintaxis fatal en `src/lib/auth.tsx` que impedía la exportación del contexto de autenticación.
    - Se desactivaron temporalmente los dashboards no esenciales (`Jefe de Área`, `Operario`, etc.) que dependían de datos de prueba (`mockData`) inconsistentes, vaciando su contenido para permitir la compilación.

3.  **Resolución de Problemas de Autenticación y Roles:**
    - Se diagnosticó que la aplicación no reconocía el rol del usuario después de iniciar sesión ("Rol no reconocido").
    - Mediante logs, se descubrió que una llamada a la API para obtener la lista de roles (`/api/groups/`) estaba fallando con un error `401 Unauthorized`.
    - Se corrigió el backend (`gestion/views.py`) para permitir el acceso público a la lista de roles.
    - Se detectó que el servidor de backend no estaba aplicando los cambios, probablemente debido a un proceso "zombie".
    - Se modificó el script `seed_data.py` para forzar la recreación de los usuarios de prueba, asegurando la consistencia de los IDs de los grupos en la base de datos.
    - Se proveyeron instrucciones explícitas para forzar el reinicio del servidor de backend y asegurar que todos los cambios fueran aplicados.

**Estado Actual:**

- La aplicación compila exitosamente.
- El inicio de sesión y el reconocimiento de roles funcionan correctamente.
- El CRUD de usuarios en el `AdminSistemasDashboard` es funcional y los datos persisten en la base de datos.
- Los dashboards secundarios han sido desactivados temporalmente y deben ser reparados en el futuro (ver `ROADMAP.md`).
