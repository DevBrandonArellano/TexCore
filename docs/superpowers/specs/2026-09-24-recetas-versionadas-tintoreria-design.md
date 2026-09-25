# Recetas versionadas y orden de tintorería — Diseño

**Fecha:** 24 de septiembre de 2026
**Rol destinatario:** Tintorero / Ingeniero tintorero
**Sistema de referencia:** DELLTEX / InfoTint (observado en planta, no se migra nada de él)

---

## 1. Problema

Cuatro defectos concretos, todos verificados contra el código:

1. **Las fórmulas se editan en sitio.** `FormulaColorViewSet` expone `update` sin guarda alguna, y `OrdenProduccion.formula_color` es una FK plana. Editar una fórmula reescribe la receta de las órdenes históricas. Incumple TEX-38 CA-1 y CA-2, y es el hallazgo A-1 de `AUDITORIA_BACKLOG_VS_CODIGO.md`.
2. **El versionado está bloqueado en base de datos.** `unique_together = [('codigo','sede'), ...]` impide dos versiones del mismo código. El campo `version` existe pero es inutilizable; `duplicar` lo esquiva deformando el código con sufijos `-vN`.
3. **Los litros del baño no se guardan en ninguna parte.** `relacion_bano` solo viaja como parámetro de `calcular-dosificacion` y como variable local del frontend. Sin litros, la dosificación de una orden pasada **no se puede reproducir**, aunque la receta estuviera congelada.
4. **Las fases son un enum cerrado de cinco valores.** Las recetas reales usan procesos con nombre propio (`DESCRUDE`, `LAVADO REDUCTIVO`) y ciclo. No caben.

Un defecto adicional de mantenimiento: `calcularCantidad` está implementado dos veces, en `FormulaQuimica.tsx:99` y en el backend. Hoy coinciden; el día que diverjan, el tintorero verá una cantidad y el inventario descargará otra.

## 2. Regla de dominio

Confirmada con el usuario:

- El **tamaño de la máquina acota** los litros posibles del baño.
- El **ingeniero tintorero fija los litros** contra el peso de la carga.
- **Relación de baño = litros / peso.** Es un resultado, no un dato de entrada.
- **Auxiliares** se dosifican en `gr/L` sobre los **litros**.
- **Colorantes** se dosifican en `%` sobre el **peso**.

Verificado contra una hoja real del sistema de referencia (lote 24337, peso 209 kg, volumen 1800 L, relación 8.61): las ocho dosificaciones cuadran exactamente con estas dos fórmulas.

## 3. Alcance

**Dentro:**

1. Catálogo de procesos de tintorería y qué máquinas ejecuta cada uno
2. Receta con fases libres: proceso, ciclo, temperatura, tiempo
3. Versionado inmutable de fórmulas, con una versión marcada como oficial
4. Orden de tintorería: litros y relación persistidos, anclada a una versión de receta
5. Un único punto de cálculo de dosificación, en el backend
6. Paneles: fórmulas con versiones, stock de químicos, historial de órdenes, historial de descargas

**Fuera (trabajo futuro, no se cierra ninguna puerta):**

- Maestros de colores y artículos como entidades propias
- Hoja de tintura imprimible con código de barras
- Integración con dosificadora, PLC o pesaje automático
- Migración de datos desde cualquier sistema externo

## 4. Decisiones de diseño

