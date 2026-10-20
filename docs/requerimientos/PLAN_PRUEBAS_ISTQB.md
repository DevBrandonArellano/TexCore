# Plan de pruebas — TexCore (ISTQB CTFL v4.0)

> **Fecha:** 20-oct-2026 · **Estado:** vigente · **Rama:** `MES`
> Sustituye como plan vigente a `PLAN_PRUEBAS.md` (marzo–mayo de 2026), que se conserva como registro histórico de los 112 casos `TC-xxx`.
> La tesis (§5.3 y p. 78) afirma que los casos de prueba adoptan las técnicas de caja negra del ISTQB (CTFL v4.0, 2023) y que la suite actúa como compuerta de calidad del pipeline. Este documento reúne en un solo lugar cómo se cumple.

## 1. Alcance y objetivos

| Elemento | Detalle |
|---|---|
| Objeto de prueba | Núcleo Django/DRF (`gestion`, `inventory`, `internal_api`), 3 microservicios FastAPI (`scanning_service`, `printing_service`, `reporting_excel`) y el frontend React/TypeScript |
| Entorno de referencia | SQL Server 2022 efímero en Docker (`scripts/run_backend_tests.sh`); SQLite en memoria solo para iterar |
| Objetivo 1 | Que cada requisito (RF, RNF, regla de negocio) tenga al menos una prueba automática trazable |
| Objetivo 2 | Que ningún cambio llegue a la rama principal con pruebas fallidas, cobertura bajo el umbral o sin la convención ISTQB |
| Objetivo 3 | Evidencia reproducible para la defensa de la tesis (`matriz_trazabilidad_pruebas.md`, `CHECKLIST_EVIDENCIA_MANUAL.md`) |
| Fuera de alcance | Pruebas de usabilidad con usuarios (RNF-05) y capacitación: las ejecuta la puesta en marcha (§5.4 de la tesis) |

## 2. Niveles de prueba

| Nivel (CTFL v4.0) | Qué se prueba | Herramienta | Dónde |
|---|---|---|---|
| Componente (unidad) | Modelos, servicios, serializadores, reglas de negocio, componentes y hooks | `unittest`/`pytest`, Vitest + Testing Library | `*/tests/`, `frontend/src/**/*.test.tsx` |
| Integración | Vistas DRF con base de datos real, permisos por rol y por sede, canal servicio a servicio (JWT RS256), proxies | `APIClient`, `TestClient` de FastAPI, `respx` | `gestion/tests`, `inventory/tests`, `internal_api/tests`, `*_service/tests/integration` |
| Sistema | Flujos extremo a extremo en el stack de producción con 3 años de datos | `scripts/smoke_test.py`, `scripts/staging_efimero.sh`, Locust | `docs/gestion-proyecto/evidencia/` |
| Aceptación | Casos de uso por rol contra los criterios de aceptación de las historias | Checklist manual con el usuario | `CHECKLIST_EVIDENCIA_MANUAL.md` |

## 3. Tipos de prueba

| Tipo | Cobertura |
|---|---|
| Funcional | Reglas de negocio de cada módulo (producción, inventario y MRP, comercial, tintorería, despacho, administración) |
| Seguridad (RNF-01, RNF-02) | Acceso no autorizado en todas las rutas, autorización por objeto entre sedes, CSRF, cifrado de datos personales. `test_acceso_no_autorizado_global.py`, `test_cifrado_datos_personales.py` |
| Rendimiento (RNF-03) | Consultas < 3 s y escaneo QR < 2500 ms; carga con 100 y 250 usuarios (Locust); consultas acotadas por pantalla |
| Estructural | Cobertura de sentencias y ramas (caja blanca) |
| Regresión | Toda la suite en cada integración; las pruebas de defectos corregidos van primero en rojo |

## 4. Técnicas de diseño

Cada archivo de prueba declara las técnicas que aplica en su cabecera («Técnicas ISTQB aplicadas»), y el gate del pipeline lo exige.

| Sigla | Técnica | Uso en TexCore |
|---|---|---|
| EP | Partición de equivalencia | Roles (permitido / no permitido), sede propia / ajena, entradas válidas / inválidas |
| BVA | Análisis de valores límite | Cero, vacío, negativo, mínimo y máximo, 9 / 10 caracteres de una justificación, el umbral exacto de stock |
| TD | Tabla de decisión | Combinaciones de rol, sede y estado que determinan el permiso (matriz de roles) |
| STT | Transición de estados | Orden de producción, pedido, plan, corrida, máquina, receta |
| CB | Caja blanca (decisiones y ramas) | Ramas de error, `except`, transacciones atómicas y reversiones |
| RND | Rendimiento (ISO/IEC 25010) | Tiempos y número de consultas por pantalla |

