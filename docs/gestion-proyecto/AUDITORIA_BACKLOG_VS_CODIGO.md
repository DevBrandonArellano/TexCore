# Auditoría del backlog contra el código — TexCore

> Validación de las **54 historias / 166 criterios de aceptación** del `PRODUCT_BACKLOG.md`
> contra la implementación real del repositorio.
>
> **Fecha:** 24 de septiembre de 2026
> **Método:** lectura directa de modelos, servicios, vistas, configuración y pipelines.
> Cada hallazgo cita `archivo:línea`. No se ejecutó la aplicación: los criterios de
> rendimiento y de usabilidad quedan marcados como **no verificables estáticamente**.

---

## Resumen

| | |
|---|---:|
| Historias con implementación localizada | **53 / 54** |
| Criterios de aceptación revisados | **166** |
| Archivos de prueba citados en los CA que existen | **45 / 45** |
| Hallazgos que incumplen un criterio | **9** |
| Hallazgos fuera de los criterios (riesgo técnico) | **4** |
| Criterios no verificables sin ejecutar | **8** |

La base es sólida: 54 usos de `select_for_update`, 67 de `transaction.atomic`, y la
matriz de trazabilidad del backlog apunta a archivos de prueba que existen **todos**.
Los hallazgos se concentran en configuración y en dos brechas de diseño.

---

## Hallazgos críticos

### C-1 · `/api/groups/` está expuesto sin autenticación

**Incumple TEX-07 CA-3** («el 100 % exige autenticación y declara explícitamente los roles autorizados»).

`gestion/views/core_views.py:25` declara un `ModelViewSet` completo sin `permission_classes`
ni `get_permissions()`:

```python
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
```

Está enrutado en `gestion/urls.py:51` (`router.register(r'groups', ...)`), y
`TexCore/settings.py:184` define `REST_FRAMEWORK` **sin `DEFAULT_PERMISSION_CLASSES`**,
por lo que DRF aplica su valor por defecto: `AllowAny`. No hay middleware que exija
sesión — `MIDDLEWARE` (`TexCore/settings.py:71`) solo incluye `AuditMiddleware`, que
audita pero no autoriza.

Resultado: cualquiera puede **listar, crear, modificar y borrar** los grupos que
sostienen el RBAC de los once roles, sin credenciales.

**Corrección:** añadir `get_permissions()` con `IsSystemAdmin` a `GroupViewSet` **y**
declarar el valor por defecto seguro:

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    ...
}
```

Es la única de las 83 vistas DRF del proyecto sin protección declarada — las otras 82
usan `permission_classes` o `get_permissions()`. El problema no es el descuido puntual,
sino que la configuración **falla en abierto**: cualquier vista futura que olvide
declarar permisos queda pública.

---

### C-2 · La exportación asíncrona de reportes está rota en producción

`inventory/reporting_proxy.py:170` encola la tarea sin red de seguridad:

```python
if is_async:
    from gestion.tasks import async_export_report
    task = async_export_report.delay(...)   # sin try/except
    return JsonResponse({...}, status=202)
```

`TexCore/settings.py:386` apunta el broker a `redis://redis:6379/0`, pero
`infrastructure/docker/docker-compose.prod.yml` **no declara ni `redis` ni
`celery_worker`** — solo `db`, `backend`, `nginx`, `printing`, `scanning` y
`reporting_excel`. El compose de desarrollo sí los tiene.

Cualquier petición con `?async=true` en producción intenta resolver un host inexistente
y devuelve un 500 sin controlar. **Los tests no pueden detectarlo** porque
`TexCore/settings_test_common.py:18` fija `CELERY_TASK_ALWAYS_EAGER = True`, que ejecuta
la tarea en proceso y nunca toca el broker.

**Corrección:** añadir `redis` y `celery_worker` al compose de producción, o envolver el
`.delay()` en un `try/except` que degrade al camino síncrono. Lo segundo es más barato y
elimina la clase de fallo entera.

---

## Hallazgos altos

### A-1 · Las fórmulas de color se editan sin versionar

