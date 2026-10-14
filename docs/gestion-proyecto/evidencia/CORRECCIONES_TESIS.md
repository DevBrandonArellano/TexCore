# Correcciones al texto de la tesis

> **Fecha:** 12-oct-2026, ampliada el 14-oct-2026 · **Rama:** `MES`
> **Documentos revisados:**
> - `docs/Anteproyecto_Capstone_Final_Version.pdf` (8-jul): las páginas citadas son las impresas;
> - el documento corregido del 6-oct (`Capstone_Resumen_y_Puntos_7_a_11_corregido.docx`), con el capítulo 7, las Tablas 46 y 47 y la Figura 49.

Afirmaciones que no coinciden con el sistema entregado. El contraste completo, con su evidencia, está en `CHECKLIST_EVIDENCIA_MANUAL.md`.

## 1. Anteproyecto (8-jul)

| Ubicación | Dice | El sistema | Corrección propuesta |
|---|---|---|---|
| §2.2, p. 22 y 24 | «red Docker de nueve contenedores» | El compose de desarrollo levanta 9 contenedores; el de producción, 6 (db, backend, nginx con el frontend y los 3 microservicios) | Distinguir los dos entornos, o hablar de «6 contenedores en producción» |
| p. 46 y p. 78 | Pipeline de integración continua en GitLab CI | GitHub Actions | «GitHub Actions» |
| §5.1, p. 65 (DoD) | «superación de los análisis estáticos (flake8, bandit, detect-secrets)» | Ruff (estilo y reglas de seguridad `S`), mypy, Semgrep y detect-secrets, todos bloqueantes | «superación de los análisis estáticos (Ruff, mypy, Semgrep y detect-secrets)» |
| §5.3, p. 68–69 | «configurado a través de GitLab CI», «flake8», «bandit», «GitLab Container Registry» | GitHub Actions, Ruff y GitHub Container Registry | Reemplazar los cuatro términos |
| §5.3, p. 69 | Umbral de cobertura del 75 % | El gate del backend es del 90 % (92,2 % medido el 14-oct) | Mantener el 75 % como mínimo comprometido y mencionar el gate real, o subir la cifra |
| p. 78 (marco de seguridad) | «cumpla formalmente con los principios de privacidad desde el diseño, respetando a cabalidad las normativas vigentes en la LOPDP» junto con los principios de la ISO/IEC 27001 | Hay control de acceso por rol, trazabilidad inmutable con justificación, cifrado en tránsito y respaldos; **no hay cifrado de los datos personales en reposo** (`Cliente.ruc_cedula` y la fecha de nacimiento del usuario están en claro) | Dos caminos, pendientes de decisión (riesgo **RS-19**): cifrar esos campos (o TDE en la base) antes de la puesta en marcha, o escribir solo lo que el sistema hace: «control de acceso, trazabilidad y cifrado en tránsito». Contraste en `docs/requerimientos/AUDITORIA_CALIDAD.md` §I.5 |
| RNF-01, Tabla 6, p. 19 | «Datos sensibles encriptados» | Cifrado en tránsito obligatorio (HTTPS con HSTS; el puerto 80 redirige) y contraseñas con hash. La base no tiene cifrado en reposo (TDE) | Precisar el alcance: «datos cifrados en tránsito y credenciales con hash», o agregar TDE al plan de despliegue |

## 2. Documento corregido (6-oct)

| Afirmación | El sistema | Corrección |
|---|---|---|
| «Réplica equivalente en GitLab CI» | GitLab CI se retiró (commit `a65ff02`) | Quitar la mención o justificar el retiro |
| La auditoría de dependencias se reporta como advertencia (§7.2.13) | `pip-audit` y `npm audit` son **bloqueantes** | Actualizar el §7.2.13 |
| TEX-54 «Completada»; Sprint 8 en staging | Pendiente (congelamiento y staging) | Completar TEX-54 o corregir el texto, en el resumen de historias y en la Sprint Review del Sprint 8 |
| 331 commits; tamaño del código | 370 commits al 8-oct, y la cifra sigue creciendo | Actualizar las cifras al cierre |
| Tabla 46 (resultados de pruebas) | Anterior al 7-oct | Actualizar con `EVIDENCIA_POR_SPRINT.md` (SQL Server 2022, 0 fallidas) y la cobertura final |
| Tabla 47 (Locust) | Coincide con la corrida del 29-sep (`carga_100_2026-09-29_stats.csv`), anterior a los 3 años de datos | Reemplazar por las cifras del 8-oct con 100 y 250 usuarios (`docs/requerimientos/EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §3) |
| Figura 49 (pipeline) | Ahora incluye ESLint, el typecheck de las pruebas del frontend y los dos gates de detect-secrets | Actualizar la figura y el texto |
| §7.2.3 y la tabla de herramientas | Nombran flake8 y bandit | Igual que la DoD del §5.1 |
