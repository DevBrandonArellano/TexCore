# Planificación de Sprints — TexCore

> **Proyecto:** TexCore — Sistema de digitalización y seguimiento de Órdenes de Producción
> **Organización:** Interfibra S.A.
> **Autor:** Brandon Arellano
> **Marco de trabajo:** Scrum
> **Fuente normativa:** `Anteproyecto_Capstone_Final_Version.docx`, §5.1, §5.2 y Tabla 14
> **Documento complementario:** `PRODUCT_BACKLOG.md`
> **Fecha de elaboración:** 23 de septiembre de 2026

---

## 1. Marco metodológico

El desarrollo de TexCore se estructura bajo **Scrum**, de naturaleza iterativa e
incremental, combinado con prácticas de **DevOps** para la Integración y el Despliegue
Continuos (CI/CD).

El trabajo se organiza en un Product Backlog priorizado, ejecutado a través de un
**Sprint 0 de preparación y ocho sprints de desarrollo, cada uno de dos semanas**.
Cada sprint cuenta con un objetivo definido (*Sprint Goal*), un conjunto de elementos
del backlog seleccionados, un entregable funcional (incremento de producto) y una
Definición de Hecho que establece los criterios de calidad para considerar completado
el trabajo.

### 1.1 Ceremonias

| Ceremonia | Momento | Duración | Propósito |
|---|---|---|---|
| **Sprint Planning** | Primer día del sprint | 2 h | Seleccionar los elementos del backlog y acordar el Sprint Goal |
| **Daily Scrum** | Diario | 15 min | Sincronizar avance e identificar impedimentos |
| **Sprint Review** | Último día del sprint | 1,5 h | Presentar el incremento y recoger retroalimentación |
| **Sprint Retrospective** | Tras la Review | 1 h | Inspeccionar el proceso y acordar mejoras |
| **Refinamiento** | Mitad del sprint | 1 h | Preparar y estimar el backlog del sprint siguiente |

### 1.2 Equipo y capacidad

| Concepto | Valor |
|---|---|
| Tamaño del equipo | 1 desarrollador full stack |
| Jornada | 5 días por semana, 8 horas diarias |
| Duración del sprint | 2 semanas (10 días hábiles) |
| Capacidad por sprint | **80 horas** |
| Esfuerzo total de desarrollo | **640 horas** en 16 semanas |
| Velocidad objetivo | **33 puntos de historia por sprint** |
| Factor de conversión | ≈ 2,4 horas por punto |

---

## 2. Definición de Hecho transversal

Conforme al §5.1 del documento Capstone, **todo incremento** de los sprints de
desarrollo debe cumplir sin excepción:

1. Código integrado en la rama principal a través del pipeline de CI/CD
2. Superación de los análisis estáticos: `flake8`, `bandit`, `detect-secrets`
3. Cobertura de pruebas automatizadas **no inferior al 75 %** en el núcleo
4. Registro de auditoría en las operaciones críticas
5. Despliegue verificado en el ambiente de **staging**

Un incremento que incumpla cualquiera de los cinco puntos **no se considera hecho**,
con independencia de que la funcionalidad opere.

---

## 3. Calendario de releases

| Sprint | Inicio | Fin | Semanas | Puntos | Release asociado |
|---|---|---|:---:|---:|---|
| Sprint 0 | 21 Sep 2026 | 02 Oct 2026 | 1–2 | 21 | — (preparación) |
| Sprint 1 | 05 Oct 2026 | 16 Oct 2026 | 3–4 | 32 | **R1 — Núcleo seguro** |
| Sprint 2 | 19 Oct 2026 | 30 Oct 2026 | 5–6 | 32 | **R1 — Núcleo seguro** |
| Sprint 3 | 02 Nov 2026 | 13 Nov 2026 | 7–8 | 32 | **R2 — Operación de planta** |
| Sprint 4 | 16 Nov 2026 | 27 Nov 2026 | 9–10 | 32 | **R2 — Operación de planta** |
| Sprint 5 | 30 Nov 2026 | 11 Dic 2026 | 11–12 | 37 | **R3 — Ciclo comercial** |
| Sprint 6 | 14 Dic 2026 | 25 Dic 2026 | 13–14 | 37 | **R3 — Ciclo comercial** |
| Sprint 7 | 04 Ene 2027 | 15 Ene 2027 | 15–16 | 34 | **R4 — Sistema completo** |
| Sprint 8 | 18 Ene 2027 | 29 Ene 2027 | 17–18 | 31 | **R4 — Sistema completo** |

