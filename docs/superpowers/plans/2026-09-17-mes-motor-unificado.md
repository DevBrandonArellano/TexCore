# Plan de Implementación: Motor Unificado de Manufactura Textil (MES)

> **Guía para Agentes y Sesiones:**  
> Este plan desglosa la modernización arquitectónica de TexCore en **6 Fases incrementales**. Cada fase es autónoma, testeable y ejecutable en sesiones de trabajo independientes o delegable a subagentes (`invoke_subagent`).
> Cada tarea incluye checkboxes (`- [ ]`) para tracking estricto. Al completar tareas, marca los checkboxes correspondientes.
> 
> **Estándar de Naming de Tests (ISTQB CTFL v4.0):**  
> `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`  
> **Comando de Verificación Backend:**  
> `docker exec docker-backend-1 python3 manage.py test --settings=TexCore.settings_test --noinput --keepdb <modulo>`  
> **Comando de Verificación Frontend:**  
> `cd frontend && npx tsc --noEmit`

**Rama Git:** `MES`  
**Objetivo General:** Implementar el Motor Unificado de Manufactura Textil (MES) que soporte nativamente:
1. Producción Continua (por turno/máquina sin orden comercial previa).
2. Producción Contra Stock (reposición basada en alertas agrupadas y planes maestros).
3. Producción Bajo Pedido (vinculación venta $\rightarrow$ planta y reserva de lotes).

---

## Mapa de Archivos por Fases

```
Fase 1: Catálogo y Lotes Unificados
├── gestion/models/catalogo.py                         [MODIFY: agregar 'producto_intermedio']
├── gestion/models/trazabilidad.py                     [MODIFY: adaptar lote para puente universal]
├── inventory/models.py                                [MODIFY: permitir referencia universal en StockBodega]
├── inventory/views/stock_views.py                     [MODIFY: fix agregación en AlertasStockAPIView]
└── tests asociados

Fase 2: Motor Unificado de Ejecución (MES Core)
├── gestion/models/mes.py                              [CREATE: CorridaProduccion, OperacionProduccion, ConsumoMaterial, ProduccionSalida, MermaDesperdicio, GenealogiaLote]
├── gestion/services/ejecucion_produccion.py           [CREATE: EjecucionProduccionService (atómico)]
├── gestion/services/genealogia_service.py             [CREATE: GenealogiaService (Trace-back y Trace-forward DAG)]
└── tests asociados

Fase 3: Modalidad 1 - Producción Continua
├── gestion/models/produccion.py                       [MODIFY: desacoplar peso_neto_requerido obligatorio]
├── gestion/serializers/mes_serializers.py             [CREATE: serializers de corridas y operaciones]
├── gestion/views/mes_views.py                         [CREATE: ViewSets para gestión de planta continua]
├── frontend/src/components/produccion/                [CREATE/MODIFY: UI de Corrida Continua para Operarios]
└── tests asociados

Fase 4: Modalidad 2 - Producción Contra Stock
├── gestion/models/planificacion.py                    [CREATE: PlanProduccion, DetallePlanProduccion]
├── inventory/services/reposicion_service.py           [CREATE: ReposicionService]
├── frontend/src/components/jefe-planta/               [MODIFY: Gestión de Planes contra Stock]
└── tests asociados

Fase 5: Modalidad 3 - Producción Bajo Pedido
├── gestion/models/ventas.py                           [MODIFY: vínculo PedidoVenta -> OrdenProduccion]
├── inventory/models.py                                [MODIFY: campo stock_reservado_pedido en StockBodega]
├── inventory/services/reserva_service.py              [CREATE: ReservaStockService]
├── frontend/src/components/vendedor/                  [MODIFY: botón 'Lanzar Producción' y visibilidad de avance]
└── tests asociados

Fase 6: Transición, Migración de Datos y Estabilización
├── gestion/management/commands/migrar_transformaciones_legacy.py [CREATE: migración histórica]
├── gestion/services/registro_lote.py                  [MODIFY: redirigir a EjecucionProduccionService]
├── inventory/transform_view.py                        [MODIFY: delegar en nuevo motor MES]
├── database/V5__optimizacion_indices_mes.sql          [CREATE: índices covering para Corrida y Genealogía]
└── verificación completa suite (1000+ tests)
```

