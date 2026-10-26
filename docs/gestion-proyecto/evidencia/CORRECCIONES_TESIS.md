# Correcciones al texto de la tesis

> **Fecha:** 12-oct-2026, ampliada el 14-oct-2026, el 19-oct-2026 y el 20-oct-2026 · **Rama:** `MES`
> **Documentos revisados:**
> - `docs/Anteproyecto_Capstone_Final_Version.pdf` (8-jul): las páginas citadas son las impresas;
> - el documento corregido del 6-oct (`Capstone_Resumen_y_Puntos_7_a_11_corregido.docx`), con el capítulo 7, las Tablas 46 y 47 y la Figura 49.

Afirmaciones que no coinciden con el sistema entregado. El contraste completo, con su evidencia, está en `CHECKLIST_EVIDENCIA_MANUAL.md`.

## 1. Anteproyecto (8-jul)

| Ubicación | Dice | El sistema | Corrección propuesta |
|---|---|---|---|
| §2.2, p. 22 y 24 | «red Docker de nueve contenedores» | El compose de desarrollo levanta 9 contenedores; el de producción, 6 (db, backend, nginx con el frontend y los 3 microservicios) | Distinguir los dos entornos, o hablar de «6 contenedores en producción» |
| p. 46 y p. 78 | Pipeline de integración continua en GitLab CI | **Se cumple (20-oct-2026, ADR-014)**: GitLab CE autoalojado es la plataforma principal; GitHub es solo un espejo | Sin corrección en lo de GitLab CI. En la p. 78, el umbral del 75 % y la mención del pipeline se sostienen |
| §5.1, p. 65 (DoD) | «superación de los análisis estáticos (flake8, bandit, detect-secrets)» | Ruff (estilo y reglas de seguridad `S`), mypy, Semgrep y detect-secrets, todos bloqueantes | «superación de los análisis estáticos (Ruff, mypy, Semgrep y detect-secrets)» |
| §5.3, p. 68–69 | «flake8» y «bandit» | Ruff (ADR-015), con mypy, Semgrep y detect-secrets. «GitLab CI» y «GitLab Container Registry» **se cumplen** (ADR-014) | Reemplazar solo flake8 y bandit: usar el texto de §5 de este documento |
| §5.3, p. 69 | Umbral de cobertura del 75 % | El gate del backend es del 90 % (92,5 % medido el 20-oct) | Mantener el 75 % como mínimo comprometido y mencionar el gate real, o subir la cifra |
| p. 78 (marco de seguridad) | «cumpla formalmente con los principios de privacidad desde el diseño, respetando a cabalidad las normativas vigentes en la LOPDP» junto con los principios de la ISO/IEC 27001 | **Resuelto el 19-oct-2026** (**RS-19** cerrado): además del control de acceso por rol, la trazabilidad inmutable con justificación, el cifrado en tránsito y los respaldos, los datos de identificación (`Cliente.ruc_cedula` y `CustomUser.date_of_birth`) se guardan cifrados con Fernet | La afirmación ya se sostiene, pero conviene precisar el alcance en lugar de dejarla genérica: **usar el texto de §3 de este documento**, que nombra las tres capas y dice qué campos se cifran. Contraste en `docs/requerimientos/AUDITORIA_CALIDAD.md` §I.5 |
| RNF-01, Tabla 6, p. 19 | «Datos sensibles encriptados» | Cifrado en tránsito obligatorio (HTTPS con HSTS; el puerto 80 redirige), contraseñas con hash y, desde el 19-oct-2026, **cifrado selectivo en reposo de los datos de identificación**. La base no tiene TDE (cifrado de todo el archivo de datos), que sigue sujeto a la edición licenciada (**RS-18**) | Precisar el alcance: «datos cifrados en tránsito, datos personales de identificación cifrados en reposo y credenciales con hash». TDE queda como medida complementaria del plan de despliegue, no como lo que cubre este RNF |

## 2. Documento corregido (6-oct)

