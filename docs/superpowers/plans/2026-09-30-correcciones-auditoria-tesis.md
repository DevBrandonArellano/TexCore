# Correcciones de la auditoría backlog vs. código (tesis capítulo 7) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar en el código los hallazgos C-1, C-2 y M-4 de la auditoría del 24-sep-2026, de modo que lo que afirma el documento de tesis (secciones 7.3.4, 7.1.2, 8.2 y 9) sea verdadero y verificable por pruebas.

**Architecture:** Cambios puntuales sobre el núcleo Django (configuración DRF, una vista, el proxy de reportes) y el `docker-compose.yml` de desarrollo. Sin nuevos módulos. Cada cambio se protege con pruebas de regresión siguiendo la convención `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`.

**Tech Stack:** Python 3.12, Django 5.2, DRF 3.16, Celery 5.4 + kombu 5.5, pytest (+ pytest-django), Docker Compose.

**Spec:** `docs/gestion-proyecto/AUDITORIA_BACKLOG_VS_CODIGO.md` (hallazgos C-1, C-2, M-4) y el documento `Documentacion/Capstone_Resumen_y_Puntos_7_a_11_corregido.docx` (sección 7.3.4: «la vista exige ahora el rol de Administrador de Sistemas y la configuración global de la API establece la autenticación obligatoria como permiso por defecto […] Se añadieron nueve pruebas automatizadas: seis […] y tres […]»).

## Global Constraints

- **NUNCA ejecutar `git commit` ni `git push`.** Al final de cada tarea se deja el cambio en el working tree y se informa al usuario; él hace los commits.
- Rama actual: `MES`. No cambiar de rama ni hacer stash.
- Tests locales del backend (sin SQL Server): `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest <ruta> -p no:cacheprovider --no-cov --no-migrations -q -W ignore`
- El archivo `gestion/tests/test_permisos_por_defecto.py` debe contener **exactamente 9 pruebas** (6 de grupos + 3 de configuración): el documento de tesis cita ese número. Pruebas adicionales van en otros archivos.
- No tocar `infrastructure/docker/docker-compose.prod.yml`: la BD en producción se queda con `expose: "1433"` (sin publicar al host).
- No modificar los archivos `.coverage` versionados; si una ejecución los altera, restaurarlos con `git checkout -- <archivo>`.
- Comentarios y mensajes en español, como el resto del código.

## Ejecución multiagente

Las Tasks 1, 2 y 3 tocan archivos disjuntos y pueden ejecutarse **en paralelo**, un subagente por tarea. La Task 4 depende de las tres y va al final.

| Tarea | Archivos exclusivos | Puede correr en paralelo con |
|---|---|---|
| Task 1 | `TexCore/settings.py`, `gestion/views/core_views.py`, `gestion/custom_jwt_views.py`, `gestion/tests/test_permisos_por_defecto.py`, `gestion/tests/test_core_views.py` | 2, 3 |
| Task 2 | `inventory/reporting_proxy.py`, `inventory/tests/test_reporting_proxy_extra.py` | 1, 3 |
| Task 3 | `infrastructure/docker/docker-compose.yml` | 1, 2 |
| Task 4 | `CHANGELOG.md`, `docs/gestion-proyecto/AUDITORIA_BACKLOG_VS_CODIGO.md` | ninguna (va al final) |

Reglas del modo multiagente:
- **Sin worktrees aislados.** Los cambios de la Task 1 no tienen commit y el usuario no hace commits desde el agente, así que un worktree no los vería ni podría integrarse. Todos los subagentes trabajan en el mismo working tree y solo pueden editar sus archivos exclusivos.
- Cada subagente corre **solo sus propias pruebas**. La suite completa del backend (Task 1 Step 5) la ejecuta el coordinador **una vez**, cuando las Tasks 1 y 2 hayan terminado.
- Después de cada tarea, un subagente revisor distinto del implementador revisa ese diff contra la tarea del plan, siguiendo superpowers:subagent-driven-development.
- Al final, un revisor revisa el diff completo con superpowers:requesting-code-review.

## Review Focus