**Hitos posteriores al desarrollo** (§5.4 del Capstone):

| Hito | Fecha | Contenido |
|---|---|---|
| Code Freeze | 29 Ene 2027 | Cierre del Sprint 8; solo correcciones de defectos |
| Pruebas integrales y preproducción | Febrero 2027 | QA integral y preparación del despliegue |
| Puesta en marcha (Fase 5) | Marzo 2027 | Sincronización con impresoras Zebra y hardware óptico; talleres operativos de máximo 2 horas por grupo |

---

# 4. Sprint Backlogs

---

## Sprint 0 — Infraestructura y DevOps

**Fechas:** 21 de septiembre – 02 de octubre de 2026 · **Capacidad:** 80 h · **Comprometido:** 21 puntos

### Objetivo del Sprint

> Establecer la infraestructura y automatizar los despliegues.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-01 | Orquestación de contenedores con Docker Compose | 5 | Must |
| TEX-02 | Red de contenedores aislada y comunicación entre servicios | 3 | Must |
| TEX-03 | API Gateway con Nginx como punto único de entrada | 5 | Must |
| TEX-04 | Pipeline de CI con Quality Gates | 5 | Must |
| TEX-05 | Estructura base del repositorio y estándares de desarrollo | 3 | Should |

### Entregable

Entorno de desarrollo operativo y backlog priorizado.

### Definición de Hecho específica

- Los contenedores levantan sin errores
- El pipeline ejecuta *build* y *lint*
- El backlog queda estimado y priorizado

> **Nota:** el Sprint 0 es de preparación; la DoD transversal de cobertura del 75 %
> no le aplica, al no producir todavía código de negocio.

---

## Sprint 1 — Seguridad, RBAC y Auditoría

**Fechas:** 05 – 16 de octubre de 2026 · **Capacidad:** 80 h · **Comprometido:** 32 puntos

### Objetivo del Sprint

> Habilitar el acceso seguro y la gestión de roles de la empresa.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-06 | Autenticación con JWT en cookies HttpOnly | 8 | Must |
| TEX-07 | Control de acceso basado en roles para los once roles | 8 | Must |
| TEX-08 | Aislamiento multi-sede de la información | 8 | Must |
| TEX-09 | Registro de auditoría inmutable en operaciones críticas | 5 | Must |
| TEX-10 | Justificación obligatoria en modificación de datos maestros | 3 | Should |

### Entregable

Autenticación y seguridad funcional.

### Definición de Hecho específica

- Acceso restringido por rol verificado
- Pruebas de acceso no autorizado superadas
- Auditoría activa

### Riesgos del sprint

El aislamiento multi-sede (TEX-08) atraviesa todos los módulos posteriores. Un defecto
aquí se propaga a cada consulta del sistema, por lo que la matriz de pruebas de RBAC
debe quedar completa antes de cerrar el sprint.

---

## Sprint 2 — Producción y Órdenes de Producción

**Fechas:** 19 – 30 de octubre de 2026 · **Capacidad:** 80 h · **Comprometido:** 32 puntos

### Objetivo del Sprint