| # | Decisión | Razón |
|---|---|---|
| **D1** | Las versiones se guardan como **JSON inmutable**, no como copias relacionales | Elección del usuario. Evita tocar `unique_together`, deja intacta la receta viva que ya consumen `descarga_quimicos` y el resto del sistema, y reduce la superficie de cambio |
| **D2** | **No se crea tabla de instantánea de ejecución.** `DescargaQuimicoOP` ya cumple ese papel | Ya registra fila por fila lo realmente descargado, con reversión y ajuste auditados. Solo hay que anclarla a la versión |
| **D3** | **`litros_bano` es el dato canónico**; la relación se deriva | Coincide con la regla de dominio: los litros los fija el ingeniero, la relación es consecuencia |
| **D4** | El cálculo de dosificación vive **solo en el backend** | Elimina la doble implementación. El frontend consume el endpoint |
| **D5** | Los procesos son un **catálogo nuevo**, no se reutiliza `ProcessStep` | `ProcessStep` es el catálogo de pasos de producción por área (`AreaProcessStep`), con `name` único global y sin sede. Mezclarlos confundiría dos dominios |
| **D6** | La versión se congela **al lanzar la orden**, no al crearla | Una orden en `pendiente` aún puede cambiar de receta; una `en_proceso` no |
| **D7** | **Los ensayos también son versiones.** Una fórmula en desarrollo acumula versiones sin ninguna marcada como oficial | El tintorero prueba varias veces y cada intento lleva su observación. Hay que conservarlos para poder compararlos |
| **D8** | **El tintorero decide** si ensaya sobre una fórmula existente o arranca una de laboratorio nueva | Decisión del usuario. No se impone una regla: en planta el criterio lo pone el personal de tintorería |
| **D9** | **La derivación no tiene regla de origen.** Se puede derivar de la versión oficial o de un ensayo | Decisión del usuario, por el mismo motivo que D8 |
| **D10** | El detalle de la fórmula usa **pestañas** (`Receta · Versiones · Órdenes`) | Es como DELLTEX organiza Recetas (`Receta · Componentes · Estadísticas · Máquinas`). No tapa la pantalla y es el patrón que el tintorero ya reconoce |

## 5. Modelo de datos

### 5.1 Nuevo: `ProcesoTintoreria`

Catálogo de procesos, con sede.

| Campo | Tipo | Notas |
|---|---|---|
| `codigo` | CharField(50) | único por sede |
| `nombre` | CharField(100) | `DESCRUDE`, `LAVADO REDUCTIVO FUERTE` |
| `tipo` | CharField(choices) | `pre_tratamiento`, `colorante`, `auxiliar`, `lavado`, `acabado` |
| `descripcion` | TextField | opcional |
| `activo` | Boolean | default True |
| `sede` | FK Sede | patrón `SedeResolvableMixin` como el resto |

### 5.2 Nuevo: `MaquinaProceso`

Qué procesos ejecuta cada máquina. Tabla intermedia explícita (no `ManyToManyField` desnudo) para poder añadir atributos después sin migración dolorosa.

| Campo | Tipo |
|---|---|
| `maquina` | FK Maquina |
| `proceso` | FK ProcesoTintoreria |

`unique_together = ('maquina', 'proceso')`

### 5.3 Modificado: `Maquina`

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `volumen_bano_litros` | Decimal(10,2), null | Volumen del recipiente. **No confundir con `capacidad_maxima`**, que es throughput por turno en kg y se deja como está |

### 5.4 Modificado: `FaseReceta`

- `nombre` (enum de 5 valores) → **`proceso` FK a `ProcesoTintoreria`**
- Campo nuevo `ciclo` PositiveIntegerField, null — el «Ciclo: 3» de las hojas de referencia
- Se conservan `orden`, `temperatura`, `tiempo`, `observaciones`

**Migración de datos:** por cada uno de los cinco valores del enum se crea un `ProcesoTintoreria` por sede (`pre_tratamiento` → «Pre-Tratamiento / Blanqueo», etc.) y se reapunta cada `FaseReceta` existente al proceso correspondiente. La migración debe ser reversible.

### 5.5 Nuevo: `VersionFormula`

Inmutable. Sin `update` ni `delete` expuestos.

| Campo | Tipo | Notas |
|---|---|---|
| `formula` | FK FormulaColor, related_name='versiones' | |
| `numero` | PositiveInteger | 1, 2, 3… dentro de la fórmula |
| `snapshot` | JSONField | receta completa, ver esquema abajo |
| `motivo` | TextField | por qué se versionó; mínimo 10 caracteres, coherente con la regla de justificación que ya aplica el proyecto |
| `creada_por` | FK User, SET_NULL | |
| `fecha` | DateTimeField, auto_now_add | |
| `es_oficial` | Boolean, default False | como máximo una por fórmula; puede no haber ninguna |
| `observaciones` | TextField, blank | **notas del ensayo**: «sale muy rojizo», «falta igualación». Es lo que distingue una prueba de otra |

`unique_together = ('formula', 'numero')`

**Una fórmula en desarrollo tiene versiones sin ninguna oficial.** Los ensayos son versiones normales: se numeran, guardan su snapshot y llevan su observación. Cuando una convence, se marca oficial. Se puede seguir ensayando (creando versiones nuevas) con una oficial ya en producción: la oficial no cambia hasta que se marque otra.

