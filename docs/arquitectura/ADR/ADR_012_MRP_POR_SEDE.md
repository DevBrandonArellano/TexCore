# ADR-012 — MRP por sede: sugerencias de compra y necesidad de producción (TexCore)

> Numeración continua con ADR-011 (`ADR_011_EQUIVALENCIAS_EMPAQUE_SIN_CONSTANTE.md`).
**Tema:** Cómo calcula el MRP qué comprar y qué producir
**Fecha:** 13-oct-2026 · **Estado:** Aceptada (decisiones del usuario) · **Origen:** TEX-27 y TEX-28; el MRP no devolvía resultados en el stack

## 1. Contexto

El motor anterior (`inventory/services/mrp_engine.py`) se ejecutaba en segundo plano y fallaba sin avisar: las corridas continuas no tienen `peso_neto_requerido` y `Decimal(str(None))` abortaba el cálculo de todas las sedes. La pantalla solo recibía un 202.

Además, el cálculo no era confiable:
- convertía los pedidos de venta en químicos de **una sola fórmula**, la última aprobada del sistema, sin importar el producto ni la sede;
- multiplicaba g/L por kg, sin litros de baño, e ignoraba los insumos en %;
- usaba la receta viva y volvía a pedir los químicos que ya se habían descargado al crear la orden;
- dos ejecuciones simultáneas podían pisarse.

Los requisitos de una orden (TEX-28) tenían el mismo error de unidades, y el Plan Maestro (MTS) proponía **producir** químicos porque tomaba cualquier producto bajo su mínimo.

## 2. Decisión

### Clasificación por `Producto.tipo`

| Clase | Tipos | Qué genera |
|---|---|---|
| Comprados | `materia_prima`, `quimico`, `colorante`, `insumo` | Sugerencia de compra |
| Fabricados | `hilo`, `tela`, `subproducto` | Necesidad de producción (Plan MTS) |

No hay lista de materiales: un producto fabricado no se desglosa en compras salvo a través de las órdenes de producción abiertas.

### Reglas

- **Disponible:** stock de las bodegas de la sede menos `stock_comprometido`.
- **Una orden abierta** (`pendiente` o `en_proceso`) necesita:
  - lo que falta de su producto de entrada: `peso_neto_requerido − Σ lotes producidos`, en relación 1:1 con el peso de salida (supuesto documentado, el mismo de TEX-28);
  - sus químicos, **solo si no se descargaron** (`DescargaQuimicoOP` aplicada), con la misma dosificación que la descarga (`calcular_dosificacion_de_orden`, extraída a `gestion/services_formula.py`).
- **Orden sin peso** (corrida continua): no se calcula y queda como advertencia.
- **Unidades:** la dosificación y el stock están en kg; un producto en otra unidad se excluye con advertencia.
- **Sugerencia de compra**, por producto comprado de la sede: `requerido + stock_mínimo − disponible`, si es mayor que 0. El stock mínimo funciona como stock de seguridad. Es **informativa**: la compra se gestiona fuera del sistema y no tiene estados.
- **Necesidad de producción**, por producto fabricado: `demanda de pedidos + demanda interna + stock_mínimo − disponible − en producción`.
  - Demanda de pedidos: lo pendiente de los pedidos abiertos, `peso − max(despachado, reservado)` por pedido y producto. Al despachar se libera el stock comprometido pero no `cantidad_fabricada`; el máximo evita restar dos veces.
  - Demanda interna: lo que falta de las órdenes cuyo producto de entrada se fabrica.
  - En producción: lo que falta de las órdenes que fabrican el producto.

### Ejecución

- `MRPEngine.ejecutar(sede, usuario)`, en una transacción con la fila de la sede bloqueada. Reemplaza solo los resultados de esa sede y registra una `MRPEjecucion` con sus conteos y advertencias.
- Si falla, la transacción se revierte (quedan los resultados anteriores) y la ejecución queda como `fallida`, con un mensaje genérico; el detalle técnico va al log.
- Es **síncrona**: una sede tarda 0,24 s y las 4 sedes 0,60 s con 3 años de datos.
- **Alcance:** el bodeguero y el administrador de sede calculan su sede; el ejecutivo y el administrador de sistemas, una sede o todas.
- **Auditoría:** se audita cada ejecución (`MRPEjecucion`), no cada requerimiento o sugerencia, que son datos calculados.

### Componentes

- `inventory/services/mrp/` (`reglas`, `requerimientos_orden`, `necesidades_produccion`, `motor`).
- API: `POST sugerencias-compra/ejecutar-mrp/` (`{sede_id}` o `{todas: true}`), `GET sugerencias-compra/ultima-ejecucion/`, `GET sugerencias-compra/necesidades-produccion/`, listas paginadas con `PaginacionAcotada`.
- TEX-28 (`requisitos_materiales`) y `ReposicionService.analizar_necesidades_reposicion` usan las mismas funciones.
- Comando `run_mrp [--sede ID]`.
- Migración `inventory/0003_mrp_por_sede`: crea `MRPEjecucion`, vincula los requerimientos a su orden y deja las sugerencias sin estados. Borra los resultados anteriores, que se recalculan.

## 3. Consecuencias

* El MRP ya no depende de las equivalencias de empaque: los pedidos se miden en kg (`DetallePedido.peso`). TEX-43 sigue aplicándose al registro de lotes (ADR-011).
* El Plan Maestro (MTS) propone producir solo productos fabricados, con el desglose de su necesidad.
* El panel ejecutivo reemplaza «OCS Aprobadas/Rechazadas», que siempre valían 0, por sugerencias de compra, productos a producir y fecha de la última ejecución.
* El supuesto 1:1 entre la entrada y la salida de una orden no considera la merma esperada. Si se necesita, se agregaría un factor por máquina o por proceso.
* Si en el futuro se gestionan las compras en el sistema, las sugerencias podrían aprobarse y contarse como material en camino; hoy no se descuentan de los cálculos siguientes.
