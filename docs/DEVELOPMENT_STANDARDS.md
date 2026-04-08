# TexCore — Estándares de Desarrollo

> Versión 1.0 | 2026-03-27
> Aplica a: backend Django, microservicios FastAPI, frontend React/TypeScript

---

## 1. Principios Generales

| Principio | Descripción |
|-----------|-------------|
| **Fail-Fast** | Las variables de entorno obligatorias se cargan con `_get_required_env()` al arranque. Si falta alguna, el proceso no inicia. |
| **Secrets sin defaults** | Ningún valor sensible tiene un valor por defecto hardcodeado (`:-`). |
| **Logging estructurado** | Todos los módulos usan `logger = logging.getLogger(__name__)`. Los errores de infraestructura usan `logger.exception()` (incluye traceback). |
| **Sin bare except** | Solo se capturan excepciones específicas. `except Exception` es admitido solo cuando se loguea y se re-lanza o se retorna error genérico al cliente. |
| **DRY en permisos** | Los permisos DRF se generan con `make_group_permission()`. No se duplican clases de permisos. |

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

### Checklist de PR con cambios de seguridad

- [ ] ¿Se validan todos los inputs externos?
- [ ] ¿Los errores al cliente son mensajes genéricos (sin stack traces)?
- [ ] ¿Los secrets provienen de variables de entorno sin valor por defecto?
- [ ] ¿Bandit no reporta hallazgos de severidad media o alta?

---

## 4. Base de Datos

### Django ORM

- **N+1**: Usar `select_related()` para FK y `prefetch_related()` para M2M en todos los `get_queryset()` de ViewSets.
- **Transacciones**: Usar `select_for_update()` en operaciones de transferencia de stock.
- **Validaciones**: La lógica de validación va en `Model.clean()`. El método `save()` llama a `self.full_clean()` antes de `super().save()`.
- **Campos auditables**: Los cambios a campos en `campos_auditables` requieren `instance._justificacion_auditoria` antes del `save()`.

### Migraciones

- Cada migration debe tener un nombre descriptivo: `0050_agregar_constraint_cantidad_positiva`.
- Los índices nuevos van en migrations separadas de los cambios de esquema.
- **No** usar `python manage.py makemigrations` en producción sin revisión del SQL generado.

---

## 5. Testing

### Niveles (ISTQB)

| Nivel | Herramienta | Alcance |
|-------|------------|---------|
| L1 — Unitario | `pytest` / `django.test.TestCase` | Lógica de modelos, cálculos |
| L2 — Integración | `django.test.TestCase` con BD | Endpoints DRF completos |
| L3 — Sistema | Postman / pytest + Docker | Flujos E2E con microservicios |
| L4 — Aceptación | Manual / Playwright | Criterios de negocio |

### Reglas

- **Factories**: Usar `factory_boy` (`gestion/tests/factories.py`). Prohibido crear fixtures JSON manuales.
- **Cobertura mínima**: 75% en módulos `gestion/` e `inventory/` (verificado en CI con `coverage report --fail-under=75`).
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

Ningún PR puede fusionarse a `main` o `staging` sin pasar:
1. `flake8` — sin errores de sintaxis o estilo
2. `bandit` — sin vulnerabilidades de severidad media/alta
3. `detect-secrets` — sin secrets detectados
4. Tests Django con cobertura ≥ 75%
5. TypeScript `tsc --noEmit` sin errores
6. Build de React sin errores

### Pre-commit

Instalar localmente:
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg  # Para Conventional Commits
```

---

## 8. Microservicios

### Contratos de servicio interno

| Servicio | Puerto | Autenticación | Health check |
|---------|--------|--------------|-------------|
| Backend Django | 8000 | JWT (cookie) | `/api/health/` |
| reporting_excel | 8001 | `X-Internal-Key` header | `/health` |
| printing_service | 8002 | Sin auth (red interna) | `/health` |
| scanning_service | 8003 | Sin auth (red interna) | `/health` |

### Reglas de microservicios

- Cada servicio debe tener un endpoint `/health` que verifique sus dependencias reales (BD, archivos, etc.).
- Los secrets se pasan vía variables de entorno — nunca hardcodeados ni con valores por defecto en producción.
- Los logs deben ser JSON estructurado emitidos a stdout.