> Digitalizar el registro en planta y el control de Órdenes de Producción.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-11 | Creación de Órdenes de Producción | 5 | Must |
| TEX-12 | Registro de lote de producción en un solo paso | 5 | Must |
| TEX-13 | Asignación de máquina y operario a una orden | 5 | Must |
| TEX-14 | Máquina de estados del ciclo de vida de la orden | 5 | Must |
| TEX-16 | Rechazo de lote con reversión de inventario | 5 | Must |
| TEX-15 | Gestión de maquinaria del área | 3 | Should |
| TEX-17 | Monitoreo del avance de planta | 4 | Should |

### Entregable

Módulo de Producción operativo.

### Definición de Hecho específica

- La orden de producción transita correctamente entre estados
- El registro de lote es atómico
- Cobertura ≥ 75 %

### Riesgos del sprint

TEX-12 es la historia de mayor exposición operativa: es la que ejecuta el operario
decenas de veces al día. Su criterio de usabilidad (no más de tres pasos, RNF-05)
debe validarse con un usuario real antes de la Sprint Review.

---

## Sprint 3 — Kárdex de Inventario

**Fechas:** 02 – 13 de noviembre de 2026 · **Capacidad:** 80 h · **Comprometido:** 32 puntos

### Objetivo del Sprint

> Sustituir los registros manuales de bodega por un Kárdex digital auditable.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-18 | Kárdex transaccional con saldo en tiempo real | 8 | Must |
| TEX-19 | Entrada de materia prima con trazabilidad de lote | 5 | Must |
| TEX-20 | Transferencia de existencias entre bodegas | 5 | Must |
| TEX-21 | Edición auditada de movimientos de inventario | 5 | Must |
| TEX-23 | Filtrado de bodegas por rol y sede | 4 | Must |
| TEX-22 | Consulta y exportación del kárdex | 5 | Should |

### Entregable

Módulo de inventario base funcional.

### Definición de Hecho específica

- Los movimientos reflejan el saldo correcto
- Cada operación queda auditada
- No existen saldos inconsistentes

### Riesgos del sprint

La concurrencia sobre el saldo (TEX-18, CA-3) exige bloqueo a nivel de fila. Es un
riesgo técnico difícil de detectar en pruebas secuenciales: debe probarse
explícitamente con operaciones simultáneas.

---

## Sprint 4 — Transformación y MRP

**Fechas:** 16 – 27 de noviembre de 2026 · **Capacidad:** 80 h · **Comprometido:** 32 puntos

### Objetivo del Sprint

> Conectar la producción con el inventario y sugerir compras de materiales.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-24 | Transformación de productos con cálculo de merma | 8 | Must |
| TEX-27 | Motor MRP de cálculo de requerimientos | 8 | Must |
| TEX-25 | Bloqueo de saldos negativos de inventario | 5 | Must |
| TEX-26 | Alertas de stock bajo | 5 | Must |
| TEX-28 | Consulta de requisitos de materiales de una orden | 3 | Should |
| TEX-29 | Registro de merma vendible | 3 | Could |

### Entregable

Módulo de inventario y MRP completo.

### Definición de Hecho específica

- El MRP genera órdenes de compra sugeridas
- Las alertas son correctas
- Las pruebas de borde quedan superadas

### Riesgos del sprint

TEX-29 (merma vendible) es la única historia `Could` del proyecto y actúa como
amortiguador: si la velocidad cae, se difiere sin comprometer el objetivo del sprint.

---

## Sprint 5 — Comercial y Control de Crédito

**Fechas:** 30 de noviembre – 11 de diciembre de 2026 · **Capacidad:** 80 h · **Comprometido:** 37 puntos

### Objetivo del Sprint

> Automatizar el ciclo de ventas, validación de créditos y pagos.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-32 | Validación automática de límite de crédito | 8 | Must |
| TEX-34 | Reconciliación de pagos con criterio FIFO | 8 | Must |
| TEX-30 | Directorio de clientes con aislamiento de cartera | 5 | Must |
| TEX-31 | Registro de pedidos de venta | 5 | Must |
| TEX-35 | Reversión auditada de pagos | 5 | Must |
| TEX-33 | Validación de precio mínimo de venta | 3 | Must |
| TEX-36 | Estado de cuenta del cliente | 3 | Should |