Restricción: **como máximo una versión oficial por fórmula.** Implementar con `UniqueConstraint(fields=['formula'], condition=Q(es_oficial=True))`.

**Esquema del `snapshot`:**

```json
{
  "formula": {
    "codigo": "PES-T0191",
    "nombre_color": "AZUL MARINO",
    "tipo_sustrato": "poliester",
    "observaciones": "..."
  },
  "fases": [
    {
      "orden": 1,
      "proceso_codigo": "DESCRUDE",
      "proceso_nombre": "Descrude",
      "proceso_tipo": "pre_tratamiento",
      "ciclo": 3,
      "temperatura": 70,
      "tiempo": 20,
      "detalles": [
        {
          "producto_id": 610,
          "producto_codigo": "Q00610",
          "producto_descripcion": "FORYL FKN",
          "tipo_calculo": "gr_l",
          "concentracion_gr_l": "0.700",
          "porcentaje": null,
          "orden_adicion": 1
        }
      ]
    }
  ]
}
```

Se guardan **código y descripción del producto además del `producto_id`**. Si mañana se renombra o se da de baja un químico, la versión histórica sigue siendo legible — que es el sentido de tener historial.

### 5.6 Modificado: `OrdenProduccion`

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `litros_bano` | Decimal(10,2), null | fijado por el ingeniero |
| `version_formula` | FK VersionFormula, **PROTECT**, null | versión congelada al lanzar |

**Además:** cambiar `formula_color` de `on_delete=CASCADE` a **`PROTECT`**. Hoy borrar una fórmula borra en cascada las órdenes de producción que la usaron. Es el agravante del hallazgo A-1.

`relacion_bano` **no se almacena**: es propiedad calculada `litros_bano / peso_neto_requerido`, con guarda de división por cero.

### 5.7 Modificado: `FormulaColor` — derivación y laboratorio

Una fórmula puede nacer de otra: se importa una receta existente, se le hacen cambios y queda como **fórmula independiente**, típicamente porque cambia el material (poliéster → acrílico). `tipo_sustrato` ya existe y sirve para el material.

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `formula_origen` | FK self, SET_NULL, null, related_name='derivadas' | de qué fórmula se importó |
| `version_origen` | FK VersionFormula, SET_NULL, null | **de qué versión concreta** se partió. Puede ser la oficial o un ensayo: lo decide el tintorero (D9) |
| `motivo_derivacion` | TextField, blank | por qué se derivó |
| `es_laboratorio` | Boolean, default False | fórmula de ensayo, no destinada a producción. Se filtra fuera del listado por defecto |

La fórmula derivada arranca su propio ciclo: sus propias versiones, su propia aprobación. Solo guarda de dónde salió. Desde la ficha se navega al origen.

`es_laboratorio` cubre D8: el tintorero que prefiera arrancar una fórmula nueva en vez de ensayar sobre la existente la marca así, y no ensucia el listado de producción.

## 6. Reglas de negocio

**Versionado**

1. **Guardar una fórmula crea siempre una versión.** No se edita nada en sitio. Cada guardado captura el snapshot y exige `observaciones` (qué se probó o qué se cambió). Así cada ensayo queda registrado y comparable.
2. Una fórmula **en desarrollo** acumula versiones sin ninguna oficial. Es el estado normal mientras se busca el color.
3. **Marcar oficial** pone `es_oficial=True` en esa versión y lo quita de la anterior. A partir de ese momento las órdenes pueden lanzarse con ella.
4. Se puede **seguir ensayando con una oficial vigente**: las versiones nuevas nacen no oficiales y la oficial no cambia hasta que se marque otra explícitamente.
5. **Se puede volver a una versión anterior** marcándola oficial de nuevo. Queda registrado quién y cuándo. *(Supuesto — ver sección 12.)*

**Derivación**

6. Derivar crea una `FormulaColor` **nueva** con `formula_origen` y `version_origen`. El origen puede ser la versión oficial o un ensayo: lo decide el tintorero.
7. La derivada arranca sin versiones propias; su primer guardado crea su v1, copiando el snapshot del origen. Desde ahí evoluciona sola.

**Orden de tintorería**

