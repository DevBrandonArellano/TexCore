# Análisis Comparativo: Monolito con Servicios Satélites vs Monolito Puro en TexCore

Este documento presenta un análisis comparativo entre la arquitectura elegida para TexCore (**Monolito con Servicios Satélites**) y una alternativa monolítica tradicional pura, fundamentado en las necesidades operativas y técnicas del sistema para la industria textil.

---

## 1. Contexto del Proyecto TexCore

TexCore es un sistema integral (gestión de órdenes de producción) que maneja flujos de trabajo de diversa naturaleza:
- **Lógica de negocio relacional compleja**: órdenes de producción, créditos de clientes, balances contables e inventario Kardex (soportados bajo transaccionalidad ACID estricta en el Core).
- **Procesos en tiempo real de baja latencia**: validación y escaneo de códigos de barra de lotes en el despacho físico.
- **Procesos pesados orientados a CPU**: renderizado y generación dinámica de PDFs y etiquetas ZPL para etiquetado.
- **Análisis intensivo de datos**: exportación asíncrona de reportes históricos a hojas de cálculo Excel con Pandas.

---

## 2. Descripción de los Enfoques

### El Enfoque Monolítico Puro (Hipotético)
En un escenario monolítico puro, **Django** habría sido el único backend responsable de todo. El enrutamiento de API, la generación de PDFs mediante WeasyPrint, el procesamiento de Pandas para Excel y el escaneo de códigos de barra convivirían en el mismo proceso (Gunicorn/WSGI) y compartirían los mismos recursos de CPU, puertos y memoria.

### La Arquitectura Actual (Monolito con Servicios Satélites)
TexCore emplea un diseño híbrido, pragmático y acotado:
- **Core Backend (Django + DRF)**: Funciona como el monolito centralizador. Se encarga de la seguridad (RBAC), el modelo relacional del negocio, la integridad referencial y las reglas de negocio principales.
- **Servicios Satélites (FastAPI)**: Pequeñas aplicaciones optimizadas y aisladas que ejecutan tareas específicas que estresan la CPU o requieren asincronía nativa:
  - `printing_service`: Genera documentos PDF y etiquetas ZPL.
  - `reporting_excel`: Aislado para procesamiento de Pandas y consultas de reportes pesados.
  - `scanning_service`: Optimizado para latencia ultrabaja en operaciones de escaneo físico en planta.
- **Nginx**: Actúa como Gateway inverso, unificando la experiencia del cliente (React) y enrutando el tráfico de manera transparente.

---

## 3. Puntos Críticos de Comparación

### 3.1. Aislamiento de Procesos Pesados (CPU-Bound)
*   **Monolito Puro**: Generar un reporte masivo en Excel (Pandas) o renderizar un PDF de 100 páginas bloquearía los workers de Django (procesos síncronos de Gunicorn). Esto causaría que otras peticiones críticas (como registrar un avance de lote o guardar stock) se encolen y sufran *Timeouts* (Errores 502/504).
*   **Monolito con Servicios Satélites (Actual)**: Al delegar estas tareas a `reporting_excel` y `printing_service`, el Core Backend (Django) nunca se bloquea. Los usuarios operativos en la planta no experimentan latencia alguna aunque los directivos estén generando reportes históricos pesados de forma simultánea.

### 3.2. Idoneidad Tecnológica y Rendimiento
*   **Monolito Puro**: Obligaría a usar Python de forma uniforme con el ORM de Django para todo. Pandas y WeasyPrint añadirían un enorme peso de dependencias al entorno base, entorpeciendo los despliegues.
*   **Monolito con Servicios Satélites (Actual)**: Permite usar **FastAPI** (asíncrono y de alto rendimiento) para los servicios satélites que requieren velocidad extrema (escaneo) o I/O pesado. Django se mantiene enfocado en lo que hace mejor: administrar la base de datos relacional y la lógica de negocio sólida.

