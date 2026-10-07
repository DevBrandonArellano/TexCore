# TexCore — Estándares de Desarrollo

> Versión 1.1 | 2026-08-07
> Aplica a: backend Django, servicios satélite FastAPI, frontend React/TypeScript

---

## 1. Principios Generales

| Principio | Descripción |
|-----------|-------------|
| **Fail-Fast** | Las variables de entorno obligatorias se cargan al arranque. Si falta alguna, el proceso no inicia. |
| **Secrets sin defaults** | Ningún valor sensible tiene un valor por defecto hardcodeado (`:-`). |
| **Logging estructurado** | Todos los módulos usan `logger = logging.getLogger(__name__)`. Los errores de infraestructura usan `logger.exception()` (incluye traceback) o formato RFC5424. |
| **Sin bare except** | Solo se capturan excepciones específicas. `except Exception` es admitido solo cuando se loguea y se re-lanza o se retorna error genérico al cliente. |
| **DRY en permisos** | Los permisos DRF se generan con `make_group_permission()`. No se duplican clases de permisos. |
| **Precisión Textil** | Las telas utilizan `DECIMAL(12,4)` en `cantidad_metros` para precisión métrica en mermas y costeo. Las equivalencias de empaquetado (hilos: 1 baño = 15 fundas = 225 conos; telas: 1 baño = 600m) son **ejemplos configurables por sede**. |

---

## 2. Convenciones de Nomenclatura

### Backend Python (PEP 8 + proyecto)

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Modelos | `PascalCase` | `OrdenProduccion` |
| Funciones/métodos | `snake_case` | `get_audit_sede_id()` |
| Variables privadas (módulo) | `_snake_case` | `_TRUSTED_PROXY_NETWORKS` |
| Constantes módulo | `UPPER_SNAKE` | `INTERNAL_KEY` |
| Factories de test | `NombreFactory` | `ClienteFactory` |

### Tests (ISTQB CTFL v4.0)

```
test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
```

Ejemplos:
- `test_cliente_dado_limite_credito_negativo_cuando_guardar_entonces_falla_constraint_bd`
- `test_orden_dado_estado_pendiente_cuando_mover_a_en_proceso_entonces_transicion_exitosa`

### Frontend TypeScript (proyecto existente)

- Componentes: `PascalCase.tsx`
- Tests: `NombreComponente.descripcion.test.tsx`
- Hooks: `useNombreHook.ts`

### Commits (Conventional Commits)

```
tipo(scope): descripción en imperativo
```