---

## FASE 1: Fundación del Modelo de Catálogo y Lotes

**Objetivo:** Permitir productos intermedios textiles, resolver el bug de falsas alertas de stock y preparar el enlace universal de lotes.

### Tarea 1.1: Incorporar `producto_intermedio` al Catálogo
- [x] Modificar `gestion/models/catalogo.py`:
  - Agregar `('producto_intermedio', 'Producto Intermedio')` a `Producto.TIPO_CHOICES`.
- [x] Crear migración Django correspondiente (`python manage.py makemigrations gestion`).
- [x] Escribir prueba unitaria:
  - `gestion/tests/test_catalogo_producto_intermedio.py`:
    `test_producto_dado_tipo_intermedio_cuando_se_crea_entonces_persiste_correctamente`
- [x] Actualizar tipos de Frontend en `frontend/src/lib/types.ts` y vistas en `frontend/src/components/admin-sistemas/ManageProductos.tsx`.

### Tarea 1.2: Corregir Consulta de Alertas de Stock Agrupadas
- [x] Modificar `inventory/views/stock_views.py` en `AlertasStockAPIView`:
  - Reemplazar el filtro por fila de lote individual por una consulta agregada sumando existencias por (bodega, producto) para evitar falsas alertas en productos multilote.
- [x] Escribir prueba unitaria:
  - `inventory/tests/test_alertas_stock_agrupadas.py`:
    `test_alerta_stock_dado_producto_con_multiples_lotes_que_superan_minimo_cuando_se_consulta_alerta_entonces_no_aparece`
    `test_alerta_stock_dado_producto_con_multiples_lotes_que_no_superan_minimo_cuando_se_consulta_alerta_entonces_aparece_agrupado`

### Tarea 1.3: Habilitar Identificador Universal de Lote en Stock
- [x] Agregar campos `producto` y `materia_prima_lote` en `LoteProduccion` con autoderivación en `clean()` para habilitar identificación universal de lotes sin romper compatibilidad.
- [x] Crear y aplicar migración `0008_add_lote_producto_and_materia_prima`.
- [x] Escribir prueba unitaria en `gestion/tests/test_lote_universal.py` cubriendo derivación automática y lotes sin orden.
- [x] Ejecutar verificación de regresión completa:
  - `docker exec docker-backend-1 python3 manage.py test --settings=TexCore.settings_test --noinput --keepdb`
  - `cd frontend && npx tsc --noEmit`

---

## FASE 2: Núcleo MES - Motor Unificado de Ejecución

**Objetivo:** Crear las entidades de manufactura real (Corrida, Operación, Consumos, Salidas, Mermas y Genealogía DAG) con su servicio orquestador transaccional.

### Tarea 2.1: Modelos de Ejecución MES
- [x] Crear archivo de modelos `gestion/models/mes.py` (o integrarlo en `gestion/models/produccion.py`):
  - `CorridaProduccion`: encabezado de turno, sede, área, línea, máquina, modalidad, OP opcional, Pedido opcional.
  - `OperacionProduccion`: paso unitario de máquina con tiempos, operario y estado.
  - `ConsumoMaterial`: entrada con lote origen, producto, bodega, cantidad y costo.
  - `ProduccionSalida`: salida con lote generado, producto, bodega, cantidad neta, calidad (primera, segunda, saldo), empaque, metros.
  - `MermaDesperdicio`: peso de merma, tipo de merma, indicador de subproducto vendible.
  - `GenealogiaLote`: relación arista dirigida `(lote_padre, lote_hijo, operacion, cantidad)`.
- [x] Registrar los modelos en `gestion/models/__init__.py`.
- [x] Crear y aplicar migraciones.

