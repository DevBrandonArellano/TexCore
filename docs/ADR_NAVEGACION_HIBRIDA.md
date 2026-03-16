# Documento de Contexto y Decisión Arquitectónica: TexCore ERP
**Tema:** Transición a Arquitectura Híbrida de Navegación (SPA + URL State)

## 1. Estado Actual del Sistema

TexCore es un ERP robusto que gestiona las operaciones de cuatro empresas textiles (Interfibra, Ribel, Hiltexpoy, Jaltextiles). El frontend está construido como una Single Page Application (SPA) pura utilizando React, Vite y TypeScript.

Actualmente, las vistas de datos masivos (Kardex, Historial de Producción, Auditorías de Bodega) manejan la paginación y el filtrado mediante estado local (`useState`). Esto genera limitaciones operativas:

* Al recargar la página, el usuario pierde su posición y vuelve a la página 1.
* No es posible utilizar los botones nativos de "Atrás/Adelante" del navegador.
* Los supervisores de planta no pueden compartir un enlace exacto de un reporte específico (ej. "Materia prima, página 3") a la gerencia.

## 2. Decisión Arquitectónica

Se ha decidido implementar un Modelo Híbrido de Navegación manteniendo la infraestructura SPA actual.

Se descarta una migración a Server-Side Rendering (SSR) con frameworks como Next.js para evitar alteraciones profundas en los pipelines de despliegue actuales, los contenedores Docker on-premise y el modelo de comunicación con la API de Django.

La solución adoptada consiste en sincronizar el estado crítico de la interfaz de usuario (paginación, filtros de búsqueda, ordenamiento y pestañas activas) directamente con la URL del navegador mediante Query Parameters.

## 3. Directrices de Implementación Técnica (Frontend)

A partir de este momento, todo desarrollo de componentes de tablas, reportes o vistas de datos en React para TexCore debe adherirse a los siguientes patrones:

* **Fuente Única de Verdad:** La URL es la única fuente de verdad para el estado de las consultas a la API.
* **Uso de React Router:** Se debe utilizar el hook `useSearchParams` de `react-router-dom` en lugar de `useState` para cualquier parámetro que modifique el conjunto de datos mostrado.
* **Peticiones a la API:** El hook `useEffect` encargado de disparar las peticiones a Axios/Django REST Framework debe tener como dependencias los valores extraídos de `searchParams`.
* **Mutación de Estado:** Las acciones del usuario (clic en "Siguiente", seleccionar una categoría, aplicar un rango de fechas) deben invocar `setSearchParams`, manteniendo intactos los parámetros de URL que no correspondan a la acción actual.

## 4. Impacto en el Backend (Django)

Esta transición es completamente transparente para el backend. Django REST Framework (DRF) está diseñado de forma nativa para consumir Query Parameters para sus clases de paginación (`PageNumberPagination`, `LimitOffsetPagination`) y filtrado (`DjangoFilterBackend`). No se requieren modificaciones en los ViewSets ni en las consultas a SQL Server para soportar este cambio.

## 5. Flujo de Trabajo Esperado para el Usuario Final

Al implementar este estándar, un usuario logueado (por ejemplo, un operador de Interfibra) experimentará el siguiente flujo:

1. Ingresa a la sección de Inventario de Materia Prima. La URL es `/inventario`.
2. Aplica un filtro por "Lote de Producción" y avanza a la página 4. La URL cambia a `/inventario?categoria=materia_prima&lote=123&page=4` sin recargar la página.
3. El usuario puede copiar esa URL y enviarla por el sistema de tickets de soporte técnico o correo electrónico.
4. Quien abra el enlace (teniendo los permisos de grupo adecuados) verá exactamente el mismo corte de datos.

## 6. Instrucciones para el Agente de IA (Directiva de Generación de Código)

Al actuar como asistente de desarrollo para el proyecto TexCore, debes aplicar estrictamente este contexto:

* Cuando se te solicite crear o refactorizar un componente React que muestre listas de datos procedentes de Django, asume automáticamente que la paginación y los filtros deben ir acoplados a la URL.
* Utiliza TypeScript de forma estricta al manejar los valores nulos o indefinidos provenientes de `searchParams.get()`.
* Prioriza la eficiencia en los re-renders, asegurando que el acoplamiento a la URL no dispare múltiples peticiones redundantes a la API de Django.

---

**Estado:** ✅ Implementado (Marzo 2026 - Ver `IMPLEMENTACION_NAVEGACION_HIBRIDA.md`)