Tipos válidos: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`, `revert`

Ejemplos:
```
feat(gestion): agregar validación de transición de estados en OrdenProduccion
fix(security): remover secret con valor por defecto en reporting_proxy
test(istqb): agregar tests EP/BVA para límite de crédito de Cliente
```

---

## 3. Seguridad

### Reglas obligatorias

1. **Path Traversal**: Las rutas de archivos recibidas de usuarios/APIs externas se validan con regex whitelist antes de usarse.
2. **Rate limiting**: Los endpoints de autenticación (`/api/token/`) tienen límite de 5 req/min por IP.
3. **IP spoofing**: `X-Forwarded-For` solo se procesa si el `REMOTE_ADDR` proviene de una red de proxy de confianza.
4. **JWT Logout**: Los refresh tokens se agregan a la blacklist en el logout (`token.blacklist()`).
5. **CORS**: `allow_origins=["*"]` está prohibido en producción. Las origenes permitidas se configuran vía variable de entorno.
6. **Autenticación Inter-Servicios**: Todos los servicios satélite utilizan firma asimétrica **JWT RS256 (2048 bits)** provista por `internal_api`.

### Checklist de PR con cambios de seguridad

- [ ] ¿Se validan todos los inputs externos?
- [ ] ¿Los errores al cliente son mensajes genéricos (sin stack traces)?
- [ ] ¿Los secrets provienen de variables de entorno sin valor por defecto?
- [ ] ¿Bandit no reporta hallazgos de severidad media o alta?

---

## 4. Base de Datos

### Django ORM

- **N+1**: Usar `select_related()` para FK y `prefetch_related()` para M2M en todos los `get_queryset()` de ViewSets.
- **Transacciones**: Usar `select_for_update()` en operaciones de transferencia de stock y movimientos de inventario.
- **Validaciones**: La lógica de validación de negocio reside en `Model.clean()`. El método `save()` llama a `self.full_clean()` antes de `super().save()`.
- **Campos auditables**: Los cambios a campos en `campos_auditables` requieren `instance._justificacion_auditoria` antes del `save()`.
- **Texto vacío es `''`, nunca `NULL`** (regla Ruff `DJ001`, convención de Django): los `CharField`/`TextField` opcionales se declaran `blank=True, default=''`. Así no hay dos representaciones del vacío (`NULL` y `''`) que los filtros, reportes y el frontend tengan que distinguir. Quien escribe en estos campos envía `''`, también desde el frontend (`valor || ''`, no `|| null`). La única excepción es un campo `unique=True` opcional, que conserva `null=True` con `# noqa: DJ001` y su motivo, porque mssql-django crea esos índices únicos filtrados (`WHERE col IS NOT NULL`): admiten varias filas sin valor si son `NULL`, pero no si son `''` (ver `docs/arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md`).
- **Orden de los miembros del modelo** (regla `DJ012`): campos y managers, `class Meta`, métodos mágicos, `save()`, `get_absolute_url()` y por último los métodos propios.
- **Pasos *best-effort* dentro de una transacción** (sincronización MES, trazabilidad, avisos): van en su propio `with transaction.atomic():` (savepoint) dentro del `try`. Sin savepoint, un error de BD atrapado deja la transacción externa inservible en SQL Server y deja a medias lo que el paso alcanzó a escribir.

### Migraciones

- Cada migration debe tener un nombre descriptivo: `0050_agregar_constraint_cantidad_positiva`.
- Los índices nuevos van en migrations separadas de los cambios de esquema.
- Si una migración hace más estricta una columna (por ejemplo, `NULL` → `NOT NULL`), primero normaliza los datos con `RunPython` y después cambia el esquema, en la misma migración (ejemplo: `gestion/0003_cadenas_vacias_sin_null`). Antes de desplegarla, se prueba sobre un respaldo con datos de producción, no solo sobre la BD vacía del CI.
- **No** usar `python manage.py makemigrations` en producción sin revisión del SQL generado.

---

## 5. Testing

### Niveles (ISTQB)

| Nivel | Herramienta | Alcance |
|-------|------------|---------|
| L1 — Unitario | `pytest` / `django.test.TestCase` | Lógica de modelos, cálculos |
| L2 — Integración | `django.test.TestCase` con BD | Endpoints DRF completos |
| L3 — Sistema | Postman / pytest + Docker | Flujos E2E con servicios satélite |
| L4 — Aceptación | Manual / Vitest / Playwright | Criterios de negocio y UI |

### Reglas

- **Factories**: Usar `factory_boy` (`gestion/tests/factories.py`). Prohibido crear fixtures JSON manuales.
- **Cobertura mínima** (bloquea el CI): **90 %** en `gestion/`, `inventory/` e `internal_api/` (`fail_under` de `.coveragerc`, única fuente). En los microservicios, el umbral de cada `pytest.ini`: `reporting_excel` 90 %, `printing_service` 95 %, `scanning_service` 90 %.
- **Refactor con pruebas de caracterización**: antes de reestructurar una función sin pruebas suficientes, se escriben pruebas que fijan su comportamiento actual y se verifica que pasan **también contra `HEAD`**. Si una prueba falla contra `HEAD`, no caracteriza: documenta un defecto, y se dice así en la prueba.
- **Técnicas obligatorias** en tests nuevos:
  - EP (Partición de Equivalencia): al menos una clase válida e inválida por parámetro
  - BVA (Valores Límite): valores mínimo, mínimo+1, máximo-1, máximo
  - STT (Transición de Estado): para cualquier modelo con máquina de estados