### Tarea 2.2: Servicio Orquestador `EjecucionProduccionService`
- [x] Crear `gestion/services/ejecucion_produccion.py`:
  - Método `@transaction.atomic def registrar_operacion(corrida, operacion_data, consumos_data, salidas_data, mermas_data, user)`.
  - Validación de balances de masa ($\sum \text{Entrada} = \sum \text{Salida} + \text{Mermas}$).
  - Bloqueo pesimista con `select_for_update()` sobre cada fila de `StockBodega` a consumir.
  - Generación automática y atómica de:
    - `MovimientoInventario(tipo='CONSUMO')` para cada consumo.
    - `MovimientoInventario(tipo='PRODUCCION')` para cada salida neta.
    - `MovimientoInventario(tipo='MERMA')` para desperdicios o subproductos.
  - Creación de aristas en `GenealogiaLote`.
- [x] Método `@transaction.atomic def revertir_operacion(operacion, user, justificacion)`:
  - Emisión de contrasientos (`DEVOLUCION` / `AJUSTE`).
  - Restauración exacta de saldos en las bodegas de origen y destino.

### Tarea 2.3: Servicio de Consulta de Genealogía (`GenealogiaService`)
- [x] Crear `gestion/services/genealogia_service.py`:
  - `obtener_trazabilidad_hacia_atras(lote)`: Recorre recursivamente los padres hasta las materias primas iniciales de proveedores.
  - `obtener_trazabilidad_hacia_adelante(lote)`: Recorre recursivamente los hijos hasta los productos terminados y despachos a clientes (Recall).
- [x] Escribir suite de pruebas TDD para el Motor MES:
  - `gestion/tests/test_ejecucion_produccion_service.py` con los casos de consumo múltiple, división (split) y mezcla (merge).

---

## FASE 3: Modalidad 1 - Producción Continua

**Objetivo:** Permitir que los operarios y supervisores abran turnos y corridas en planta registrando transformaciones continuas sin orden de producción.

### Tarea 3.1: Desacoplamiento de `OrdenProduccion`
- [x] Modificar `gestion/models/produccion.py`:
  - Hacer `peso_neto_requerido` nullable o permitir que corridas continuas no referencien ninguna OP (`orden_produccion=None`).
  - Relajar validaciones de `clean()` en `LoteProduccion` cuando no exista OP asociada.

### Tarea 3.2: Endpoints y Serializers para Producción Continua
- [x] Crear `gestion/serializers/mes_serializers.py`:
  - `CorridaProduccionSerializer`, `OperacionProduccionSerializer`, `RegistroOperacionInputSerializer`.
- [x] Crear `gestion/views/mes_views.py`:
  - `CorridaProduccionViewSet`: endpoints para `iniciar_corrida`, `finalizar_corrida`, `pausar`, `registrar_operacion`.
- [x] Registrar rutas en `gestion/urls.py`.

### Tarea 3.3: Integración Frontend para Producción Continua
- [x] Crear componente en `frontend/src/components/produccion/CorridaContinuaDashboard.tsx`:
  - Selector de turno, área, línea y máquina.
  - Vista rápida de pesaje continuo: botón para escanear/seleccionar lote de entrada y botón para imprimir etiqueta del lote generado.
- [x] Validar compilación TypeScript: `cd frontend && npx tsc --noEmit`.

---

## FASE 4: Modalidad 2 - Producción Contra Stock (MTS)

**Objetivo:** Estructurar la reposición planificada de inventarios con control estricto de desviación entre lo planificado y lo real.

### Tarea 4.1: Modelo de Planificación de Stock
- [x] Crear `gestion/models/planificacion.py`:
  - `PlanProduccion`: sede, fecha_inicio, fecha_fin, estado ('borrador', 'aprobado', 'en_ejecucion', 'cerrado').
  - `DetallePlanProduccion`: plan, producto_objetivo, cantidad_planificada, cantidad_ejecutada, cantidad_aceptada, cantidad_segunda.
- [x] Crear migraciones y registrar en `gestion/models/__init__.py`.

### Tarea 4.2: Servicio de Reposición y Generación de OP
- [x] Crear `inventory/services/reposicion_service.py`:
  - `generar_orden_desde_plan(detalle_plan, user)`: Genera una `OrdenProduccion` de reposición asociada al plan.
  - Al alimentar la orden mediante `CorridaProduccion`, actualizar el avance y las cantidades aceptadas en el plan.