| Afirmación | El sistema | Corrección |
|---|---|---|
| «Réplica equivalente en GitLab CI» | **Se cumple**: GitLab CI es hoy el pipeline principal (ADR-014); no hay réplica porque GitHub Actions se retiró | Sin corrección |
| La auditoría de dependencias se reporta como advertencia (§7.2.13) | `pip-audit` y `npm audit` son **bloqueantes** | Actualizar el §7.2.13 |
| TEX-54 «Completada»; Sprint 8 en staging | Pendiente (congelamiento y staging) | Completar TEX-54 o corregir el texto, en el resumen de historias y en la Sprint Review del Sprint 8 |
| 331 commits; tamaño del código | 370 commits al 8-oct, y la cifra sigue creciendo | Actualizar las cifras al cierre |
| Tabla 46 (resultados de pruebas) | Anterior al 7-oct | Actualizar con `EVIDENCIA_POR_SPRINT.md` (SQL Server 2022, 0 fallidas) y la cobertura final |
| Tabla 47 (Locust) | Coincide con la corrida del 29-sep (`carga_100_2026-09-29_stats.csv`), anterior a los 3 años de datos | Reemplazar por las cifras del 8-oct con 100 y 250 usuarios (`docs/requerimientos/EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §3) |
| Figura 49 (pipeline) | Ahora incluye ESLint, el typecheck de las pruebas del frontend y los dos gates de detect-secrets | Actualizar la figura y el texto |
| §7.2.3 y la tabla de herramientas | Nombran flake8 y bandit | Igual que la DoD del §5.1 |

---

## 3. Texto propuesto para la tesis — RNF-01 / RS-19 (seguridad de la información)

> **Añadido el 19-oct-2026**, al cerrar **RS-19**. Reemplaza la redacción genérica de
> la p. 78 (marco de seguridad) y precisa el RNF-01 de la Tabla 6 (p. 19). Está escrito
> para que cada afirmación tenga su evidencia en el repositorio: nada que el sistema no
> haga. Evidencia: `docs/arquitectura/CIFRADO_DATOS_PERSONALES.md`,
> `docs/requerimientos/AUDITORIA_CALIDAD.md` §I.5 y
> `gestion/tests/test_cifrado_datos_personales.py`.

### 3.1 Párrafo para pegar

> Para dar cumplimiento a la Ley Orgánica de Protección de Datos Personales (LOPDP,
> 2021) y al principio de *privacidad desde el diseño*, el sistema implementa una
> estrategia de cifrado en capas:
>
> 1. **Cifrado en tránsito.** Toda la comunicación entre el cliente y el servidor viaja
>    sobre TLS 1.2/1.3 con HSTS, y el puerto 80 redirige a HTTPS. La sesión se sostiene
>    con tokens JWT en cookies `HttpOnly`, `Secure` y `SameSite`, y la autenticación
>    entre el núcleo y los tres microservicios satélite usa JWT con firma asimétrica
>    RS256. La conexión con SQL Server se establece con `Encrypt=yes`.
> 2. **Cifrado selectivo en reposo, en la capa de aplicación.** Los datos personales de
>    identificación —la cédula o el RUC del cliente (`Cliente.ruc_cedula`) y la fecha de
>    nacimiento del usuario (`CustomUser.date_of_birth`)— se cifran en la capa de
>    aplicación con el esquema simétrico autenticado Fernet (AES-128 en modo CBC, con
>    HMAC-SHA256 de integridad), antes de llegar a la base de datos. La clave
>    criptográfica no reside en el código ni en la base: se inyecta por variable de
>    entorno y el sistema no arranca sin ella. Para no perder el rendimiento de las
>    consultas transaccionales —el texto cifrado de un mismo valor es distinto en cada
>    escritura, por el vector de inicialización aleatorio— la búsqueda por identificación
>    y la restricción de unicidad por sede se resuelven mediante un **índice ciego**: un
>    resumen unidireccional HMAC-SHA256 del valor, con su propio índice en la base de
>    datos, que permite la igualdad exacta sin descifrar ni exponer el dato.
> 3. **Control de acceso y trazabilidad.** Lo anterior se complementa con el control de
>    acceso basado en roles (RBAC) aplicado a los once roles del sistema y al cien por
>    ciento de los *endpoints* de la API, con aislamiento por sede y por área, y con un
>    registro de auditoría inmutable que exige justificación en los cambios a datos
>    maestros. Ese registro no almacena los datos personales en claro: la fecha de
>    nacimiento se audita por su resumen HMAC, de modo que el cambio queda demostrado
>    sin revelar el dato.

### 3.2 Para el RNF-01 de la Tabla 6 (p. 19)

Donde hoy dice «Datos sensibles encriptados», el enunciado verificable es:

> Datos cifrados en tránsito (TLS 1.2/1.3 con HSTS), datos personales de identificación
> cifrados en reposo con Fernet (AES-128-CBC + HMAC-SHA256) y credenciales almacenadas
> con función de *hash* de contraseña.

### 3.3 Precisiones que conviene no omitir

Si el tribunal pregunta por el alcance, estas son las fronteras reales y es mejor
declararlas que dejar que se asuman:

| Afirmación | Alcance real |
|---|---|
| «Cifrado en reposo» | **Selectivo**: los dos campos de identificación, no todo el archivo de datos. El cifrado transparente de la base (TDE) cubriría el archivo completo, pero depende de la edición de SQL Server que licencie la organización (riesgo **RS-18**) y queda como medida complementaria del plan de despliegue. |
| «Privacidad desde el diseño» | Se cumple en lo técnico (minimización del dato expuesto, cifrado, control de acceso, trazabilidad). Las medidas **organizativas** que la LOPDP también exige —consentimiento, política de retención, designación del responsable de tratamiento— corresponden a Interfibra S.A. y son parte de la puesta en marcha (§5.4). |
| «Sin comprometer el rendimiento» | Medido: las consultas por identificación van por el índice ciego, que es un índice de la base, así que conservan el orden de magnitud anterior. Lo que **sí** se pierde es la búsqueda parcial (`LIKE`) y la ordenación por el campo cifrado, que el sistema no usaba. |
| Gestión de la clave | Si se pierde `FIELD_ENCRYPTION_KEYS`, los datos cifrados no se recuperan. La rotación está prevista (lista de claves: la primera cifra, todas descifran) y documentada en `SECURITY.md`. |

---

## 4. Sin corrección — RNF-02 y OWASP API1/API2 (control de acceso)

El texto de la tesis se sostiene tal como está: la Tabla 7 (p. 19) pide verificar el RNF-02
«mediante revisión de permisos por rol y pruebas de acceso no autorizado», y la comparación
de arquitecturas afirma que «los riesgos API1 y API2 del OWASP API Security Top 10 2023
quedan mitigados». El sistema lo cumple, con pruebas automáticas que recorren todas las rutas
de la API: el contraste y su evidencia están en `CHECKLIST_EVIDENCIA_MANUAL.md` (RNF-02),
`docs/requerimientos/AUDITORIA_CALIDAD.md` §I.2 y `docs/matriz_trazabilidad_pruebas.md`
(sección RNF-02). No hay que cambiar el documento.

### 4.1 Precisiones por si el tribunal pregunta

| Afirmación | Alcance real |
|---|---|
| «100 % de los endpoints» | Las rutas de negocio, sí. Las 6 rutas públicas son el inicio de sesión, la renovación del token, el *healthcheck*, los dos *endpoints* de token entre servicios (que validan el secreto del servicio) y el registro de errores del navegador, que está acotado en tamaño y limitado por IP. |
| Roles que «ven todas las sedes» | El Administrador de Sistemas y el Ejecutivo ven todas las sedes por diseño; la prueba de autorización por objeto cubre los 9 roles restantes. |
| Indicadores del área | El KPI de área no exige un rol: se acota al área del propio usuario, y sin área asignada responde 403. |

---

## 5. Texto propuesto para la tesis — análisis estático con Ruff (§5.1 y §5.3)

> **Añadido el 20-oct-2026.** Es la única corrección de redacción del pipeline: el sistema
> usa **Ruff** en lugar de flake8 y bandit desde el 5-oct-2026. La decisión, con sus cifras,
> está en `docs/arquitectura/ADR/ADR_015_RUFF_EN_LUGAR_DE_FLAKE8_Y_BANDIT.md`.

### 5.1 Para la Definición de Hecho (§5.1, p. 65)

Donde dice «superación de los análisis estáticos (flake8, bandit, detect-secrets)»:

> superación de los análisis estáticos (Ruff para estilo, errores y reglas de seguridad;
> mypy para tipos; Semgrep para análisis estático de seguridad, y detect-secrets para
> secretos expuestos)

### 5.2 Para la fase de Integración y Análisis Estático (§5.3, p. 68–69)

Donde dice «validaciones automatizadas de sintaxis y formato (flake8), detección de
vulnerabilidades con bandit, y escaneo de secretos expuestos mediante detect-secrets»:

> validaciones automatizadas de estilo, errores y formato con Ruff —que integra las reglas
> de pycodestyle y pyflakes (las de flake8) y las reglas de seguridad de bandit—, verificación
> de tipos con mypy, análisis estático de seguridad con Semgrep y escaneo de secretos
> expuestos mediante detect-secrets. Todos son bloqueantes.

### 5.3 Párrafo de justificación (si el tribunal pregunta por el cambio)

> Durante la ejecución se reemplazaron flake8 y bandit por Ruff, un analizador estático para
> Python que reúne en una sola herramienta las reglas de estilo y errores de flake8 y las
> reglas de seguridad de bandit. El cambio se adoptó por cinco motivos: (1) una única
> herramienta y una única configuración, idéntica en el pipeline y en el control previo al
> *commit*, en lugar de dos herramientas configuradas por separado; (2) cobertura del cien por
> ciento del código Python del repositorio —con flake8 el pipeline solo revisaba los cuatro
> paquetes del núcleo y quedaban 48 violaciones sin detectar en los microservicios y los
> *scripts*—; (3) detección de defectos reales y no solo de estilo, mediante reglas de Django,
> de fechas sin zona horaria, de manejo de excepciones, de bloqueos en código asíncrono y de
> complejidad ciclomática máxima de 15; (4) velocidad, porque al estar escrito en Rust analiza
> el repositorio en segundos sin alargar el pipeline, y (5) que la migración se hizo sin
> regresión: todo lo que flake8 rechazaba Ruff lo sigue rechazando, y cada regla nueva entró
> con cero violaciones. El objetivo de la fase —que ningún cambio con defectos de estilo,
> seguridad o secretos expuestos llegue a la rama principal— se mantiene y queda ampliado.
