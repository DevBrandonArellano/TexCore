# Análisis Comparativo: Arquitectura de Microservicios vs Monolítica en TexCore

Este documento presenta un análisis comparativo entre la arquitectura actual de TexCore (Microservicios Pragmáticos) y una alternativa monolítica tradicional, fundamentado en las necesidades operativas y técnicas del sistema para la industria textil.

---

## 1. Contexto del Proyecto TexCore

TexCore es un sistema integral (ERP/MES) que gestiona flujos críticos:
- Lógica de negocio relacional compleja (órdenes, créditos, inventario Kardex).
- Procesos en tiempo real de baja latencia (escaneo de lotes en despacho).
- Procesos pesados orientados a CPU (generación de PDFs/Etiquetas ZPL).
- Análisis intensivo de datos (exportación de reportes masivos a Excel con Pandas).

## 2. Descripción de los Enfoques

### El Enfoque Monolítico (Hipotético)
En un escenario monolítico, **Django** habría sido el único backend responsable de todo. El enrutamiento de API, la generación de PDFs mediante WeasyPrint, el procesamiento de Pandas para Excel y el escaneo de códigos de barras convivirían en el mismo proceso (Gunicorn/WSGI) y compartirían los mismos recursos de CPU y memoria.

### La Arquitectura Actual (Microservicios Pragmáticos)
TexCore emplea un diseño híbrido y pragmático:
- **Core Backend (Django + DRF)**: Centraliza la seguridad (RBAC), el modelo relacional y la lógica de negocio (SRP, ACID).
- **Servicios Satélites (FastAPI)**: 
  - `printing_service`: Dedicado a renderizar PDFs y ZPL.
  - `reporting_excel`: Aislado para procesamiento de Pandas y consultas masivas (SPs).
  - `scanning_service`: Optimizado para latencia ultrabaja en operaciones de planta.
- **Nginx**: Actúa como Gateway unificando la experiencia del cliente (React).

---

## 3. Puntos Críticos de Comparación

### 3.1. Aislamiento de Procesos Pesados (CPU-Bound)
*   **Monolito**: Generar un reporte masivo en Excel (Pandas) o renderizar un PDF de 100 páginas bloquearía los "workers" de Django (procesos síncronos). Esto causaría que otras peticiones críticas (como registrar un abono o guardar stock) se encolen y sufran *Timeouts* (Errores 502/504).
*   **Microservicios (Actual)**: Al delegar estas tareas a `reporting_excel` y `printing_service`, el Core Backend (Django) nunca se bloquea. Los usuarios operativos en la planta no experimentan lentitud aunque los directivos estén generando reportes históricos pesados.

### 3.2. Idoneidad Tecnológica y Rendimiento
*   **Monolito**: Obligaría a usar Python de forma uniforme con el ORM de Django para todo. Pandas y WeasyPrint añadirían un enorme peso de dependencias al entorno base, entorpeciendo los despliegues.
*   **Microservicios (Actual)**: Permite usar **FastAPI** (asíncrono y de alto rendimiento) para los servicios que requieren velocidad extrema (escaneo) o I/O pesado. Django se mantiene enfocado en lo que hace mejor: administrar la base de datos relacional y la lógica de negocio sólida.

### 3.3. Gestión de Dependencias a Nivel de Sistema Operativo
*   **Monolito**: La imagen Docker de un monolito en TexCore tendría que contener: binarios de WeasyPrint (Pango, Cairo, etc.), librerías de Pandas, drivers ODBC completos de MS SQL Server para Linux, herramientas de ZPL, etc. Esto genera una imagen gigantesca, lenta de desplegar (CI/CD) y altamente vulnerable.
*   **Microservicios (Actual — evolución Mayo 2026)**: Cada contenedor tiene estrictamente lo que necesita. La imagen de `printing_service` tiene Cairo/Pango, y la de Django es limpia y ligera. Gracias a la **migración a API Interna** (ver §5), `reporting_excel` y `scanning_service` ya no requieren drivers ODBC/SQLAlchemy — sus imágenes son ahora aún más ligeras, conteniendo solo `httpx`, `PyJWT` y `Pandas`. Si los drivers de base de datos cambian en el futuro, **ningún microservicio satélite necesita actualizarse**.

### 3.4. Resiliencia y Tolerancia a Fallos
*   **Monolito**: Un error de desbordamiento de memoria (OOM - Out of Memory) causado por Pandas al intentar exportar un millón de registros tumbaría todo el servidor. Nadie en la empresa podría usar el sistema.
*   **Microservicios (Actual)**: Si el `reporting_excel` sufre un OOM o el `printing_service` falla, solo se inhabilitan las descargas y las impresiones. El `Core Backend` sigue en pie permitiendo la facturación, los despachos y la producción ininterrumpida. Docker Compose puede reiniciar el servicio fallido silenciosamente.

