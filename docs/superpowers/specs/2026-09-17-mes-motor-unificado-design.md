# Especificación de Diseño: Motor Unificado de Manufactura Textil (MES)

**Fecha:** 2026-09-17  
**Autor:** Equipo Senior de Arquitectura, Manufactura y ERP (Brandon Arellano & Antigravity)  
**Rama Git:** `MES`  
**Estado:** Aprobado para Implementación  
**Controles de Calidad y Cumplimiento:** ISO 27001 A.9.4, A.12.4 | COBIT DSS06, MEA01 | ISA-95 Nivel 3 (MES) | ISTQB CTFL v4.0  

---

## 1. Contexto Industrial y Justificación Arquitectónica

TexCore gestiona la operación textil integral de múltiples sedes. La fábrica opera bajo una cadena progresiva de transformación física de materiales:
$$\text{Materia Prima (Fibras)} \longrightarrow \text{Intermedio 1 (Mecha/Cinta)} \longrightarrow \text{Intermedio 2 (Hilo crudo)} \longrightarrow \text{Intermedio 3 (Hilo teñido/Tela)} \longrightarrow \text{Producto Terminado (Conos/Rollos)}$$

La planta opera concurrentemente bajo tres modalidades:
1. **Producción Continua**: La planta opera ininterrumpidamente por turnos y máquinas según disponibilidad de fibra y líneas, sin necesidad de una orden comercial previa.
2. **Producción Contra Stock (MTS)**: Fabricación para reposición de existencias basada en niveles de inventario mínimo y planes de producción.
3. **Producción Bajo Pedido (MTO)**: Fabricación desencadenada por pedidos de clientes, con requerimiento estricto de reserva de lotes y trazabilidad comercial.

### Problema Central del Sistema Previo
El sistema asumía que *toda transformación requiere una `OrdenProduccion` obligatoria y con peso predeterminado*, no distinguía `producto_intermedio` en el catálogo, mantenía dos conceptos de lote incompatibles (`MateriaPrimaLote` vs `LoteProduccion`), y desconectaba `PedidoVenta` de la planta.

### Principio Rector
**Las tres modalidades deben converger y ejecutarse a través del mismo Motor Unificado de Ejecución (MES).** La intención (Plan o Pedido) y la autorización (Orden) son capas desacopladas y opcionales; la **Ejecución Física** (`CorridaProduccion` $\rightarrow$ `OperacionProduccion` $\rightarrow$ `ConsumoMaterial` + `ProduccionSalida` + `MermaDesperdicio`) es universal, obligatoria e inmutable en el Kardex.

---

## 2. Arquitectura de Dominio (ISA-95)