1. Login anónimo (`POST /api/token/`) y refresh deben seguir funcionando tras el permiso global `IsAuthenticated` → Task 1 añade prueba.
2. `GET /api/health/` sin autenticación debe seguir devolviendo 200 (lo usan los healthchecks de Docker) → Task 1 añade prueba.
3. El Administrador de Sistemas debe poder seguir listando grupos (lo consume `frontend/src/components/admin-sistemas/useSedesYGrupos.ts`) → Task 1 añade prueba.
4. Exportación con `?async=true` cuando Redis no está disponible (producción no despliega Redis) debe responder 503 con mensaje claro, no 500 → Task 2.
5. Los endpoints de `internal_api` autenticados con JWT de servicio no deben romperse por el default global → Task 1 lo cubre con la ejecución de la suite completa.

---

### Task 1: Verificar y completar el cierre de C-1 (vista de grupos pública)

> **Contexto:** los cambios de código de esta tarea YA están aplicados en el working tree (sin commit). La tarea es revisarlos, añadir las 3 pruebas de Review Focus 1–3 y verificar la suite completa. Si al revisar `git diff` falta alguno de los cambios, aplicarlo tal como se muestra abajo.

**Files:**
- Verify: `TexCore/settings.py` (bloque `REST_FRAMEWORK`, ~línea 184)
- Verify: `gestion/views/core_views.py:25-32` (`GroupViewSet`)
- Verify: `gestion/custom_jwt_views.py` (`CustomTokenObtainPairView`, `CustomTokenRefreshView`)
- Verify: `gestion/tests/test_permisos_por_defecto.py` (9 pruebas, ya creado)
- Modify: `gestion/tests/test_core_views.py` (añadir clase al final)

**Interfaces:**
- Consumes: `gestion.permissions.IsSystemAdmin`, `gestion.tests.factories.CustomUserFactory(groups=[...])`
- Produces: `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] == ('rest_framework.permissions.IsAuthenticated',)`

- [ ] **Step 1: Revisar el diff existente**

Run: `git diff TexCore/settings.py gestion/views/core_views.py gestion/custom_jwt_views.py`
Expected: contiene exactamente estos cambios:

```python
# TexCore/settings.py, dentro de REST_FRAMEWORK, tras DEFAULT_AUTHENTICATION_CLASSES
    # Seguro por defecto: una vista que omita permission_classes queda cerrada,
    # no pública (DRF usa AllowAny si no se define). Ver test_permisos_por_defecto.py.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
```

```python
# gestion/views/core_views.py
class GroupViewSet(viewsets.ModelViewSet):
    # Los grupos sostienen el RBAC de los once roles: solo admin_sistemas
    # puede consultarlos o modificarlos (hallazgo crítico C-1).
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    pagination_class = None
    permission_classes = [IsSystemAdmin]
```

```python
# gestion/custom_jwt_views.py
from rest_framework.permissions import AllowAny, IsAuthenticated
...
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    # Login: público por diseño; explícito porque el default global exige autenticación.
    permission_classes = [AllowAny]
...
class CustomTokenRefreshView(TokenRefreshView):
    # Refresh: se autentica con la cookie de refresh, no con el access token.
    permission_classes = [AllowAny]
```

