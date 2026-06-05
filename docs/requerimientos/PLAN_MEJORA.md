# Análisis de Mejora del Sistema TexCore

## 1. Diagnóstico de Problemas Actuales

### Errores Críticos Identificados y Resueltos:
*   **500 Internal Server Error (Registrar Lote):** 
    *   *Causa:* Falta de asignación de `bodega_entrada` y `bodega_salida` en las Órdenes de Producción. El sistema dependía de campos obsoletos (`producto`, `bodega`).
    *   *Acción:* Se actualizaron las referencias en el servicio `RegistroLoteService` y se corrigieron datos maestros.
*   **401 Unauthorized (Reportes):**
    *   *Causa:* Desfase en el protocolo de comunicación entre el Monolito y el Microservicio de Reportes. El microservicio esperaba JWT (RS256) pero el proxy enviaba `X-Internal-Key`.
    *   *Acción:* Se implementó `generate_token` en `JWTServiceAuthentication` y se actualizó el `ReportingProxyView` para usar JWT firmado.
*   **Flujo de Empaque Ineficiente:**
    *   *Problema:* El empaquetador debía seleccionar manualmente la máquina, lo cual es redundante ya que la máquina está asignada a la OP.
    *   *Acción:* Se simplificó la interfaz del `EmpaquetadoDashboard` y se automatizó la selección de máquina.

## 2. Plan de Mejora Arquitectónica (S.O.L.I.D. & Patrones)

### A. Refactorización del Flujo de Producción (Single Responsibility Principle)
Actualmente, `RegistroLoteService` está creciendo demasiado. Se propone dividirlo en:
1.  **`InventoryOrchestrator`:** Gestiona movimientos de entrada/salida.
2.  **`QualityControlService`:** Valida calidades y pesos (tara/bruto).
3.  **`TraceabilityEngine`:** Genera y vincula códigos de barras/QR (Lotes).

### B. Soporte para Procesos Multietapa y Bodegas Intermedias
Para cumplir con el requerimiento de que un Jefe de Área maneje múltiples procesos con bodegas intermedias:
*   **Modelo `RutaProduccion`:** Definir una secuencia de `Pasos` (Procesos) vinculados a una OP.
*   **Bodegas de Proceso (WIP):** Cada máquina o grupo de máquinas tendrá una `Bodega Virtual/Intermedia`. El sistema moverá el stock automáticamente entre estas bodegas al finalizar cada paso.
*   **Patrón State:** Implementar el estado de la OP como una máquina de estados para manejar transiciones complejas (ej: Tintura -> Secado -> Empaque).

### C. Dashboards Dinámicos e Interactivos
*   **Librería:** Integración profunda de **Recharts** (ya disponible en el proyecto).
*   **Componentización:** Crear un `SharedKPIChart` que reciba configuraciones JSON para renderizar Line/Bar/Pie charts dinámicamente.
*   **Frecuencia:** Implementar `React Query` o `SWR` para polling de datos de producción en tiempo real (vital para Jefes de Planta).

### D. Mejora en la Integración de Impresión
*   **Microservicio de Impresión (Python/FastAPI):**
    *   Debe centralizar los templates ZPL.
    *   Soporte para múltiples impresoras vía IP/Raw Socket (evitando dependencia del Browser Print si es posible).
    *   **Patrón Proxy:** El backend de Django actúa como proxy (ya implementado parcialmente) para asegurar que solo usuarios autenticados manden a imprimir.

## 3. Estrategia de Testing (Correcto Funcionamiento)

*   **Tests Unitarios (Backend):** Mockear servicios de inventario para probar solo la lógica de creación de lotes.
*   **Tests de Integración (Full Flow):** Crear un test que simule: Crear OP -> Registrar 3 Lotes -> Verificar Stock en Bodega Salida -> Verificar Movimientos Inventario.
*   **Tests E2E (Frontend):** Usar Vitest + Testing Library para asegurar que al cambiar la presentación en el empaque, la tara se actualice correctamente.

## 4. Próximos Pasos Sugeridos
1.  **Migración de Datos:** Hacer obligatorios los campos `bodega_entrada` y `bodega_salida` en el modelo `OrdenProduccion`.
2.  **Dashboard Ejecutivo:** Implementar el primer gráfico de "Tendencia de Producción" usando Recharts en el rol de Ejecutivo.
3.  **Intermediate Warehouses:** Crear el modelo `ConfiguracionMaquinaBodega` para mapear automáticamente dónde entra y sale el producto según la máquina seleccionada.