> **Estado: RESUELTO (24–25 de septiembre de 2026)** — spec
> `docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md`, Fases 1 y 2.
> Editar una fórmula aprobada exige motivo y crea una versión nueva inmutable
> (`VersionFormula`, snapshot JSON de la receta completa); la OP congela la versión oficial
> al lanzarse (`OrdenProduccion.version_formula`) y ya no cambia; `formula_color` pasó a
> `PROTECT` (borrar una fórmula con OPs → 409). Detalle en `CHANGELOG.md` (24-sep-2026).
> El texto siguiente describe el estado del código al momento de la auditoría.

**Incumple TEX-38 CA-1 y CA-2.**

CA-1 exige que modificar una fórmula ya usada en producción **cree una nueva versión**
conservando la anterior. La implementación no lo hace:

- `gestion/models/formula.py:30` — el campo `version` se incrementa *«al duplicar la formula»* (su propio `help_text`).
- `gestion/views/formula_views.py:32` — `FormulaColorViewSet` expone `update` y `partial_update` con `FormulaColorWriteSerializer`, **sin guarda alguna** que bloquee la edición de una fórmula en uso.
- `gestion/views/formula_views.py:117` — la acción `duplicar` sí versiona correctamente, pero depende de que el usuario la elija.
- `gestion/models/produccion.py:55` — `OrdenProduccion.formula_color` es una FK plana, **sin instantánea de la receta**.

Consecuencia: si un Tintorero edita una fórmula, las órdenes de producción históricas que
la usaron pasan a mostrar la receta nueva. Se pierde la reproducibilidad del lote, que es
justamente lo que el módulo debe garantizar.

**Agravante fuera de los criterios:** esa misma FK usa `on_delete=models.CASCADE`.
Borrar una fórmula **borra en cascada las órdenes de producción** que la referencian.
Para un ERP auditable debería ser `PROTECT`.

**Corrección:** bloquear `update` cuando la fórmula tenga órdenes asociadas y redirigir a
`duplicar`; o guardar una instantánea de la receta en la OP al ejecutarla. Y cambiar el
`CASCADE` por `PROTECT`.

### A-2 · La cobertura no bloquea la integración

**Incumple TEX-04 CA-3** («si la cobertura es inferior al 75 %, el pipeline falla e impide la mezcla del código»).

`.github/workflows/ci.yml:225` — el paso que verifica el umbral lleva
`continue-on-error: true`, con este comentario explícito:

> *el pipeline falla si los TESTS fallan (paso anterior), no si la cobertura cae levemente por debajo del umbral.*

La cobertura es hoy una **anotación informativa**, no una barrera. El criterio dice lo
contrario. O se endurece el pipeline, o se corrige la redacción del criterio — pero
ahora mismo el documento afirma algo que el pipeline no hace.

*(`flake8`, `bandit` y `detect-secrets` sí son barreras reales y corren en ese orden: CA-1 se cumple en esa parte.)*

---

## Hallazgos medios

| # | Historia | Criterio | Hallazgo | Evidencia |
|---|---|---|---|---|
| M-1 | TEX-18 | CA-4 | El kárdex almacena **3 decimales**, el criterio exige 4 | `inventory/models.py:101,145` y `:21` → `decimal_places=3` |
| M-2 | TEX-04 | CA-1 | CI no corre en «cualquier rama»: solo `push` a `staging` y PR a `master`/`staging` | `.github/workflows/ci.yml:37-40` |
| M-3 | TEX-01 | CA-1 | «todos alcanzan estado healthy» no se cumple: hay `healthcheck` solo en `db` y `backend` (dev) y solo en `db` (prod) | `infrastructure/docker/docker-compose.yml:22,71`; `.prod.yml:27` |
| M-4 | TEX-02 | CA-2 | En desarrollo el puerto de BD **sí** está publicado (`1433:1433`), igual que Redis (`6379`) | `infrastructure/docker/docker-compose.yml:18-19,167-168` |
| M-5 | TEX-09 | CA-2 | La inmutabilidad se apoya en *no exponer* endpoint de escritura, no en el modelo: `AuditLog` no redefine `save()` ni `delete()` | `gestion/models/core.py:92-121` |
| M-6 | TEX-52 | CA-1 | La consulta de auditoría recorta a **30 días fijos**, así que filtrar por fecha no alcanza registros antiguos | `inventory/views/audit_views.py:35-36` |
| M-7 | TEX-01 | CA-1 | `docker compose up` desde la raíz no funciona: los compose viven en `infrastructure/docker/` | — |
| M-8 | TEX-03 | CA-3 | `system_views.py` toma la IP de `REMOTE_ADDR` en vez de la cadena de proxies que sí usa el middleware | `gestion/views/system_views.py:36` vs `gestion/middleware.py:39-40` |

