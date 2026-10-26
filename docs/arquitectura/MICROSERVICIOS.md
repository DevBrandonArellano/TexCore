# Análisis Comparativo: Monolito con Servicios Satélites vs Monolito Puro en TexCore

Este documento presenta un análisis comparativo entre la arquitectura elegida para TexCore (**Monolito con Servicios Satélites**) y una alternativa monolítica tradicional pura, fundamentado en las necesidades operativas y técnicas del sistema para la industria textil.

---

## 1. Contexto del Proyecto TexCore

TexCore es un sistema integral (gestión de órdenes de producción) que maneja flujos de trabajo de diversa naturaleza:
- **Lógica de negocio relacional compleja**: órdenes de producción, créditos de clientes, balances contables e inventario Kardex (soportados bajo transaccionalidad ACID estricta en el Core).
- **Procesos en tiempo real de baja latencia**: validación y escaneo de códigos de barra de lotes en el despacho físico.
- **Procesos pesados orientados a CPU**: renderizado y generación dinámica de PDFs y etiquetas ZPL para etiquetado.
- **Análisis intensivo de datos**: exportación de reportes históricos a hojas de cálculo Excel con Pandas.

---

## 2. Descripción de los Enfoques

### El Enfoque Monolítico Puro (Hipotético)
En un escenario monolítico puro, **Django** habría sido el único backend responsable de todo. El enrutamiento de API, la generación de PDFs mediante WeasyPrint, el procesamiento de Pandas para Excel y el escaneo de códigos de barra convivirían en el mismo proceso (Gunicorn/WSGI) y compartirían los mismos recursos de CPU, puertos y memoria.

### La Arquitectura Actual (Monolito con Servicios Satélites)
TexCore emplea un diseño híbrido, pragmático y acotado:
- **Core Backend (Django + DRF)**: Funciona como el monolito centralizador. Se encarga de la seguridad (RBAC), el modelo relacional del negocio, la integridad referencial y las reglas de negocio principales.
- **Servicios Satélites (FastAPI)**: Pequeñas aplicaciones optimizadas y aisladas que ejecutan tareas específicas que estresan la CPU o requieren asincronía nativa:
  - `printing_service`: Genera documentos PDF y etiquetas ZPL.
  - `reporting_excel`: Aislado para el formateo con Pandas/openpyxl de los reportes que el backend le envía ya resueltos.
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
*   **Monolito con Servicios Satélites (Actual — evolución Mayo 2026)**: Cada contenedor tiene estrictamente lo que necesita. La imagen de `printing_service` tiene Cairo/Pango, y la del Core Django es limpia y ligera. Gracias a la **migración a API Interna** (ver §5), `reporting_excel` y `scanning_service` ya no requieren drivers ODBC/SQLAlchemy — sus imágenes son más ligeras: `scanning_service` lleva `httpx` y `PyJWT`; `reporting_excel`, `PyJWT`, Pandas y openpyxl. Si los drivers de base de datos cambian en el futuro, **ningún servicio satélite necesita actualizarse**.

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

### 5.2 La Solución: el backend es el único dueño de la BD

```
Antes:
  scanning_service ──pyodbc──► texcore_db
  reporting_excel  ──pyodbc──► texcore_db

Ahora:
  scanning_service ──HTTP + JWT RS256──► Django Internal API ──ORM──► texcore_db
  Django ──POST /generate + JWT RS256 (filas ya resueltas)──► reporting_excel
  Django ──POST /pdf/*, /zpl/* + JWT RS256 (datos del documento)──► printing_service
```

El **backend Django** es el único dueño del esquema y de las credenciales de la base de datos. Cada satélite se relaciona con él de una forma:

| Satélite | Dirección | Autenticación |
|---|---|---|
| `scanning_service` | Llama a Django: `GET /api/internal/v1/lotes/{codigo}/validate/` | Se registra con `SERVICE_NAME`/`SERVICE_SECRET` y obtiene un token RS256 de 5 min con scope `lotes:read` |
| `reporting_excel` | Django lo llama: `POST /generate` con las filas del reporte | Verifica con la clave pública el token RS256 (5 min) que firma el backend |
| `printing_service` | Django lo llama: `/pdf/*` y `/zpl/etiqueta` con los datos del documento | Verifica firma, vencimiento, `type=service_access` e `iss=texcore` del token RS256 de 60 s que firma el backend |

Ningún satélite acepta tráfico sin un JWT RS256 válido (RS-09 en `docs/requerimientos/REGISTRO_RIESGOS.md`).

`reporting_excel` llamaba antes a la API interna para obtener los datos. Desde el 31-ago-2026, el backend ejecuta las mismas consultas en proceso (`internal_api/services/reporting_data.py`) y solo le pide el formateo. Así se eliminó un salto de red que, con 250 usuarios concurrentes, era el primer punto de falla: los errores bajaron del 53,76 % al 0,00 % con la misma configuración (20 workers, 3 CPU).

### 5.3 Beneficios Concretos Obtenidos

*   **Seguridad (ISO 27001 A.9.2/A.9.4):** Las credenciales de BD solo existen en los contenedores `backend` y `db`. Los satélites solo tienen la clave pública RSA (y `scanning_service`, su propio secreto de servicio).
*   **Encapsulamiento del esquema:** Un cambio en el modelo de Django (renombrar una columna, dividir una tabla) solo requiere ajustar la API interna o las funciones de datos de reportes; los satélites no cambian.
*   **Imágenes Docker más ligeras:** `reporting_excel` eliminó ~120 MB de drivers ODBC para Linux; `scanning_service` eliminó SQLAlchemy completo.
*   **Testabilidad:** Las pruebas de los satélites no necesitan Docker ni SQL Server: `scanning_service` simula la API de Django con `respx`, y `reporting_excel` y `printing_service` se prueban con el cliente HTTP de FastAPI.
*   **Circuit Breaker:** el `DjangoApiClient` de `scanning_service` corta tras 3 errores consecutivos, evitando que un backend caído cause cascadas de reintentos.

### 5.4 Comparativa Final — Tres Enfoques

| Criterio | Monolito Puro | Satélites + BD Directa (Obsol.) | Monolito con Servicios Satélites (Actual) |
|----------|----------|-------------------|------------------------------|
| Aislamiento de procesos pesados | ❌ Ninguno | ✅ Total | ✅ Total |
| Independencia de esquema de BD | ❌ No aplica | ❌ Acoplado | ✅ Encapsulado en Django |
| Seguridad de credenciales BD | ❌ Una clave expuesta | ❌ Múltiples claves expuestas | ✅ Solo en backend |
| Imagen Docker de satélite | ❌ No aplica | ⚠️ Incluye drivers ODBC | ✅ Sin drivers de BD |
| Testabilidad sin infraestructura | ❌ Difícil | ❌ Requiere BD real | ✅ Sin BD ni Docker |
| Escalabilidad horizontal | ❌ Todo o nada | ✅ Por servicio | ✅ Por servicio |