---

## 6. APIs y Documentación

- Todos los ViewSets deben tener docstring con descripción del recurso.
- La documentación OpenAPI se genera automáticamente con `drf-spectacular` y está disponible en `/api/docs/` (solo para `IsAdminUser`).
- Los errores de la API siguen el formato estándar definido en `gestion/exceptions.py`:
  ```json
  {
    "success": false,
    "error": {
      "code": 400,
      "message": "Descripción del error",
      "fields": { "campo": ["mensaje de validación"] }
    }
  }
  ```

---

## 7. CI/CD y Calidad

### Gates de calidad (`.github/workflows/ci.yml`)

Flujo de ramas: rama de trabajo → PR a `staging` → PR de `staging` a `master` (producción). `master` solo acepta
PRs desde `staging`. Ningún PR puede fusionarse a `staging` o `master` sin pasar el job `quality-gate` («Quality Gate · Barrera de Calidad»), que exige que pasen todos estos jobs:
1. **Workflows**: `actionlint` y `zizmor`. Workflows válidos y sin hallazgos de seguridad: actions fijadas por SHA, sin inyección por plantillas, permisos mínimos.
2. **Lint y análisis estático del backend**:
   - **Ruff** en 0 sobre todo el Python del repo, con las reglas de `pyproject.toml`. Incluye las reglas de seguridad `S` (reemplazan a bandit), Django (`DJ`) y complejidad ciclomática ≤ 15 (`C901`). Plan: `docs/superpowers/plans/2026-10-05-migracion-ruff.md`.
   - `detect-secrets`.
   - **mypy** en 0, con los plugins de Django y DRF.
3. **SAST**: Semgrep (`p/django`, `p/python`, `p/secrets`, `p/jwt`). Bloquea en severidad ERROR; los falsos positivos llevan `# nosemgrep: <regla>` con su motivo.
4. **Tests del backend** sobre SQL Server 2022, aplicando todas las migraciones, con cobertura ≥ 90 %.
5. **Tests de los 3 microservicios**, cada uno con su umbral de cobertura.
6. **SCA**: `pip-audit` (backend y microservicios) y `npm audit` del frontend sin vulnerabilidades conocidas.
7. **Frontend**: `tsc --noEmit`, Vitest con sus umbrales de cobertura y el build de React.
8. **En PRs hacia `master`**: la rama de origen es `staging` y las imágenes Docker se construyen.

Una función que supera la complejidad 15 se divide en pasos con nombre (extraer métodos o servicios, SRP), cubiertos antes con pruebas de caracterización. No se excluye con `noqa` salvo que el motivo quede escrito.

### Pre-commit

Corre los mismos Ruff y `detect-secrets` que el CI (`.pre-commit-config.yaml`). Instalar localmente:
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg  # Para Conventional Commits
```

---

## 8. Servicios Satélite

### Contratos de servicio interno

| Servicio | Puerto interno | Autenticación | Health check |
|---------|--------------|--------------|-------------|
| Backend Django | 8000 | JWT (cookie / RS256) | `/api/health/` |
| scanning_service | 8000 (red interna) | JWT RS256 | `/health` |
| reporting_excel | 8002 | JWT RS256 | `/health` |
| printing_service | 8001 | Interno | `/health` |

> Los puertos son internos a la red Docker. Nginx enruta `/api/scanning/` → `scanning_service:8000`. `reporting_excel` es invocado por proxy seguro desde Django. `printing_service` es invocado por `EmpaqueService` (`http://printing_service:8001`).

### Reglas de servicios satélite

- Cada servicio debe tener un endpoint `/health` que verifique sus dependencias reales.
- Los secrets se pasan vía variables de entorno — nunca hardcodeados ni con valores por defecto en producción.
- Ningún servicio satélite se conecta directamente a la base de datos SQL Server; la comunicación con el core es 100% API-first.
- Los logs deben ser JSON estructurado emitidos a stdout.