### 3.3. Gestión de Dependencias a Nivel de Sistema Operativo
*   **Monolito Puro**: La imagen Docker de un monolito puro tendría que contener: binarios de WeasyPrint (Pango, Cairo, etc.), librerías de Pandas, drivers ODBC completos de MS SQL Server para Linux, herramientas de ZPL, etc. Esto genera una imagen gigantesca, lenta de construir y desplegar en CI/CD.
*   **Monolito con Servicios Satélites (Actual — evolución Mayo 2026)**: Cada contenedor tiene estrictamente lo que necesita. La imagen de `printing_service` tiene Cairo/Pango, y la del Core Django es limpia y ligera. Gracias a la **migración a API Interna** (ver §5), `reporting_excel` y `scanning_service` ya no requieren drivers ODBC/SQLAlchemy — sus imágenes son ahora aún más ligeras, conteniendo solo `httpx`, `PyJWT` y `Pandas`. Si los drivers de base de datos cambian en el futuro, **ningún servicio satélite necesita actualizarse**.

### 3.4. Resiliencia y Tolerancia a Fallos
*   **Monolito Puro**: Un error de desbordamiento de memoria (OOM - Out of Memory) causado por Pandas al intentar exportar un reporte masivo tumbaría todo el servidor. Nadie en la empresa podría registrar producción o despachos.
*   **Monolito con Servicios Satélites (Actual)**: Si el satélite `reporting_excel` sufre un OOM o el `printing_service` falla, solo se inhabilitan las descargas y las impresiones de forma temporal. El `Core Backend` (monolito) sigue en pie permitiendo la facturación, los despachos y la producción física ininterrumpida. Docker Compose puede reiniciar el servicio satélite fallido silenciosamente en segundos.

### 3.5. Escalabilidad Independiente
*   **Monolito Puro**: Si aumenta la demanda de etiquetas en la planta, se debe escalar toda la instancia del monolito (comprando más RAM y CPU general), desperdiciando recursos.
*   **Monolito con Servicios Satélites (Actual)**: Permite escalar horizontalmente solo el satélite `printing_service` o `scanning_service` según la carga física del momento, optimizando costos de infraestructura.

---

## 4. Conclusión

Para un Sistema de gestión de órdenes de producción industrial como TexCore, un enfoque monolítico tradicional puro habría introducido un alto riesgo operativo (cuellos de botella y bloqueos por procesos CPU-bound). 

La arquitectura de **Monolito con Servicios Satélites** (donde Django es el core y FastAPI maneja los extremos pesados/rápidos de forma aislada) es **la decisión arquitectónica correcta**. Brinda las ventajas de robustez y rapidez de desarrollo de un monolito (para la lógica core), combinada con la resiliencia, escalabilidad y aislamiento tecnológico de servicios independientes en las áreas sujetas a mayor estrés.

---

## 5. Evolución Arquitectónica — Aislamiento total con API Interna (Mayo 2026)

### 5.1 El Problema: Acoplamiento de Base de Datos

En la versión inicial, los servicios satélites `scanning_service` y `reporting_excel` se conectaban **directamente a `texcore_db`** mediante SQLAlchemy y pyodbc respectivamente. Esto violaba el aislamiento y creaba varios problemas:

| Riesgo | Impacto |
|--------|---------|
| Credenciales de BD en múltiples contenedores | Superficie de ataque ampliada (ISO 27001 A.9.2) |
| Migraciones de esquema rotas de forma inesperada | Un cambio de columna en Django podía romper silenciosamente los servicios satélites |
| Imposibilidad de escalar la BD independientemente | Cualquier cambio de motor (ej. Azure SQL) requería actualizar 3 contenedores |
| Tests de servicios satélites dependientes de SQL Server real | Sin posibilidad de unit-testing puro |

### 5.2 La Solución: API Gateway Interna JWT RS256

```
Antes:
  scanning_service ──pyodbc──► texcore_db
  reporting_excel  ──pyodbc──► texcore_db

Después:
  scanning_service ──HTTP/JWT──► Django Internal API ──ORM──► texcore_db
  reporting_excel  ──HTTP/JWT──► Django Internal API ──ORM──► texcore_db
```

El **backend Django (Monolito)** se convierte en el único dueño del esquema de base de datos. Los servicios satélites son **clientes HTTP** que se autentican con **Service Tokens RS256** (`type: service_access`, TTL 15 min) y consumen una API interna con scopes granulares (`lotes:read`, `reports:read`).

