# Política de seguridad — TexCore

## Versiones con soporte

Solo recibe correcciones la versión desplegada desde `master`. Las ramas de trabajo y `staging` son temporales.

## Reportar una vulnerabilidad

- No abras un issue público. Usa **Security → Report a vulnerability** del repositorio (aviso privado de GitHub) o escribe al responsable del sistema en la organización.
- Incluye: componente afectado (backend, nginx, `printing_service`, `scanning_service`, `reporting_excel`, base de datos o pipeline), pasos para reproducir, impacto y, si la tienes, una propuesta de corrección.
- **Plazos de respuesta:**

| Severidad (CVSS) | Acuse de recibo | Corrección desplegada |
|---|---|---|
| Crítica (9,0–10) | 24 h | 72 h |
| Alta (7,0–8,9) | 48 h | 7 días |
| Media (4,0–6,9) | 5 días hábiles | 30 días |
| Baja (< 4,0) | 10 días hábiles | siguiente release |

- La corrección entra por el flujo normal (MR a `staging` → MR a `master`), con su prueba de regresión, y queda registrada en `CHANGELOG.md` y en `docs/requerimientos/REGISTRO_RIESGOS.md`. Si la vulnerabilidad se está explotando, se aplica primero el rollback (`rollback:produccion`) o la mitigación en nginx.

## Controles automáticos

| Control | Dónde | Bloquea |
|---|---|---|
| Ruff (reglas `S`), Semgrep, mypy, detect-secrets | `.gitlab-ci.yml` (`lint:backend`, `sast:semgrep`) | El merge |
| pip-audit (4 servicios) y npm audit | `audit:*` y `seguridad:*` | El merge / aviso semanal |
| Trivy sobre las 6 imágenes | `scan:trivy`, `seguridad:contenedores` | El despliegue |
| yamllint y shellcheck (el pipeline y los scripts) | `lint:pipeline` | El merge |
| Convención de pruebas ISTQB y rutas públicas fuera de la lista blanca (RNF-02) | `lint:istqb`, `lint:permisos` | El merge |
| Firma con clave (cosign) y procedencia SLSA, verificadas en el servidor | `build:imagenes`, `deploy:produccion` | El despliegue |
| Métricas DORA | `gobierno:dora` (semanal) | — (seguimiento) |
| Renovate (pip, npm, imágenes base por digest, el pipeline) | `dependencias:renovate` y `renovate.json` | — (MR semanales a `staging`) |

Las excepciones (`# noqa`, `# nosemgrep`, entradas auditadas de detect-secrets) llevan su motivo en el mismo lugar y se revisan cada trimestre.

## Rotación de secretos

Los secretos de la aplicación viven solo en `.env.prod` del servidor (permisos 600); no pasan por GitHub. Procedimientos en `docs/arquitectura/GUIA_DESPLIEGUE.md` §4.4.

| Secreto | Rotación ordinaria | Rotación inmediata si… |
|---|---|---|
| `SECRET_KEY` | Anual | Exposición del servidor o del archivo. Invalida las sesiones activas. |
| Par RSA `INTERNAL_JWT_*` | Anual | Exposición de la clave privada. Recrear los 6 servicios. |
| `FIELD_ENCRYPTION_KEYS` (datos personales en reposo, RS-19) | Anual | Exposición. Rotación **sin parada**: la clave nueva va primera y la vieja se queda detrás, `manage.py cifrar_datos_personales --reparar` reescribe lo guardado, y luego se retira la vieja. **Si se pierde, los datos cifrados no se recuperan**: guárdala también junto al respaldo cifrado. Ver `docs/arquitectura/CIFRADO_DATOS_PERSONALES.md` §4. |
| `BLIND_INDEX_KEY` (índice ciego, RS-19) | No se rota por calendario | Exposición. Al cambiarla, las búsquedas por identificación dejan de encontrar nada hasta correr `manage.py cifrar_datos_personales --recalcular-indices`. |
| `SCANNING_SERVICE_SECRET`, `REPORTING_SERVICE_SECRET` | Anual | Exposición. `register_services --force` y recrear el satélite. |
| `DB_PASSWORD` (cuenta `sa`) | Anual | Exposición. `ALTER LOGIN sa WITH PASSWORD` y recrear backend y db. |
| Certificado TLS | Al vencer (Let's Encrypt: automática cada 90 días) | Compromiso de la clave privada. |
| Token del runner propio | Al reinstalar el runner | Compromiso del servidor. Eliminarlo en Settings → Actions → Runners. |
| Contraseñas de usuarios | Política de la organización | Sospecha de acceso indebido (el administrador la restablece). |

## Revisión trimestral

Cada trimestre (enero, abril, julio y octubre), el responsable del sistema:

1. Revisa las métricas DORA de `gobierno:dora` y anota las acciones en el backlog.
2. Actualiza las versiones fijadas que Renovate no cubre: Ruff, Semgrep, Trivy, cosign y detect-secrets en `.gitlab-ci.yml`, `infrastructure/gitlab/Dockerfile.ci-tools` y `.pre-commit-config.yaml`. Rota además el par de claves de cosign y el token de GitLab (`GUIA_GITLAB.md` §7).
3. Revisa cada excepción vigente de los linters y escáneres y retira las que ya no aplican.
4. Mide el tiempo del pipeline (CI y release) y corrige los pasos que más crecieron.
5. Prueba una restauración del respaldo (`GUIA_DESPLIEGUE.md` §4.3) y un rollback en el staging efímero.