### Tarea 4.3: Pruebas Unitarias de Reposición
- [x] Escribir `gestion/tests/test_produccion_stock.py`:
  - Validar simulación del Caso 9 y Caso 13 (desviación superior/inferior a la planificada).

### Tarea 4.4: Integración Frontend MTS
- [x] Crear componente `frontend/src/components/jefe-planta/PlanProduccionMTS.tsx`:
  - Visualización de metas, avance cualitativo, barras de progreso y desviaciones.
  - Creación automática de planes desde alertas agrupadas de stock mínimo.
  - Lanzamiento directo de Órdenes de Producción MTS asociadas.

---

## FASE 5: Modalidad 3 - Producción Bajo Pedido (MTO)

**Objetivo:** Vincular pedidos comerciales con órdenes de producción y garantizar la reserva inmutable de los lotes fabricados para el cliente.

### Tarea 5.1: Vinculación Comercial en el Modelo
- [x] Modificar `gestion/models/ventas.py` y `gestion/models/produccion.py`:
  - Agregar `pedido_venta = ForeignKey(PedidoVenta, null=True, blank=True, on_delete=SET_NULL, related_name='ordenes_produccion')` en `OrdenProduccion`.
  - Agregar estado de producción en `DetallePedido` (`cantidad_fabricada`).
- [x] Agregar campo `stock_comprometido` en `StockBodega` para aislar lotes reservados de lotes disponibles para venta libre.

### Tarea 5.2: Flujo de Reserva y Despacho
- [x] Crear `inventory/services/reserva_service.py`:
  - Cuando una corrida bajo pedido genera lotes de salida, marcarlos automáticamente como comprometidos para el cliente del pedido.
  - En `inventory/views/despacho_views.py`, priorizar o restringir el despacho de esos lotes únicamente a la guía del pedido vinculado.

### Tarea 5.3: Pruebas de Producción Bajo Pedido
- [x] Escribir `gestion/tests/test_produccion_pedido.py`:
  - Validar simulación de Caso 10 (MTO) y Caso 11 (procesos intermedios con reserva).

---

## FASE 6: Migración de Datos, Compatibilidad y Estabilización

**Objetivo:** Migrar registros históricos de `TransformacionProducto` al nuevo esquema, actualizar la capa de compatibilidad y asegurar que toda la suite de pruebas pase al 100%.

### Tarea 6.1: Capa de Compatibilidad en Servicios Existentes
- [x] Modificar `gestion/services/registro_lote.py`:
  - Mantener la firma pública de `registrar_lote()`, pero por debajo delegar la persistencia atómica en `EjecucionProduccionService`.
- [x] Modificar `inventory/transform_view.py`:
  - Reemplazar la mutación cruda de stock por una invocación al nuevo motor MES registrando mermas y genealogía.

### Tarea 6.2: Comando de Migración de Transformaciones Históricas
- [x] Crear comando `gestion/management/commands/migrar_transformaciones_legacy.py`:
  - Lee filas de `TransformacionProducto`.
  - Crea sus correspondientes `CorridaProduccion` y `OperacionProduccion`.
  - Deja auditoría de la migración en `AuditLog`.

### Tarea 6.3: Optimización SQL Server 2022
- [x] Crear script `database/V5__optimizacion_indices_mes.sql`:
  - Índices filtrados para `CorridaProduccion(sede_id, estado)`.
  - Índices bidireccionales en `GenealogiaLote(lote_padre_id, lote_hijo_id)`.
- [x] Confirmar que los 21 Stored Procedures antiguos fueron retirados como código muerto y que los reportes operan al 100% sobre Django ORM e `internal_api`.

### Tarea 6.4: Batería de Pruebas Completa
- [x] Ejecutar suite completa en Docker:
  `docker exec docker-backend-1 python3 manage.py test --settings=TexCore.settings_test --noinput --keepdb`
- [x] Ejecutar build y verificación de tipos Frontend:
  `cd frontend && npx tsc --noEmit`
- [x] Ejecutar actualización del grafo de conocimiento:
  `graphify update .`