- [ ] **Step 2: Correr las 9 pruebas de regresión**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest gestion/tests/test_permisos_por_defecto.py -p no:cacheprovider --no-cov --no-migrations -q -W ignore`
Expected: `9 passed`

- [ ] **Step 3: Escribir las pruebas de Review Focus 1–3 (al final de `gestion/tests/test_core_views.py`)**

```python
class AccesoPublicoYAdminTrasPermisoPorDefectoTestCase(TestCase):
    """
    El permiso global IsAuthenticated no debe cerrar lo que es público por
    diseño (login, healthcheck) ni impedir al admin_sistemas gestionar grupos.
    Técnica: partición de equivalencia (EP) sobre rutas públicas / restringidas.
    """

    def setUp(self):
        self.client = APIClient()

    def test_health_dado_anonimo_cuando_get_entonces_200(self):
        resp = self.client.get('/api/health/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_token_dado_anonimo_con_credenciales_validas_cuando_post_entonces_200(self):
        user = CustomUserFactory(groups=['operario'])
        user.set_password('Clave-Prueba-123')
        user.save()
        resp = self.client.post(
            reverse('token_obtain_pair'),
            {'username': user.username, 'password': 'Clave-Prueba-123'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_groups_dado_admin_sistemas_cuando_get_entonces_200(self):
        self.client.force_authenticate(user=CustomUserFactory(groups=['admin_sistemas']))
        resp = self.client.get(reverse('group-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
```

Antes de correrla, confirmar el nombre de la ruta de login: `grep -n "token" TexCore/urls.py gestion/urls.py`. Si el `name=` no es `token_obtain_pair`, usar el que aparezca (o la ruta literal `'/api/token/'`).

- [ ] **Step 4: Correr las 3 pruebas nuevas**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest gestion/tests/test_core_views.py -k AccesoPublicoYAdmin -p no:cacheprovider --no-cov --no-migrations -q -W ignore`
Expected: `3 passed` (son pruebas de caracterización: deben pasar ya con el código actual; si alguna falla, el default global rompió algo y hay que corregirlo antes de seguir).

- [ ] **Step 5: Suite completa del backend**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest gestion inventory internal_api -p no:cacheprovider --no-cov --no-migrations -q -W ignore`
Expected: 0 fallos (referencia del 30-sep-2026: `1323 passed, 2 skipped` antes de las 3 pruebas nuevas → ahora `1326 passed, 2 skipped`).

- [ ] **Step 6: Sin commit** — informar al usuario los archivos modificados (`git status --short`).

---

### Task 2: Cerrar C-2 — exportación asíncrona sin broker responde 503

**Files:**
- Modify: `inventory/reporting_proxy.py` (bloque `if is_async:`, ~líneas 164-180)
- Test: `inventory/tests/test_reporting_proxy_extra.py` (clase `ReportingProxyViewExtraTestCase`)

**Interfaces:**
- Consumes: `gestion.tasks.async_export_report.delay(report_path=..., params=..., report_format=..., user_id=...)`
- Produces: respuesta `JsonResponse({"detail": ...}, status=503)` cuando el broker no está disponible.

- [ ] **Step 1: Escribir la prueba que falla** (añadir justo después de `test_get_dado_modo_async_cuando_get_entonces_202_y_no_llama_httpx`)

```python
    @patch('gestion.tasks.async_export_report.delay')
    def test_get_dado_modo_async_sin_broker_cuando_get_entonces_503_con_detalle(self, mock_delay):
        # Producción no despliega Redis: encolar debe degradar a 503 claro, no a 500.
        from kombu.exceptions import OperationalError
        admin = User.objects.create_user(username='admin_qa_sin_broker', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        mock_delay.side_effect = OperationalError('Error 111 connecting to redis:6379')

        with patch("httpx.Client.post") as mock_post:
            resp = self.client.get('/api/reporting/export/productos?async=true')
            mock_post.assert_not_called()

        self.assertEqual(resp.status_code, 503)
        self.assertIn('asíncrona', resp.json()['detail'])
```

- [ ] **Step 2: Verificar que falla**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest inventory/tests/test_reporting_proxy_extra.py -k sin_broker -p no:cacheprovider --no-cov --no-migrations -q -W ignore`
Expected: FAIL — la excepción `OperationalError` se propaga (o el handler devuelve 500), no 503.

- [ ] **Step 3: Implementación mínima** — reemplazar el bloque `if is_async:` de `inventory/reporting_proxy.py` por:

```python
        if is_async:
            from kombu.exceptions import OperationalError
            from gestion.tasks import async_export_report
            # Enviar la tarea a Celery. En producción no se despliega Redis
            # (las exportaciones síncronas miden p95 < 250 ms): si el broker no
            # está disponible se responde 503 explícito en vez de un 500.
            try:
                task = async_export_report.delay(
                    report_path=clean_path,
                    params=params,
                    report_format=report_format,
                    user_id=user.id
                )
            except OperationalError as exc:
                logger.warning(
                    "Exportación asíncrona no disponible (broker caído) para '%s': %s",
                    clean_path, exc,
                )
                return JsonResponse({
                    "detail": "La exportación asíncrona no está disponible en este entorno. "
                              "Solicite el reporte sin el parámetro async."
                }, status=503)
            return JsonResponse({
                "detail": "Reporte encolado para generación en background.",
                "task_id": task.id
            }, status=202)
```

- [ ] **Step 4: Verificar que pasa, junto con la prueba async existente**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest inventory/tests/test_reporting_proxy_extra.py inventory/tests/test_reporting_proxy.py -p no:cacheprovider --no-cov --no-migrations -q -W ignore`
Expected: todo en verde, incluido `test_get_dado_modo_async_cuando_get_entonces_202_y_no_llama_httpx`.

- [ ] **Step 5: Sin commit** — informar al usuario.

---

### Task 3: Cerrar M-4 — puertos de BD y Redis solo en localhost (entorno de desarrollo)

**Files:**
- Modify: `infrastructure/docker/docker-compose.yml` (servicio `db`, ~línea 18-19; servicio `redis`, ~línea 166-167)

**Interfaces:**
- Consumes: nada.
- Produces: SSMS en la máquina de desarrollo sigue conectando a `localhost,1433`; nadie en la red local puede alcanzar la BD ni Redis.

- [ ] **Step 1: Comprobar el estado actual**

Run: `docker compose -f infrastructure/docker/docker-compose.yml config | grep -B2 -A6 "published"`
Expected (antes): `published: "1433"` y `published: "6379"` sin `host_ip`, es decir, expuestos en `0.0.0.0`. Si Docker no está disponible, hacer `grep -n '"1433:1433"\|"6379:6379"' infrastructure/docker/docker-compose.yml` → 2 coincidencias.

- [ ] **Step 2: Cambiar los mapeos**

En el servicio `db`:
```yaml
    ports:
      # Solo loopback: SSMS local conecta a localhost,1433; la red de la
      # planta no alcanza la BD (auditoría M-4). En producción no se publica.
      - "127.0.0.1:1433:1433"
```
En el servicio `redis`:
```yaml
    ports:
      - "127.0.0.1:6379:6379"
```

- [ ] **Step 3: Verificar**

Run: `docker compose -f infrastructure/docker/docker-compose.yml config | grep -B2 -A6 "published"`
Expected: ambos puertos muestran `host_ip: 127.0.0.1`. Sin Docker: `grep -n '127.0.0.1:1433:1433\|127.0.0.1:6379:6379' infrastructure/docker/docker-compose.yml` → 2 coincidencias, y `git diff --stat` solo toca ese archivo.

- [ ] **Step 4: Sin commit** — informar al usuario. Nota para él: para administrar la BD de **producción** desde SSMS usar túnel SSH (`ssh -L 1433:<ip-contenedor-db>:1433 usuario@servidor`), nunca publicar el puerto en `docker-compose.prod.yml`.

---

### Task 4: Documentación — CHANGELOG y estado de la auditoría

**Files:**
- Modify: `CHANGELOG.md` (añadir entrada al inicio, siguiendo el formato de las existentes)
- Modify: `docs/gestion-proyecto/AUDITORIA_BACKLOG_VS_CODIGO.md` (marcar C-1, C-2 y M-4 como resueltos)

- [ ] **Step 1: Leer el formato de las 2 entradas más recientes del CHANGELOG** (`sed -n 1,60p CHANGELOG.md`) y añadir una entrada fechada 2026-09-30 con:
  - **Seguridad (C-1):** `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`; `GroupViewSet` restringido a `admin_sistemas`; login/refresh declarados `AllowAny`; 9 pruebas en `test_permisos_por_defecto.py` + 3 en `test_core_views.py`.
  - **Robustez (C-2):** `?async=true` sin broker → 503 con mensaje; 1 prueba.
  - **Infra (M-4):** puertos 1433 y 6379 de desarrollo ligados a `127.0.0.1`.
  - **Verificación:** resultado real de la suite completa del Task 1 Step 5 (copiar los números obtenidos, no los de referencia).

- [ ] **Step 2: En `AUDITORIA_BACKLOG_VS_CODIGO.md`**, bajo los encabezados `### C-1`, `### C-2` y en la fila `M-4`, añadir una línea: `> **Resuelto 2026-09-30.**` seguida de una frase con el archivo corregido y la prueba que lo protege. No reescribir el resto del informe (es evidencia histórica).

- [ ] **Step 3: Sin commit** — entregar al usuario el resumen final: `git status --short`, números de la suite y la lista de archivos por tarea.

---

## Decisiones pendientes del usuario (fuera de este plan — NO implementar)

1. **Compuerta de cobertura del núcleo** (`.github/workflows/ci.yml:229`, `continue-on-error: true`): hoy no bloquea el merge, aunque la tesis (8.2) recomienda que sea bloqueante. Quitarla puede romper el pipeline si la cobertura en SQL Server baja de `fail_under = 90` (`.coveragerc`).
2. **Historia faltante (53/54)** en la sección 7.4.1 de la tesis: identificar cuál antes de cambiar el texto.
3. **Cronograma de sprints** en la tesis (marcadores `Periodo: [fecha]`) frente al calendario académico (Tabla 14 del anteproyecto).
4. **Tabla 46 de la tesis**: tras este plan el núcleo tendrá más pruebas; actualizar el conteo con el resultado real del CI (SQL Server), no con el local.