8. Al pasar una orden a `en_proceso`, se fija `version_formula` con la versión oficial vigente. Si la fórmula no tiene versión oficial, **se rechaza el lanzamiento**.
9. Una orden ya lanzada **nunca** cambia de versión.
10. `DescargaQuimicosService.descargar_para_op` calcula desde `orden.version_formula.snapshot`, no desde la receta viva.
11. Dosificación: `gr/L → cantidad = litros × concentracion / 1000` · `% → cantidad = peso × porcentaje / 100`.
12. Si la máquina tiene `volumen_bano_litros`, entonces `litros_bano ≤ volumen_bano_litros`. Si no lo tiene, no se valida y se advierte en la UI.

**Permisos**

13. Solo `tintorero` y `admin_sistemas` crean versiones, marcan oficial y derivan. Reutilizar `IsTintoreroOrAdmin`.

## 7. API

| Método y ruta | Para qué |
|---|---|
| `GET/POST /procesos-tintoreria/` | catálogo de procesos |
| `GET /maquinas/{id}/procesos/` | procesos que ejecuta una máquina |
| `POST /formula-colors/{id}/versiones/` | guarda una versión nueva; body `{observaciones}` |
| `POST /formula-colors/{id}/versiones/{n}/marcar-oficial/` | marca esa versión como oficial y desmarca la anterior |
| `POST /formula-colors/{id}/derivar/` | crea fórmula derivada; body `{codigo, nombre_color, tipo_sustrato, version_origen, motivo_derivacion, es_laboratorio}` |
| `GET /formula-colors/{id}/derivadas/` | fórmulas nacidas de esta |
| `GET /formula-colors/{id}/versiones/` | listado del historial |
| `GET /formula-colors/{id}/versiones/{n}/` | una versión concreta |
| `GET /formula-colors/{id}/versiones/{a}/diff/{b}/` | comparación entre dos versiones |
| `POST /ordenes-produccion/{id}/calcular-dosificacion/` | body `{litros_bano}`; devuelve cantidades y relación. **Sustituye** al cálculo del frontend |
| `GET /ordenes-produccion/historial/` | historial con filtros de fecha, máquina, fórmula y estado |
| `GET /ordenes-produccion/{id}/descargas-quimico/` | descargas de una orden |

`POST /formula-colors/{id}/calcular-dosificacion/` se conserva para simulación sobre una receta sin orden, pero pasa a recibir `{peso, litros}` en vez de `{kg_tela, relacion_bano}`.

## 8. Paneles

El panel de tintorería pasa de dos pestañas a cuatro:

1. **Fórmulas** — lista con columna «Oficial» (`v3`, o `—` si está en desarrollo) y filtro para ocultar las de laboratorio. Al seleccionar una, el detalle se abre con **tres pestañas** (D10):
   - **Receta** — maestro–detalle como hoy, con las dos rejillas apiladas: procesos arriba, insumos del proceso seleccionado abajo.
   - **Versiones** — historial con número, fecha, autor y observación; acciones *Ver*, *Comparar* y *Marcar oficial*; y un comparador que muestra añadido / modificado / retirado entre dos versiones cualesquiera, incluidos los cambios de proceso (temperatura, tiempo, ciclo).
   - **Órdenes** — qué órdenes se lanzaron con cada versión.
2. **Stock de químicos** — lo que ya existe, más un indicador por fórmula de si hay stock suficiente para lanzarla.
3. **Historial de órdenes** *(nuevo)* — tabla filtrable por fecha, máquina, fórmula y estado; cada fila abre peso, litros, relación, versión usada y sus descargas.
4. **Descargas de químicos** *(nuevo)* — vista transversal de `DescargaQuimicoOP` con filtros, mostrando reversiones y ajustes.

Los filtros y la pestaña activa se persisten en la URL, siguiendo el patrón que ya usa `TintoreroDashboard`.

## 9. Pruebas

Convención del proyecto: ISTQB declarado en el nombre y en la matriz de trazabilidad.

| Área | Técnica | Casos mínimos |
|---|---|---|
| Versionado | STT | cada guardado crea versión; la anterior queda intacta; `observaciones` obligatoria |
| Ensayos | EP | fórmula con 3 versiones y ninguna oficial es estado válido; no se puede lanzar una orden con ella |
| Versión oficial | TD | como máximo una oficial; marcar otra desmarca la anterior; volver a una anterior queda registrado |
| Derivación | STT | derivar crea fórmula nueva con `formula_origen` y `version_origen`; el origen puede ser oficial o ensayo; la derivada evoluciona sin afectar al origen |
| Inmutabilidad | CB-D | `update` y `delete` sobre una versión son rechazados |
| Dosificación | BVA | peso o litros en cero; litros igual al volumen de máquina (se acepta); litros por encima (se rechaza) |
| Congelado | STT | lanzar sin versión oficial falla; editar la fórmula después no altera la orden lanzada |
| Snapshot | EP | producto renombrado o dado de baja: la versión sigue legible |
| Permisos | TD | operario no aprueba ni versiona; tintorero sí |
| Migración | — | las fases existentes quedan apuntando al proceso correcto y la migración revierte |