### Entregable

Módulo Comercial funcional.

### Definición de Hecho específica

- La validación de crédito bloquea pedidos fuera de cupo
- El criterio FIFO se aplica cronológicamente
- La reversión queda auditada

### Riesgos del sprint

Sprint sobrecargado (37 puntos frente a una velocidad objetivo de 33). TEX-36 es la
candidata a diferir. La lógica FIFO con reversión (TEX-34 y TEX-35) es la de mayor
densidad de reglas del proyecto y conviene abordarla al inicio del sprint.

---

## Sprint 6 — Tintorería y Empaquetado

**Fechas:** 14 – 25 de diciembre de 2026 · **Capacidad:** 80 h · **Comprometido:** 37 puntos

### Objetivo del Sprint

> Estandarizar las recetas de tintorería y emitir etiquetas de empaque.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-37 | Recetas de tintorería por fases | 8 | Must |
| TEX-39 | Calculadora de dosificación asociada a la orden | 8 | Must |
| TEX-38 | Versionamiento de fórmulas de color | 5 | Must |
| TEX-40 | Descarga automática de químicos al inventario | 5 | Must |
| TEX-42 | Emisión de etiqueta ZPL para impresoras Zebra | 5 | Must |
| TEX-41 | Registro de pesaje en estación de empaquetado | 3 | Must |
| TEX-43 | Equivalencias de empaque configurables por sede | 3 | Should |

### Entregable

Módulos de Tintorería y Empaquetado funcionales.

### Definición de Hecho específica

- La dosificación calcula gramos exactos
- La etiqueta ZPL se imprime con tara
- Las recetas quedan versionadas

### Riesgos del sprint

**Riesgo de calendario:** el sprint transcurre del 14 al 25 de diciembre, coincidiendo
con el período festivo de Navidad. La capacidad real puede situarse por debajo de las
80 horas nominales. A ello se suma que es uno de los dos sprints sobrecargados
(37 puntos) y que TEX-42 depende de hardware externo (impresoras Zebra), cuya
disponibilidad para pruebas debe asegurarse antes del inicio del sprint.

**Mitigación:** diferir TEX-43 al Sprint 7 y adelantar la verificación de conectividad
con la impresora al Sprint 5.

---

## Sprint 7 — Despacho y Dashboard Ejecutivo

**Fechas:** 04 – 15 de enero de 2027 · **Capacidad:** 80 h · **Comprometido:** 34 puntos

### Objetivo del Sprint

> Asegurar despachos con escáner y proveer tableros de control a gerencia.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-44 | Microservicio de escaneo de códigos QR y de barras | 8 | Must |
| TEX-45 | Despacho atómico con descarga de inventario | 8 | Must |
| TEX-46 | Panel ejecutivo de indicadores | 8 | Must |
| TEX-47 | Microservicio de reportes en Excel | 5 | Must |
| TEX-48 | Drill-down sobre los indicadores | 5 | Should |

### Entregable

Módulo de Despacho y panel ejecutivo funcionales.

### Definición de Hecho específica

- El escaneo valida el lote contra el pedido
- El despacho es atómico, sin descargas parciales
- Los KPIs se presentan en tiempo real

### Riesgos del sprint

El requisito de **menos de 2500 ms** en la validación por escaneo (RNF-03) es el único
umbral de rendimiento cuantificado del proyecto. Debe medirse en condiciones
realistas de red de planta, no en entorno local, donde el resultado sería optimista.

---

## Sprint 8 — Administración y Code Freeze

**Fechas:** 18 – 29 de enero de 2027 · **Capacidad:** 80 h · **Comprometido:** 31 puntos

### Objetivo del Sprint