M-1 probablemente sea un error **del backlog, no del código**: el sistema usa 3 decimales
de forma consistente y hubo una corrección histórica en ese sentido. Lo más sensato es
corregir el criterio.

---

## Criterios no verificables sin ejecutar

Ocho criterios fijan métricas que requieren medición en ejecución. No hay pruebas de
carga en el repositorio (Locust sigue pendiente en el `ROADMAP.md`), así que **hoy no
existe evidencia de ninguno**:

| Historia | Criterio | Métrica |
|---|---|---|
| TEX-17 | CA-3 | Panel de planta < 3 s |
| TEX-22 | CA-3 | Consulta de kárdex < 3 s |
| TEX-44 | CA-3 | Escaneo < 2500 ms |
| TEX-12 | CA-5 | Registro de lote ≤ 3 pasos |
| TEX-41 | CA-3 | Pesaje ≤ 3 pasos |
| TEX-46 | CA-4 | Panel responsivo y legible |

Es el hueco más visible de cara a una defensa: son criterios **numéricos** y ahora mismo
no se pueden sostener con datos. Montar Locust con los tres escenarios de arriba cubriría
la mitad de la tabla.

---

## Lo que quedó verificado y conviene defender

- **Trazabilidad documental intacta.** Los 45 archivos de prueba citados en los criterios existen. Es un punto fuerte poco común.
- **Valores límite correctos.** Crédito: `(saldo + nuevo) > limite` bloquea, así que el límite exacto se acepta (`sales_serializers.py:304`, TEX-32 CA-3). Precio: `precio_unitario < precio_base` rechaza, el igual pasa (`:46`, TEX-33 CA-2). Alertas: `cantidad__lt=stock_minimo` no alerta en el umbral exacto (`reposicion_service.py:243`, TEX-26 CA-2), con test dedicado.
- **FIFO bien resuelto.** `gestion/utils.py:119` ordena por `('fecha_pedido', 'id')`, aplica `min(saldo, valor_pedido)` para abonos parciales, deja el excedente como saldo a favor y excluye anulados con justificación documentada. Cubre los tres criterios de TEX-34.
- **Concurrencia y atomicidad.** 54 `select_for_update` y 67 `transaction.atomic`. El despacho es atómico (`inventory/views/despacho_views.py:94,134,452`).
- **Cookies JWT.** `HttpOnly` fijo, `Secure = not DEBUG`, `SameSite=Lax` (`TexCore/settings.py:223-230`). TEX-06 CA-1 cumplido.
- **Compose de producción bien diseñado.** Redes `dmz_net` / `internal_net`, solo `nginx` publica puertos, el resto usa `expose`.

---

## Orden de trabajo sugerido

1. **C-1** — cerrar `/api/groups/` y poner `DEFAULT_PERMISSION_CLASSES`. Es media hora y elimina una exposición real.
2. **A-1** — versionado de fórmulas y `PROTECT` en la FK. Es el que compromete la trazabilidad, que es la tesis del proyecto.
3. **C-2** — `try/except` en el encolado asíncrono.
4. **A-2 / M-2** — decidir si se endurece el CI o se corrige la redacción de TEX-04.
5. **M-1** — corregir el criterio de TEX-18 a 3 decimales.
6. **Locust** — los tres escenarios de rendimiento, para poder sostener los criterios numéricos.

Los demás hallazgos medios son de configuración y no bloquean nada.