Objetivo de cobertura: mantener el umbral vigente del proyecto (`fail_under=90` en `.coveragerc`, el que usa el CI; el 89 de `setup.cfg` era configuración duplicada y se eliminó).

## 10. Fases de implementación

Tres entregas independientes, cada una utilizable por sí sola.

**Fase 1 — Cimientos** — ✅ completa (24-sep-2026)
`ProcesoTintoreria`, `MaquinaProceso`, `Maquina.volumen_bano_litros`, `FaseReceta.proceso` + `ciclo`, migración de datos del enum, y `formula_color` a `PROTECT`.

**Fase 2 — Versionado** — ✅ completa (25-sep-2026; incluye además `OrdenProduccion.version_formula` y las reglas 4-5, adelantadas desde la Fase 3)
`VersionFormula`, reglas 1 a 5, endpoints de aprobación, historial y diff, y la pestaña de versiones en el panel.

**Fase 3 — Orden y paneles** — ✅ completa (25-sep-2026)
`litros_bano` en la orden (sección «Baño de Tintura» en `OrdenDetalleSheet.tsx`), cálculo unificado en backend (`gestion/services/descarga_quimicos.py`), y las pestañas de historial de órdenes (`HistorialOrdenesTintoreria.tsx`) y de descargas de químicos (`DescargasQuimicosTintoreria.tsx`).

**Fase 4 — Ensayos y derivación** — ✅ completa (25-sep-2026)
Se separó «crear versión» de «marcar oficial» (`VersionadoFormulaService.crear_version()` / `.marcar_oficial()`), se agregó `.derivar()` con los campos de derivación en `FormulaColor` (§5.7: `formula_origen`, `version_origen`, `motivo_derivacion`, `es_laboratorio`), los endpoints `marcar_oficial`/`derivar`/`derivadas`, y el detalle con pestañas `Receta · Versiones · Órdenes` (`FormulaDetalle.tsx`) reemplazando el panel lateral. Migración `0017_formula_derivacion_y_ensayos.py`.

### Desajustes entre lo construido y las decisiones D7–D10 (resueltos en la Fase 4)

Las Fases 1 y 2 se habían implementado con las reglas anteriores. Ambos puntos quedaron resueltos al cerrar la Fase 4:

| Construido en Fases 1-2 | Diseño vigente | Resolución |
|---|---|---|
| `versionado_formula.aprobar()` y `.versionar()` creaban siempre una versión **oficial**. No existía la versión no oficial | D7: los ensayos son versiones **sin** marcar oficial, y conviven con una oficial vigente | Resuelto: `crear_version()` y `marcar_oficial()` son ahora operaciones independientes; una fórmula puede tener versiones sin ninguna oficial |
| El historial vivía en `VersionesFormulaSheet.tsx`, un panel lateral deslizante — la opción **B** que se descartó | D10: pestañas `Receta · Versiones · Órdenes` dentro del detalle — opción **A** | Resuelto: `VersionesFormulaSheet.tsx` se retiró (junto a su test); su contenido (lista + `DiffVista`) se reutilizó en `VersionesFormulaPanel.tsx`, embebido como pestaña de `FormulaDetalle.tsx` |

## 11. Riesgos

| Riesgo | Mitigación |
|---|---|
| La migración del enum de fases toca datos existentes | Reversible, y probada con datos sembrados antes de aplicar |
| Retirar el cálculo del frontend añade una llamada de red por recálculo | Debounce en la UI; el endpoint es de solo lectura y barato |
| `PROTECT` en `formula_color` romperá borrados que hoy funcionan | Es el comportamiento correcto; el error debe explicar que hay órdenes asociadas |
| El JSON del snapshot no es consultable relacionalmente | Aceptado en D1. Los informes por línea salen de `DescargaQuimicoOP`, que sí es relacional |