> Permitir la autoadministración de catálogos y congelar el sistema para preproducción.

### Sprint Backlog

| ID | Historia | Puntos | Prioridad |
|---|---|---:|---|
| TEX-49 | Panel de Administrador de Sistemas | 8 | Must |
| TEX-50 | Panel de Administrador de Sede | 5 | Must |
| TEX-51 | Gestión de catálogos maestros | 5 | Must |
| TEX-52 | Consulta del registro de auditoría | 5 | Must |
| TEX-54 | Congelamiento de código y despliegue en staging | 3 | Must |
| TEX-53 | Persistencia del estado de navegación en la URL | 5 | Should |

### Entregable

Sistema completo en staging, listo para validación.

### Definición de Hecho específica

- Los roles administrativos operan según su alcance
- La navegación es persistente
- El congelamiento de código queda aplicado

### Riesgos del sprint

Es el último sprint y absorbe cualquier deuda arrastrada. Se reserva deliberadamente
por debajo de la velocidad objetivo (31 puntos frente a 33) para dejar margen a la
corrección de defectos detectados en sprints previos.

---

# 5. Seguimiento y métricas

### 5.1 Métricas por sprint

| Métrica | Definición | Fuente |
|---|---|---|
| **Velocidad** | Puntos completados que cumplen la DoD | Tablero Jira |
| **Cobertura de pruebas** | Porcentaje de líneas cubiertas en el núcleo | `coverage report` |
| **Quality Gates superados** | Ejecuciones del pipeline en verde | Pipeline CI/CD |
| **Defectos escapados** | Defectos detectados tras cerrar el sprint | Incidencias en Jira |
| **Compromiso cumplido** | Puntos completados ÷ puntos comprometidos | Tablero Jira |

### 5.2 Gráfico de avance

Se mantiene un **burndown** por sprint (puntos restantes por día) y un **burnup**
acumulado del proyecto contra los 288 puntos totales.

---

# 6. Registro de riesgos del plan

| ID | Riesgo | Sprint | Impacto | Probabilidad | Mitigación |
|---|---|---|---|---|---|
| R-01 | Período festivo reduce la capacidad real | 6 | Alto | Alta | Diferir TEX-43; reducir el compromiso a 34 puntos |
| R-02 | Indisponibilidad de impresoras Zebra para pruebas | 6 | Alto | Media | Verificar conectividad durante el Sprint 5 |
| R-03 | Umbral de 2500 ms no alcanzado en red de planta | 7 | Alto | Media | Medir en entorno real desde el inicio del sprint |
| R-04 | Defectos de concurrencia en el saldo de inventario | 3 | Alto | Media | Pruebas explícitas de operaciones simultáneas |
| R-05 | Sobrecarga sostenida en los sprints 5 y 6 | 5, 6 | Medio | Alta | Diferir las historias `Should` identificadas |
| R-06 | Cobertura por debajo del 75 % bloquea la integración | Todos | Medio | Media | Desarrollo guiado por pruebas desde el Sprint 1 |
| R-07 | Defecto en el aislamiento multi-sede se propaga | 1 | Alto | Baja | Matriz completa de pruebas RBAC antes de cerrar |

---

# 7. Referencias

- Documento Capstone, §5.1 *Metodología de Desarrollo y Planificación Ágil*
- Documento Capstone, §5.2 y **Tabla 14** *Product Backlog y Plan de Releases*
- Documento Capstone, §5.4 *Plan de Adopción y Puesta en Marcha*
- Documento Capstone, §5.5 *Estimación de Costos*
- `PRODUCT_BACKLOG.md` — detalle de las 54 historias con criterios de aceptación
- `docs/matriz_trazabilidad_pruebas.md` — correspondencia requisito ↔ caso de prueba
- Schwaber, K. y Sutherland, J. (2020). *The Scrum Guide*
- ISTQB CTFL v4.0 — técnicas de diseño de pruebas