**Convención de nombres** (CTFL v4.0): `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]` en Python y «dado … cuando … entonces …» en el frontend. La aplica `scripts/auditar_convencion_pruebas.py`.

## 5. Criterios de entrada y de salida

**Entrada** (para integrar un cambio):
- el código compila y pasa los análisis estáticos (Ruff, `ruff format`, mypy, Semgrep, detect-secrets);
- la prueba de un defecto corregido se escribió primero y falló antes del cambio.

**Salida** (para aceptar un cambio):

| Criterio | Umbral | Dónde se hace cumplir |
|---|---|---|
| Pruebas fallidas | 0 | Pipeline |
| Cobertura del núcleo | ≥ 90 % (`fail_under`) | `.coveragerc` |
| Cobertura de `scanning_service` y `reporting_excel` | ≥ 90 % | `pytest.ini` de cada servicio |
| Cobertura de `printing_service` | ≥ 95 % | `printing_service/pytest.ini` |
| Cobertura del frontend | líneas 95, funciones 91, ramas 89, sentencias 94 | `frontend/vite.config.ts` |
| Tipos | `tsc --noEmit` y `mypy` sin errores | Pipeline |
| Convención ISTQB | 0 hallazgos | `scripts/auditar_convencion_pruebas.py` |
| Acceso no autorizado | 0 rutas públicas fuera de la lista blanca | `scripts/auditar_permisos_backend.py` |
| Dependencias y contenedores | sin CVE crítico ni alto con parche | `pip-audit`, `npm audit`, Trivy |

El mínimo comprometido en la tesis es del **75 %** (§5.1, §5.3 y p. 78); el sistema exige más.

## 6. Entorno y datos

- **Base de datos:** SQL Server 2022 por digest, con RCSI, creada por prueba; las migraciones y los índices nativos (V2, V4, V5) se ejercitan.
- **Datos:** fábricas (`gestion/tests/factories.py`); las pruebas no dependen de datos de demostración.
- **Servicios externos:** los satélites se prueban con dobles (`respx`, `dependency_overrides`) y su contrato con el núcleo con pruebas de integración propias.
- **Claves de cifrado de prueba:** solo para la suite, marcadas para detect-secrets.

## 7. Riesgos de la calidad

Los riesgos y su mitigación están en `REGISTRO_RIESGOS.md`. Los que condicionan este plan:

| Riesgo | Mitigación en las pruebas |
|---|---|
| Autorización por objeto incompleta (RS-21) | Recorrido de todas las rutas con los roles acotados a una sede |
| Cifrado de datos personales (RS-19) | 34 pruebas de campo cifrado, índice ciego y rotación de claves |
| Migraciones sobre datos reales (RD-05) | Pruebas de ida y vuelta y verificación sobre un respaldo |
| Divergencia entre suites y CI | Un único pipeline (ADR-014) |

## 8. Trazabilidad

`docs/matriz_trazabilidad_pruebas.md` vincula cada módulo y requisito con su archivo de prueba, la técnica ISTQB y el estado. `CHECKLIST_EVIDENCIA_MANUAL.md` contrasta cada afirmación de la tesis con su evidencia (✅ cumple, ❌ no cumple, ⏳ pendiente, 📅 planificado). La cadena es: **requisito de la tesis → matriz → archivo de prueba → técnica declarada en su cabecera → gate del pipeline**.

## 9. Métricas (20-oct-2026)

| Suite | Pruebas | Cobertura |
|---|---|---|
| Núcleo (SQL Server 2022) | 1944 al cierre del 20-oct | 92,5 % |
| `scanning_service` | 66 | 94,3 % |
| `printing_service` | 114 | 98,9 % |
| `reporting_excel` | 76 | 99,2 % |
| Frontend | 1981 en 138 archivos | por encima de los umbrales |
| Convención de nombres | 4078 de 4078 | — |
| Archivos de prueba con la técnica declarada | 326 de 326 | — |

## 10. Mantenimiento

- Una prueba nueva sigue la convención y su archivo declara la técnica; el gate falla si no.
- Al corregir un defecto se agrega su prueba (en rojo antes del cambio) y se registra en `matriz_trazabilidad_pruebas.md`.
- Las cifras de este documento se actualizan en cada cierre de sprint, junto con el `CHANGELOG.md`.