```
+----------------------------------------------------------------------------------------------------+
| NIVEL 4: PLANIFICACIÓN Y COMERCIAL (ERP)                                                           |
|                                                                                                    |
|    [ PlanProduccion ] (MTS)                         [ PedidoVenta ] (MTO)                          |
|    - Metas de reposición                            - Cliente, entrega, crédito                    |
|    - Opcional                                       - Opcional                                     |
|               \                                                 /                                  |
|                \                                               /                                   |
|                 v                                             v                                    |
|             [ OrdenProduccion ]                                                                    |
|             - Código, Sede, Área, Producto Objetivo, Cantidad Meta                                 |
|             - Obligatoria en MTO y MTS | OPCIONAL en Producción Continua                           |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
| NIVEL 3: EJECUCIÓN DE MANUFACTURA (MES - MOTOR UNIFICADO)                                          |
|                                                                                                    |
|   [ CorridaProduccion ]                                                                            |
|   - Contenedor de ejecución física (Turno, Jornada, Línea, Máquina, Operador)                      |
|   - modalidad: CONTINUA | STOCK | PEDIDO                                                           |
|   - orden_produccion (FK Nullable), pedido_venta (FK Nullable), plan_produccion (FK Nullable)      |
|                                                 |
|                                                 v
|   [ OperacionProduccion ]                                                                          |
|   - Paso de transformación unitaria en máquina (Cardado, Hilatura, Tintura, Enconado)              |
|   - maquina, proceso, hora_inicio, hora_fin, operario, setup_minutos                               |
|         /                               |                               \                          |
|        /                                |                                \                         |
|       v                                 v                                 v                        |
|  [ ConsumoMaterial ]          [ ProduccionSalida ]              [ MermaDesperdicio ]               |
|  - lote_origen (Lote)         - lote_destino (Lote)             - peso_merma                       |
|  - producto, bodega_origen    - producto, bodega_destino        - tipo_merma (volátil / vendible)  |
|  - cantidad_consumida         - cantidad_neta, clasificacion    - producto_merma, bodega_merma     |
|  - costo_unitario             - presentación, tara, metros      - es_subproducto (bool)            |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v (Transacción Atómica)
+----------------------------------------------------------------------------------------------------+
| NIVEL 2 / 1: KARDEX Y TRAZABILIDAD AUDITABLE                                                       |
|                                                                                                    |
|   [ Lote ] (Unificado)                                                                             |
|   - Identificador único universal: MP, Intermedio, PT, Químico.                                    |
|                                                                                                    |
|   [ GenealogiaLote ]                                                                               |
|   - Grafo DAG: (lote_padre, lote_hijo, operacion, cantidad_usada, timestamp)                       |
|                                                                                                    |
|   [ MovimientoInventario ] (Kardex Transaccional Inmutable)                                        |
|   - Tipos: CONSUMO, PRODUCCION, MERMA, AJUSTE, VENTA, COMPRA, TRANSFERENCIA                        |
|                                                                                                    |
|   [ StockBodega ]                                                                                  |
|   - Saldo exacto por (bodega, producto, lote) con bloqueo SELECT FOR UPDATE (UPDLOCK, ROWLOCK)     |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Modelo de Datos Detallado

### 3.1 Catálogo y Lote Unificado
- **`Producto`**:
  - `tipo`: Se incorpora `'producto_intermedio'` a `TIPO_CHOICES`.
- **`Lote`** (Unificación conceptual):
  - Provee una clave foránea universal para que `StockBodega.lote` pueda rastrear tanto materias primas externas como lotes intermedios y terminados.
  - Campos clave: `codigo_lote`, `producto`, `sede`, `fecha_creacion`, `activo`.

### 3.2 Motor de Ejecución
- **`CorridaProduccion`**:
  - `id`: BigAutoField
  - `codigo`: CharField(100, unique_per_sede)
  - `sede`: FK(Sede)
  - `area`: FK(Area)
  - `linea`: FK(LineaProduccion, null=True, blank=True)
  - `maquina_principal`: FK(Maquina, null=True, blank=True)
  - `modalidad`: CharField(choices=['CONTINUA', 'STOCK', 'PEDIDO'])
  - `orden_produccion`: FK(OrdenProduccion, null=True, blank=True, related_name='corridas')
  - `pedido_venta`: FK(PedidoVenta, null=True, blank=True, related_name='corridas')
  - `plan_produccion`: FK(PlanProduccion, null=True, blank=True, related_name='corridas')
  - `turno`: CharField(50)
  - `fecha_jornada`: DateField
  - `hora_inicio`: DateTimeField
  - `hora_fin`: DateTimeField(null=True, blank=True)
  - `estado`: CharField(choices=['en_proceso', 'pausada', 'finalizada', 'anulada'])
  - `supervisor`: FK(CustomUser, null=True)

- **`OperacionProduccion`**:
  - `corrida`: FK(CorridaProduccion, related_name='operaciones')
  - `numero_secuencia`: PositiveIntegerField
  - `maquina`: FK(Maquina)
  - `proceso`: FK(ProcessStep)
  - `operario`: FK(CustomUser)
  - `hora_inicio`: DateTimeField
  - `hora_fin`: DateTimeField
  - `estado`: CharField(choices=['en_curso', 'completada', 'rechazada'])

- **`ConsumoMaterial`**:
  - `operacion`: FK(OperacionProduccion, related_name='consumos')
  - `lote_origen`: FK(Lote, related_name='usos_como_insumo')
  - `producto`: FK(Producto)
  - `bodega_origen`: FK(Bodega)
  - `cantidad_consumida`: DecimalField(max_digits=12, decimal_places=3)
  - `costo_unitario`: DecimalField(max_digits=12, decimal_places=3, default=0)

- **`ProduccionSalida`**:
  - `operacion`: FK(OperacionProduccion, related_name='salidas')
  - `lote_generado`: FK(Lote, related_name='origen_produccion')
  - `producto`: FK(Producto)
  - `bodega_destino`: FK(Bodega)
  - `cantidad_neta`: DecimalField(max_digits=12, decimal_places=3)
  - `clasificacion_calidad`: CharField(choices=['primera', 'segunda', 'saldo'])
  - `peso_bruto`: DecimalField(max_digits=12, decimal_places=3)
  - `tara`: DecimalField(max_digits=12, decimal_places=3)
  - `unidades_empaque`: IntegerField(default=1)
  - `cantidad_metros`: DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

- **`MermaDesperdicio`**:
  - `operacion`: FK(OperacionProduccion, related_name='mermas')
  - `peso_merma`: DecimalField(max_digits=12, decimal_places=3)
  - `tipo_merma`: CharField(choices=['maquina', 'material', 'setup', 'corte', 'humedad', 'otro'])
  - `es_subproducto_vendible`: BooleanField(default=False)
  - `producto_subproducto`: FK(Producto, null=True, blank=True)
  - `bodega_subproducto`: FK(Bodega, null=True, blank=True)

- **`GenealogiaLote`**:
  - `lote_padre`: FK(Lote, related_name='hijos_genealogia')
  - `lote_hijo`: FK(Lote, related_name='padres_genealogia')
  - `operacion`: FK(OperacionProduccion)
  - `cantidad_padre_usada`: DecimalField(max_digits=12, decimal_places=3)
  - `timestamp`: DateTimeField(auto_now_add=True)

---

## 4. Matriz de Trazabilidad y Reglas de Negocio

1. **Atomicidad de Inventario**: Toda confirmación de `OperacionProduccion` debe descontar los lotes de entrada en `StockBodega`, registrar las salidas en `StockBodega`, e insertar registros en `MovimientoInventario` bajo una sola transacción `@transaction.atomic`.
2. **Balance de Masa**: Por cada operación:
   $$\sum \text{Cantidad Entrada} = \sum \text{Cantidad Salida Neta} + \sum \text{Peso Mermas y Desperdicios} \pm \Delta_{\text{humedad/tolerancia}}$$
3. **Reserva MTO**: Si la corrida tiene `pedido_venta`, el stock resultante ingresa con estado reservado para ese pedido impidiendo su asignación a otros despachos.
4. **Alerta Agregada MTS**: Las alertas de reposición consultan:
   $$\text{Saldo Agregado} = \sum_{\text{lotes}} \text{StockBodega}(\text{bodega}, \text{producto}) < \text{stock\_minimo}(\text{producto})$$
5. **No Regresión**: Los 21 Stored Procedures de reportería gerencial y los 1006 tests existentes deben permanecer compatibles o actualizarse sin alterar los contratos de salida de la API interna.