### 5.3 Beneficios Concretos Obtenidos

*   **Seguridad (ISO 27001 A.9.2/A.9.4):** Las credenciales de BD solo existen en el contenedor `backend`. Los servicios satélites solo tienen una clave pública RSA (no pueden derivar contraseñas ni acceder a otras tablas).
*   **Encapsulamiento total del esquema:** Cualquier refactorización del modelo Django (renombrar una columna, dividir una tabla) solo requiere actualizar los serializers de la API interna — los servicios satélites no se enteran.
*   **Imágenes Docker más ligeras:** `reporting_excel` eliminó ~120 MB de drivers ODBC para Linux; `scanning_service` eliminó SQLAlchemy completo.
*   **Testabilidad:** Los tests de servicios satélites ahora usan `respx` para mockear HTTP sin necesidad de Docker/SQL Server.
*   **Circuit Breaker:** `DjangoApiClient` corta automáticamente tras 3 errores consecutivos, evitando que un backend caído cause cascadas de reintentos.

### 5.4 Comparativa Final — Tres Enfoques

| Criterio | Monolito Puro | Satélites + BD Directa (Obsol.) | Monolito con Servicios Satélites (Actual) |
|----------|----------|-------------------|------------------------------|
| Aislamiento de procesos pesados | ❌ Ninguno | ✅ Total | ✅ Total |
| Independencia de esquema de BD | ❌ No aplica | ❌ Acoplado | ✅ Encapsulado en Django |
| Seguridad de credenciales BD | ❌ Una clave expuesta | ❌ Múltiples claves expuestas | ✅ Solo en backend |
| Imagen Docker de satélite | ❌ No aplica | ⚠️ Incluye drivers ODBC | ✅ Solo httpx + PyJWT |
| Testabilidad sin infraestructura | ❌ Difícil | ❌ Requiere BD real | ✅ Mock HTTP (`respx`) |
| Escalabilidad horizontal | ❌ Todo o nada | ✅ Por servicio | ✅ Por servicio |

---

### Nota — Auditoría 2026-08-31: DSL innecesario en el adaptador de `reporting_excel`

El adaptador de la migración descrita en §5 (`reporting_excel/src/infrastructure/django_client.py`) todavía
usaba, en la práctica, un DSL de texto tipo `"EXEC sp_GetKardexBodega @BodegaID=?, ..."` parseado con regex y un
mapeo posicional (`_SP_MAPPING`) para simular la llamada a un stored procedure que en realidad nunca se
ejecutaba — puro overhead y una fuente de bugs de parámetros desalineados ya documentada dos veces. Se eliminó
ese DSL: ahora los 4 routers de `reporting_excel` (`exports.py`, `gerencial.py`, `produccion.py`, `vendedores.py`)
llaman directo al endpoint REST con un dict de parámetros nombrados vía `DjangoReportRepository.fetch(endpoint, params)`.

**Actualización — resuelto el mismo día:** la cadena de cada reporte hacía un salto redundante —
`nginx → backend Django (reporting_proxy) → reporting_excel → de vuelta al mismo backend Django (internal_api)`.
Bajo alta concurrencia, ese último salto (con el timeout más corto de toda la cadena, 30s en `django_client.py`)
era el primer punto de falla. Se invirtió el flujo: `reporting_proxy` ahora consulta los datos EN PROCESO
(`internal_api/services/reporting_data.py` + `report_dispatch.py`, mismo código de las vistas existentes,
sin red) y solo le pide a `reporting_excel` (nuevo `POST /generate`) que formatee el archivo — el salto
desapareció por completo. Verificado con una prueba de carga de 250 usuarios (solo 20 workers/3 CPU, config
que antes daba 53.76% de fallos a esta escala): 0.00% de fallos tras el fix. Los routers viejos por-reporte
(`exports.py`, `gerencial.py`, `produccion.py`, `vendedores.py`) y el DSL descrito arriba ya se eliminaron
(commit `cfb5212`) — `reporting_excel/src/routers/` solo conserva `generate.py`.