### 3.5. Escalabilidad Independiente
*   **Monolito**: Si aumenta la demanda de etiquetas en la planta, se debe escalar todo el monolito (comprando más RAM y CPU general), desperdiciando recursos.
*   **Microservicios (Actual)**: Permite escalar horizontalmente solo el `printing_service` o el `scanning_service` según la carga de cada módulo, optimizando costos de infraestructura.

---

## 4. Conclusión

Para un ERP industrial como TexCore, un enfoque monolítico tradicional habría introducido un alto riesgo operativo (cuellos de botella y bloqueos por procesos CPU-bound). 

La arquitectura de **Microservicios Pragmáticos** (donde Django es el core y FastAPI maneja los extremos pesados/rápidos) es **la decisión arquitectónica correcta**. Brinda las ventajas de robustez y rapidez de desarrollo de un monolito (para la lógica core), combinada con la resiliencia, escalabilidad y aislamiento tecnológico propios de los microservicios en las áreas donde el sistema está sujeto a mayor estrés.

---

## 5. Evolución Arquitectónica — Database-per-Service con API Interna (Mayo 2026)

### 5.1 El Problema: Acoplamiento de Base de Datos

En la versión inicial, los microservicios `scanning_service` y `reporting_excel` se conectaban **directamente a `texcore_db`** mediante SQLAlchemy y pyodbc respectivamente. Esto violaba el patrón **Database-per-Service** y creaba varios problemas:

| Riesgo | Impacto |
|--------|---------|
| Credenciales de BD en múltiples contenedores | Superficie de ataque ampliada (ISO 27001 A.9.2) |
| Migraciones de esquema rotas de forma inesperada | Un cambio de columna en Django podía romper silenciosamente los microservicios |
| Imposibilidad de escalar la BD independientemente | Cualquier cambio de motor (ej. Azure SQL) requería actualizar 3 contenedores |
| Tests de microservicios dependientes de SQL Server real | Sin posibilidad de unit-testing puro |

### 5.2 La Solución: API Gateway Interna JWT RS256

```
Antes:
  scanning_service ──pyodbc──► texcore_db
  reporting_excel  ──pyodbc──► texcore_db

Después:
  scanning_service ──HTTP/JWT──► Django Internal API ──ORM──► texcore_db
  reporting_excel  ──HTTP/JWT──► Django Internal API ──ORM──► texcore_db
```

El **backend Django** se convierte en el único dueño del esquema de base de datos. Los microservicios son **clientes HTTP** que se autentican con **Service Tokens RS256** (`type: service_access`, TTL 15 min) y consumen una API interna con scopes granulares (`lotes:read`, `reports:read`).

### 5.3 Beneficios Concretos Obtenidos

*   **Seguridad (ISO 27001 A.9.2/A.9.4):** Las credenciales de BD solo existen en el contenedor `backend`. Los microservicios solo tienen una clave pública RSA (no pueden derivar contraseñas ni acceder a otras tablas).
*   **Encapsulamiento total del esquema:** Cualquier refactorización del modelo Django (renombrar una columna, dividir una tabla) solo requiere actualizar los serializers de la API interna — los microservicios no se enteran.
*   **Imágenes Docker más ligeras:** `reporting_excel` eliminó ~120 MB de drivers ODBC para Linux; `scanning_service` eliminó SQLAlchemy completo.
*   **Testabilidad:** Los tests de microservicios ahora usan `respx` para mockear HTTP sin necesidad de Docker/SQL Server.
*   **Circuit Breaker:** `DjangoApiClient` corta automáticamente tras 3 errores consecutivos, evitando que un backend caído cause cascadas de reintentos.

### 5.4 Comparativa Final — Tres Enfoques

| Criterio | Monolito | Micro + BD Directa | Micro + API Interna (Actual) |
|----------|----------|-------------------|------------------------------|
| Aislamiento de procesos pesados | ❌ Ninguno | ✅ Total | ✅ Total |
| Independencia de esquema de BD | ❌ No aplica | ❌ Acoplado | ✅ Encapsulado en Django |
| Seguridad de credenciales BD | ❌ Una clave expuesta | ❌ Múltiples claves expuestas | ✅ Solo en backend |
| Imagen Docker de microservicio | ❌ Monolítica | ⚠️ Incluye drivers ODBC | ✅ Solo httpx + PyJWT |
| Testabilidad sin infraestructura | ❌ Difícil | ❌ Requiere BD real | ✅ Mock HTTP (`respx`) |
| Escalabilidad horizontal | ❌ Todo o nada | ✅ Por servicio | ✅ Por servicio |
