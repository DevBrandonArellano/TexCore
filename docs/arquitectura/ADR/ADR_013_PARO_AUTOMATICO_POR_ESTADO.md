# ADR-013 — El estado de la máquina genera el paro que registra su detención (TexCore)

> Numeración continua con ADR-012 (`ADR_012_MRP_POR_SEDE.md`).
**Tema:** De dónde sale el historial de «qué días se detuvo una máquina»
**Fecha:** 14-oct-2026 · **Estado:** Aceptada (decisión del usuario) · **Origen:** pedido del Jefe de Área de ver e imprimir el historial de mantenimiento

## 1. Contexto

En el sistema convivían dos representaciones de una máquina detenida, sin relación entre ellas:

| | Qué guarda | Quién lo crea |
|---|---|---|
| `ParoMaquina` | Un intervalo con `inicio`, `fin`, `categoria` (Seis Grandes Pérdidas), `planificado`, `descripcion` y `usuario`. Alimenta la Disponibilidad del OEE | El Operario o el Jefe de Área, a mano, en el modal «Registrar Paro» |
| `Maquina.estado` | Solo el valor actual: `operativa`, `mantenimiento` o `inactiva` | El Jefe de Área, con un `PATCH` desde la tarjeta o el formulario de la máquina |

El cambio de estado **no dejaba fechas**. Si el Jefe de Área ponía una máquina en mantenimiento el lunes
y la devolvía a operativa el miércoles, el sistema no podía decir que estuvo dos días detenida: solo que
«ahora está operativa». Era justo la pregunta del pedido («qué días se detuvieron»), y la Disponibilidad
del OEE tampoco se enteraba de esos días.

Las dos salidas posibles eran: pedir a la gente que registre además el paro a mano (depende de que se
acuerden, y el dato que importa es el que falta), o derivar el paro del cambio de estado.

## 2. Decisión

**El cambio de estado abre y cierra un paro.** `ParoPorEstadoService.sincronizar` se ejecuta en
`MaquinaViewSet.perform_update`, que lee el estado anterior antes de guardar:

| Transición | Efecto |
|---|---|
| → `mantenimiento` | Abre un paro `MANTENIMIENTO_PLANIFICADO` con `planificado=True` |
| → `inactiva` | Abre un paro `OTRO` con `planificado=False` |
| → `operativa` | Cierra el paro automático abierto con `fin = ahora` |
| `mantenimiento` ↔ `inactiva` | Cierra el anterior y abre el nuevo |
| Estado sin cambios | No registra nada |

Reglas que acompañan la decisión:

1. **`ParoMaquina.origen`** (`manual` / `estado`) distingue quién lo creó. **Solo los de origen `estado`
   se cierran solos.** Un paro registrado a mano no se modifica nunca: sigue siendo histórico inmutable,
   como ya decía el ViewSet, y el servicio jamás lo toca.
2. **Idempotencia y concurrencia.** El paro abierto se toma con `select_for_update()` dentro de
   `transaction.atomic`, y si ya existe uno automático abierto del mismo tipo no se abre otro: dos
   peticiones simultáneas no pueden duplicar ni cerrar dos veces el mismo paro.
3. **`inactiva` penaliza la Disponibilidad; `mantenimiento` no.** El OEE no castiga los paros
   planificados (`OeeService`), y una máquina en mantenimiento programado lo es. Una máquina inactiva
   está parada **sin** mantenimiento programado, así que su paro no es planificado y sí baja la
   Disponibilidad: es el comportamiento que se quiere ver.
4. El `origen` es de solo lectura en la API: `estado` lo pone únicamente el servicio.

## 3. Consecuencias

**A favor**
- El historial del Jefe de Área (`GET /api/paros-maquina/historial/`) y su PDF responden «qué días se
  detuvo cada máquina» sin pedirle a nadie un registro extra.
- El OEE mejora su fidelidad: los días en mantenimiento o inactiva dejan de ser invisibles.
- Una sola fuente del tiempo detenido, que comparten la pantalla, el PDF y el OEE.

**En contra, y cómo se mitiga**
- Una máquina que se deja `inactiva` meses acumula un paro enorme que hunde su Disponibilidad. Es
  correcto —estuvo parada—, pero conviene recordarlo al leer el OEE histórico. La pantalla marca los
  paros **en curso** y el resumen los cuenta aparte, precisamente para que se vean.
- El paro automático nace sin `turno` y con una descripción fija («Apertura automática: la máquina pasó
  a mantenimiento»). Quien necesite detallar la causa registra además un paro manual, que no se
  sobreescribe.
- Un cambio de estado hecho fuera de la API (el admin de Django, SQL directo) no genera paro. La API es
  el único camino de la aplicación; el admin de Django lo usa solo el administrador de sistemas.

## 4. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Dejar el historial solo con los paros manuales | El dato que falta es justo el del cambio de estado, y depende de que alguien se acuerde |
| Un modelo nuevo de «historial de estados» | Duplicaría lo que `ParoMaquina` ya modela (intervalo con categoría) y habría que sumar dos fuentes para las horas detenidas y para el OEE |
| Exigir inicio y fin al cambiar el estado | Un formulario más en el flujo rápido de la tarjeta de máquina, para un dato que el sistema ya conoce (el instante del cambio) |
| Cerrar también los paros manuales al volver a operativa | Un paro manual puede describir algo que sigue abierto por otro motivo; modificar un histórico que alimenta el OEE no es aceptable |

## 5. Verificación

- `gestion/tests/test_paro_por_estado.py`: la tabla de decisión completa, la idempotencia y que el paro
  manual abierto nunca se cierra.
- `gestion/tests/test_historial_mantenimiento.py`: el `PATCH` del estado deja el paro visible en el
  historial, con `origen=estado` y marcado en curso.
- En el stack `texcore-prod` con `e1_jefe_area`: `mantenimiento` → paro en curso planificado;
  `operativa` → el mismo paro cerrado con su fin y las horas sumadas en el resumen.

## 6. Referencias

- `gestion/services/paro_por_estado.py`, `gestion/services/historial_paros.py`
- `gestion/models/maquina.py` (`ParoMaquina.origen`), migración `gestion/0009_paromaquina_origen` (hoy dentro de `0003_squashed_0009_paromaquina_origen`)
- Manual del Jefe de Área, secciones 5 y 5.1
- Detalle de la implementación: `CHANGELOG.md`, 14 de octubre de 2026 (tarde)
