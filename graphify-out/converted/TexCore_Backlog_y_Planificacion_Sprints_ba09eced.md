<!-- converted from TexCore_Backlog_y_Planificacion_Sprints.docx -->







TexCore
Product Backlog y Planificacion de Sprints

Sistema de digitalizacion y seguimiento de Ordenes de Produccion
Interfibra S.A.

Brandon Arellano
Proyecto Capstone
Universidad de las Americas

23 de septiembre de 2026

Documento derivado de las secciones 5.1 y 5.2 y de la Tabla 14 del documento Capstone. Marco de trabajo Scrum.

# Indice
Pulse F9 sobre este indice para generarlo.

# Product Backlog — TexCore
Proyecto: TexCore — Sistema de digitalización y seguimiento de Órdenes de Producción Organización: Interfibra S.A. Autor: Brandon Arellano Marco de trabajo: Scrum (§5.1 del documento Capstone) Fuente normativa: Anteproyecto_Capstone_Final_Version.docx, §5.2 y Tabla 14 Fecha de elaboración: 23 de septiembre de 2026
## 1. Propósito del documento
Este documento constituye el Product Backlog de TexCore: la lista única, ordenada y priorizada de todo el trabajo necesario para construir el producto. Cada elemento se expresa como una historia de usuario con criterios de aceptación verificables.
El backlog deriva directamente de los Elementos del Backlog declarados en la Tabla 14 del documento Capstone. No introduce alcance nuevo: descompone en historias trazables lo que el documento ya comprometió por sprint.
## 2. Convenciones
### 2.1 Formato de historia
Cada historia sigue la plantilla de Connextra:
Como \<rol\> quiero \<funcionalidad\> para \<beneficio de negocio\>.
### 2.2 Formato de criterios de aceptación
Los criterios de aceptación se expresan en Gherkin en español (Dado / Cuando / Entonces / Y). Esta elección no es estética: el estándar de pruebas del proyecto nombra cada test como test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado], de modo que cada criterio de aceptación se corresponde uno a uno con un caso de prueba automatizado, conforme a ISTQB CTFL v4.0.
### 2.3 Estimación
Story Points en escala de Fibonacci (1, 2, 3, 5, 8, 13). La referencia de calibración es TEX-12 (registro de lote) = 5 puntos.

Capacidad declarada: el §5.5 del Capstone establece 640 horas de esfuerzo en 16 semanas de desarrollo, es decir 80 horas por sprint con dedicación de jornada completa. Los ocho sprints de desarrollo suman 267 puntos, de donde resulta una velocidad objetivo de 33 puntos por sprint (≈ 2,4 h por punto).
Los sprints 5 y 6 quedan por encima de esa media (37 puntos cada uno). Es una sobrecarga asumida conscientemente: concentran la lógica de negocio de mayor valor —control de crédito, reconciliación FIFO y dosificación química— y sus historias Could ya fueron desplazadas a otros sprints. Si la velocidad real se sitúa por debajo de 33 puntos, las candidatas a diferir son TEX-36 y TEX-43, ambas Should.
### 2.4 Prioridad (MoSCoW)

### 2.5 Estado
Todas las historias nacen en `To Do`, conforme al plan de ejecución aprobado en el documento Capstone.
## 3. Definición de Hecho (DoD) transversal
Conforme al §5.1 del documento Capstone, todo incremento debe cumplir:
- Código integrado en la rama principal a través del pipeline de CI/CD
- Superación de los análisis estáticos (flake8, bandit, detect-secrets)
- Cobertura de pruebas automatizadas no inferior al 75 % en el núcleo
- Registro de auditoría en las operaciones críticas
- Despliegue verificado en el ambiente de staging
## 4. Mapa de épicas
Las nueve épicas se corresponden con los nueve sprints de la Tabla 14.

## 5. Roles del sistema
Los once roles definidos en el Capstone (Tabla 13) y en docs/historias-usuarios/ROLES_Y_PERMISOS.md:

# 6. Backlog detallado
## EP-00 · Infraestructura y DevOps
Sprint 0 (21 Sep – 02 Oct) · Objetivo: Establecer la infraestructura y automatizar los despliegues. Entregable: Entorno de desarrollo operativo y backlog priorizado.
### TEX-01 · Orquestación de contenedores con Docker Compose
Como desarrollador quiero levantar todo el stack de TexCore con un solo comando para eliminar las diferencias de entorno entre mi equipo y el servidor.

Criterios de aceptación
- CA-1 — Dado un equipo con Docker instalado y sin configuración previa, cuando ejecuto docker compose up, entonces se levantan los contenedores de backend Django, frontend React, base de datos SQL Server 2022 y los tres microservicios FastAPI, y todos alcanzan estado healthy sin intervención manual.
- CA-2 — Dado el stack levantado, cuando consulto el estado de los contenedores, entonces ninguno presenta reinicios en bucle ni errores en el log de arranque.
- CA-3 — Dado que detengo y vuelvo a levantar el stack, cuando consulto la base de datos, entonces los datos persisten por estar montados en un volumen nombrado.
### TEX-02 · Red de contenedores aislada y comunicación entre servicios
Como desarrollador quiero que los servicios se comuniquen por nombre dentro de una red privada para que ningún puerto interno quede expuesto al exterior.

Criterios de aceptación
- CA-1 — Dado el stack levantado, cuando el backend resuelve el nombre de host de un microservicio, entonces la conexión se establece por la red interna sin pasar por el host.
- CA-2 — Dado un intento de conexión directa desde fuera del host al puerto de la base de datos, cuando se ejecuta la conexión, entonces es rechazada por no estar el puerto publicado.
### TEX-03 · API Gateway con Nginx como punto único de entrada
Como administrador de sistemas quiero un único punto de entrada que enrute al backend, al frontend y a los microservicios para simplificar el despliegue y la gestión de certificados.

Criterios de aceptación
- CA-1 — Dado el gateway en ejecución, cuando solicito una ruta de API, entonces Nginx la enruta al backend Django conservando cabeceras de origen.
- CA-2 — Dado el gateway en ejecución, cuando solicito la raíz del sitio, entonces Nginx sirve la aplicación React compilada.
- CA-3 — Dado una petición que atraviesa el gateway, cuando el backend registra la auditoría, entonces la IP de origen real se preserva y no se sustituye por la del proxy.
### TEX-04 · Pipeline de CI con Quality Gates
Como desarrollador quiero que cada push ejecute análisis estático y pruebas automáticamente para impedir que código defectuoso alcance la rama principal.

Criterios de aceptación
- CA-1 — Dado un push a cualquier rama, cuando arranca el pipeline, entonces ejecuta en orden flake8, bandit y detect-secrets, y falla la ejecución si alguno reporta hallazgos.
- CA-2 — Dado que el análisis estático pasa, cuando continúa el pipeline, entonces levanta una base de datos efímera y ejecuta la suite con pytest.
- CA-3 — Dado que la cobertura resultante es inferior al 75 %, cuando finaliza la fase de pruebas, entonces el pipeline falla e impide la mezcla del código.
### TEX-05 · Estructura base del repositorio y estándares de desarrollo
Como desarrollador quiero una estructura de proyecto documentada con estándares explícitos para que el código mantenga una organización coherente desde el inicio.

Criterios de aceptación
- CA-1 — Dado el repositorio inicializado, cuando reviso su estructura, entonces existen los módulos gestion, inventory, internal_api, frontend y los tres microservicios, cada uno con su propio conjunto de pruebas.
- CA-2 — Dado un nuevo colaborador, cuando consulta la documentación de estándares, entonces encuentra la convención de nombres de pruebas ISTQB y las reglas de acceso a base de datos.
## EP-01 · Seguridad, RBAC y Auditoría
Sprint 1 (05 Oct – 16 Oct) · Objetivo: Habilitar el acceso seguro y la gestión de roles de la empresa. Entregable: Autenticación y seguridad funcional.
### TEX-06 · Autenticación con JWT en cookies HttpOnly
Como usuario del sistema quiero iniciar sesión de forma segura para que mis credenciales y mi sesión no queden expuestas a robo desde el navegador.

Criterios de aceptación
- CA-1 — Dado un usuario con credenciales válidas, cuando inicia sesión, entonces el sistema emite un JWT almacenado en una cookie marcada HttpOnly, Secure y SameSite, y el token no resulta accesible desde JavaScript.
- CA-2 — Dado una petición con un token expirado, cuando se consulta cualquier endpoint protegido, entonces el sistema responde 401 sin revelar detalle del error.
- CA-3 — Dado una petición sin token, cuando se consulta un endpoint protegido, entonces el sistema responde 401.
- CA-4 — Dado un usuario autenticado, cuando cierra sesión, entonces la cookie se invalida y el token deja de ser aceptado.
Verificación: gestion/tests/test_cookie_jwt_auth.py — técnicas EP, CB-D.
### TEX-07 · Control de acceso basado en roles para los once roles
Como administrador de sistemas quiero que cada rol acceda únicamente a las funciones de su competencia para cumplir la segregación de funciones exigida por la organización.

Criterios de aceptación
- CA-1 — Dado el sistema inicializado, cuando se consultan los grupos de permisos, entonces existen los once roles: Operario, Jefe de Área, Jefe de Planta, Tintorero, Empaquetado, Despacho, Bodeguero, Vendedor, Ejecutivo, Administrador de Sede y Administrador de Sistemas.
- CA-2 — Dado un usuario con rol Operario, cuando intenta acceder a un endpoint de administración, entonces el sistema responde 403.
- CA-3 — Dado cualquier endpoint del sistema, cuando se audita su configuración de permisos, entonces el 100 % exige autenticación y declara explícitamente los roles autorizados, conforme a la métrica de RNF-01.
- CA-4 — Dado la matriz completa de roles contra endpoints, cuando se ejecuta la prueba de autorización, entonces cada combinación rol–operación produce el resultado esperado (permitido o denegado).
Verificación: inventory/tests/test_roles_rbac.py — técnica TD (Tabla de Decisión).
### TEX-08 · Aislamiento multi-sede de la información
Como administrador de sede quiero que cada sede vea solo sus propios datos para evitar fugas de información entre plantas de la organización.

Criterios de aceptación
- CA-1 — Dado un usuario asignado a la sede A, cuando consulta cualquier listado operativo, entonces obtiene exclusivamente registros de la sede A.
- CA-2 — Dado un usuario de la sede A, cuando solicita por identificador un registro de la sede B, entonces el sistema responde 404, sin confirmar la existencia del registro.
- CA-3 — Dado un usuario con rol Administrador de Sistemas, cuando consulta un listado, entonces obtiene los registros de todas las sedes.
Verificación: gestion/tests/test_cliente_sede_filtering.py — técnica EP.
### TEX-09 · Registro de auditoría inmutable en operaciones críticas
Como auditor quiero que toda operación crítica quede registrada de forma inalterable para poder reconstruir qué ocurrió, cuándo y por obra de quién.

Criterios de aceptación
- CA-1 — Dado cualquier operación de creación, modificación o eliminación sobre una entidad auditable, cuando la operación se confirma, entonces se registra usuario, marca de tiempo, dirección IP de origen y valores anterior y posterior.
- CA-2 — Dado un registro de auditoría existente, cuando se intenta modificarlo o eliminarlo, entonces la operación es rechazada.
- CA-3 — Dado una petición que llega con la cabecera X-Forwarded-For manipulada, cuando el sistema extrae la IP de origen, entonces utiliza únicamente la cadena de proxies de confianza, descartando el valor suplantado.
Verificación: gestion/tests/test_audit_middleware.py — técnicas EP, BVA, CB-D.
### TEX-10 · Justificación obligatoria en modificación de datos maestros
Como auditor quiero que toda modificación de un dato maestro exija una justificación escrita para que el historial explique el porqué de cada cambio.

Criterios de aceptación
- CA-1 — Dado un cliente existente, cuando se actualiza sin adjuntar justificación, entonces el sistema rechaza la operación con error de validación.
- CA-2 — Dado la creación de un cliente nuevo, cuando se envía sin justificación, entonces la operación se acepta, pues la exigencia aplica solo a modificaciones.
- CA-3 — Dado una justificación de menos de 10 caracteres, cuando se envía la modificación, entonces el sistema la rechaza por longitud insuficiente.
Verificación: gestion/tests/test_cliente_auditoria_justificacion.py — técnica CB-D.
## EP-02 · Producción y Órdenes de Producción
Sprint 2 (19 Oct – 30 Oct) · Objetivo: Digitalizar el registro en planta y el control de Órdenes de Producción. Entregable: Módulo de Producción operativo.
### TEX-11 · Creación de Órdenes de Producción
Como Jefe de Planta quiero crear órdenes de producción indicando producto, fórmula de color y meta de producción para planificar la carga de la planta.

Criterios de aceptación
- CA-1 — Dado mi rol de Jefe de Planta, cuando creo una orden indicando producto, fórmula de color, peso neto requerido y área responsable, entonces la orden se registra en estado `Pendiente`.
- CA-2 — Dado una orden sin producto o sin meta de producción, cuando intento guardarla, entonces el sistema la rechaza indicando los campos faltantes.
- CA-3 — Dado mi rol de Operario, cuando intento crear una orden de producción, entonces el sistema responde 403.
- CA-4 — Dado una orden creada con fórmula y bodega de químicos asociadas, cuando se confirma la creación, entonces el sistema ejecuta la descarga automática de químicos correspondiente.
Verificación: gestion/tests/test_production_views.py, test_descarga_quimicos_tdd.py — técnicas TD, EP, CB-D.
### TEX-12 · Registro de lote de producción en un solo paso
Como Operario quiero registrar la producción de un lote con un solo clic para no interrumpir la operación de la máquina.

Criterios de aceptación
- CA-1 — Dado una orden asignada a mi usuario en estado `En Proceso`, cuando registro peso, turno y horas y confirmo, entonces el sistema crea el lote con código trazable autogenerado y actualiza el inventario dentro de la misma transacción atómica.
- CA-2 — Dado una orden sin máquina u operario asignado, cuando intento registrar un lote, entonces el sistema rechaza la operación, conforme a la regla de RF-01.
- CA-3 — Dado que el registro alcanza o supera la meta de la orden, cuando se confirma el lote, entonces el sistema sugiere el cambio de estado a `Finalizada`.
- CA-4 — Dado un fallo al actualizar el inventario, cuando se procesa el registro, entonces se revierte la transacción completa y no queda ningún lote huérfano.
- CA-5 — Dado el flujo completo de registro, cuando se cuenta la interacción del operario, entonces no supera los tres pasos, conforme a la métrica de RNF-05.
Verificación: gestion/tests/test_registro_lote_*.py — técnicas EP, BVA, STT.
### TEX-13 · Asignación de máquina y operario a una orden
Como Jefe de Área quiero asignar una máquina y un operario a cada orden para habilitarla para producción y distribuir la carga de mi área.

Criterios de aceptación
- CA-1 — Dado una orden en estado `Pendiente` de mi área, cuando le asigno máquina y operario, entonces la orden transita automáticamente a `En Proceso`.
- CA-2 — Dado una orden perteneciente a otra área, cuando intento asignarle recursos, entonces el sistema responde 403.
- CA-3 — Dado una máquina en estado de mantenimiento, cuando intento asignarla, entonces el sistema rechaza la asignación.
Verificación: gestion/tests/test_production_views.py — técnicas TD, STT.
### TEX-14 · Máquina de estados del ciclo de vida de la orden
Como Jefe de Planta quiero que las órdenes solo transiten entre estados válidos para que el avance reportado refleje la realidad de la planta.

Criterios de aceptación
- CA-1 — Dado una orden en estado `Pendiente`, cuando se le asignan recursos, entonces transita a `En Proceso`.
- CA-2 — Dado una orden en estado `Pendiente`, cuando se intenta finalizarla directamente, entonces el sistema rechaza la transición por inválida.
- CA-3 — Dado una orden en estado `Finalizada`, cuando se intenta registrar un lote sobre ella, entonces el sistema rechaza la operación.
- CA-4 — Dado una orden en curso, cuando se pausa y luego se reanuda, entonces conserva el avance acumulado previamente.
Verificación: gestion/tests/test_production_views.py — técnica STT (Transición de Estados).
### TEX-15 · Gestión de maquinaria del área
Como Jefe de Área quiero administrar las máquinas de mi área y su estado para reflejar su disponibilidad real al planificar.

Criterios de aceptación
- CA-1 — Dado mi rol de Jefe de Área, cuando creo o edito una máquina, entonces queda registrada en mi área con estado Operativa, Mantenimiento o Inactiva.
- CA-2 — Dado el panel de control de área, cuando lo consulto, entonces muestra la carga de trabajo actual de cada máquina frente a su capacidad máxima.
Verificación: gestion/tests/test_production_views.py — técnicas EP, TD.
### TEX-16 · Rechazo de lote con reversión de inventario
Como Jefe de Área quiero rechazar un lote defectuoso para que el inventario no contabilice producto que no cumple calidad.

Criterios de aceptación
- CA-1 — Dado un lote producido en mi área, cuando lo rechazo indicando motivo, entonces el sistema revierte todos los movimientos de inventario asociados, conforme a la regla de RF-01.
- CA-2 — Dado un lote ya despachado, cuando intento rechazarlo, entonces el sistema impide la operación.
- CA-3 — Dado un rechazo confirmado, cuando consulto la auditoría, entonces encuentro el registro con usuario, motivo y marca de tiempo.
Verificación: gestion/tests/test_production_views.py — técnicas STT, CB-D.
### TEX-17 · Monitoreo del avance de planta
Como Jefe de Planta quiero ver el avance global de las órdenes con su detalle para detectar desviaciones sin recorrer la planta.

Criterios de aceptación
- CA-1 — Dado el panel de Jefe de Planta, cuando lo abro, entonces muestra todas las órdenes de mi sede con su estado y barra de progreso.
- CA-2 — Dado el listado de órdenes, cuando selecciono una fila, entonces se abre un panel lateral con producto, fórmula, sede, área responsable, fechas y almacenes.
- CA-3 — Dado una consulta del panel con la sede completa cargada, cuando se mide el tiempo de respuesta, entonces es inferior a 3 segundos, conforme a la métrica de RNF-03.
Verificación: gestion/tests/test_produccion_kpi_service.py — técnica EP.
## EP-03 · Kárdex de Inventario
Sprint 3 (02 Nov – 13 Nov) · Objetivo: Sustituir los registros manuales de bodega por un Kárdex digital auditable. Entregable: Módulo de inventario base funcional.
### TEX-18 · Kárdex transaccional con saldo en tiempo real
Como Bodeguero quiero que cada movimiento actualice el saldo al instante para que el inventario del sistema coincida con la bodega física.

Criterios de aceptación
- CA-1 — Dado un producto con saldo conocido, cuando registro una entrada, entonces el saldo se incrementa en la cantidad exacta dentro de la misma transacción.
- CA-2 — Dado un producto con saldo conocido, cuando registro una salida, entonces el saldo se decrementa y queda asentado el saldo resultante en el kárdex.
- CA-3 — Dado dos movimientos simultáneos sobre el mismo producto, cuando se procesan concurrentemente, entonces el bloqueo a nivel de fila impide condiciones de carrera y el saldo final es consistente.
- CA-4 — Dado un producto de tipo tela, cuando registro una cantidad en metros, entonces se almacena con precisión decimal de cuatro posiciones sin pérdida por redondeo.
Verificación: inventory/tests/test_views_endpoints.py — técnicas EP, BVA, CB-D.
### TEX-19 · Entrada de materia prima con trazabilidad de lote
Como Bodeguero quiero registrar la recepción de materia prima identificando su lote de origen para poder rastrear el material hasta el producto terminado.

Criterios de aceptación
- CA-1 — Dado una recepción de proveedor, cuando registro producto, cantidad, bodega y documento de referencia, entonces se crea el lote de materia prima con su saldo disponible.
- CA-2 — Dado un lote de materia prima consumido en producción, cuando consulto su trazabilidad, entonces obtengo las órdenes de producción que lo consumieron.
- CA-3 — Dado una entrada sin documento de referencia, cuando intento guardarla, entonces el sistema la rechaza.
Verificación: gestion/tests/test_materia_prima_f0_001.py — técnicas EP, BVA, STT.
### TEX-20 · Transferencia de existencias entre bodegas
Como Bodeguero quiero transferir producto entre bodegas para reubicar existencias sin alterar el inventario total.

Criterios de aceptación
- CA-1 — Dado stock suficiente en la bodega de origen, cuando transfiero una cantidad a la bodega de destino, entonces el origen se decrementa y el destino se incrementa en la misma transacción, y el inventario total permanece invariable.
- CA-2 — Dado una cantidad superior al saldo de origen, cuando intento transferir, entonces el sistema rechaza la operación.
- CA-3 — Dado una transferencia con bodega de origen igual a la de destino, cuando intento guardarla, entonces el sistema la rechaza por inválida.
- CA-4 — Dado una transferencia de cantidad cero o negativa, cuando se envía, entonces el serializador la rechaza.
Verificación: inventory/tests/test_serializers.py, test_views_endpoints.py — técnicas BVA, EP.
### TEX-21 · Edición auditada de movimientos de inventario
Como Bodeguero quiero corregir un movimiento mal registrado dejando constancia para que el ajuste sea rastreable y no una alteración silenciosa.

Criterios de aceptación
- CA-1 — Dado un movimiento existente, cuando lo edito aportando una razón de al menos 10 caracteres, entonces el sistema recalcula el saldo y registra el cambio en la auditoría.
- CA-2 — Dado una edición sin razón o con razón menor a 10 caracteres, cuando la envío, entonces el sistema la rechaza.
- CA-3 — Dado una edición que dejaría el saldo en negativo, cuando la confirmo, entonces el sistema la rechaza, conforme a la regla de RF-02.
Verificación: inventory/tests/test_movimiento_views.py — técnicas EP, BVA, CB-D.
### TEX-22 · Consulta y exportación del kárdex
Como Bodeguero quiero consultar el histórico de movimientos de un producto y exportarlo para conciliar con los registros físicos de bodega.

Criterios de aceptación
- CA-1 — Dado un producto con movimientos, cuando consulto su kárdex filtrando por rango de fechas, entonces obtengo los movimientos en orden cronológico con el saldo resultante de cada uno.
- CA-2 — Dado un kárdex en pantalla, cuando solicito la exportación, entonces recibo un archivo descargable con las mismas filas mostradas.
- CA-3 — Dado una consulta de kárdex, cuando se mide el tiempo de respuesta, entonces es inferior a 3 segundos, conforme a RNF-03.
Verificación: inventory/tests/test_views_endpoints.py — técnicas EP, CB-D.
### TEX-23 · Filtrado de bodegas por rol y sede
Como administrador de sistemas quiero que cada usuario vea solo las bodegas que le competen para mantener la segregación de funciones en el inventario.

Criterios de aceptación
- CA-1 — Dado un usuario de una sede, cuando lista bodegas, entonces obtiene únicamente las de su sede.
- CA-2 — Dado un rol sin permiso de escritura en inventario, cuando intenta crear o modificar una bodega, entonces el sistema responde 403.
Verificación: gestion/tests/test_inventory_views.py — técnicas TD, EP, CB-D.
## EP-04 · Transformación y MRP
Sprint 4 (16 Nov – 27 Nov) · Objetivo: Conectar la producción con el inventario y sugerir compras de materiales. Entregable: Módulo de inventario y MRP completo.
### TEX-24 · Transformación de productos con cálculo de merma
Como Jefe de Área quiero registrar la transformación de un producto en otro indicando pesos de entrada y salida para que la merma quede cuantificada por etapa.

Criterios de aceptación
- CA-1 — Dado una orden en curso en mi área, cuando registro una transformación con producto de salida, máquina, peso de entrada y peso de salida, entonces el sistema calcula la merma automáticamente como diferencia entre ambos pesos.
- CA-2 — Dado una cadena de transformaciones, cuando registro una nueva etapa, entonces el sistema exige que el producto de entrada coincida con el producto de salida de la etapa anterior.
- CA-3 — Dado un peso de salida mayor al de entrada, cuando intento registrarlo, entonces el sistema rechaza la operación por merma negativa.
- CA-4 — Dado una orden de otra área o sede, cuando intento registrar una transformación sobre ella, entonces el sistema responde 403.
Verificación: gestion/tests/test_production_views.py — técnicas BVA, TD, CB-D.
### TEX-25 · Bloqueo de saldos negativos de inventario
Como Bodeguero quiero que el sistema impida dejar cualquier saldo en negativo para garantizar que el inventario digital sea siempre físicamente posible.

Criterios de aceptación
- CA-1 — Dado un producto con saldo de 100 unidades, cuando intento una salida de 101, entonces el sistema rechaza la operación, conforme a la regla de RF-02.
- CA-2 — Dado un producto con saldo de 100 unidades, cuando registro una salida de exactamente 100, entonces la operación se acepta y el saldo queda en cero.
- CA-3 — Dado un consumo de producción que excede el stock disponible, cuando se procesa, entonces la transacción completa se revierte sin consumo parcial.
Verificación: gestion/tests/test_descarga_quimicos_stock_p0.py, test_consumo_mezcla_service.py — técnicas BVA, EP.
### TEX-26 · Alertas de stock bajo
Como Bodeguero quiero recibir aviso cuando un insumo cae bajo su mínimo para reponerlo antes de que detenga la producción.

Criterios de aceptación
- CA-1 — Dado un producto con stock mínimo configurado, cuando su saldo cae por debajo de ese umbral, entonces aparece en el panel de alertas de stock bajo.
- CA-2 — Dado un producto exactamente en su stock mínimo, cuando se evalúan las alertas, entonces no se genera alerta, pues la condición es estrictamente menor.
- CA-3 — Dado un Jefe de Área, cuando consulta sus alertas, entonces ve únicamente los insumos críticos de su propia área.
Verificación: inventory/tests/test_views_endpoints.py — técnicas BVA, EP.
### TEX-27 · Motor MRP de cálculo de requerimientos
Como Bodeguero quiero conocer qué materiales faltan para cubrir las órdenes abiertas para anticipar las compras necesarias.

Criterios de aceptación
- CA-1 — Dado un conjunto de órdenes de producción abiertas, cuando ejecuto el cálculo MRP, entonces el sistema explosiona los materiales requeridos por sus fórmulas y los contrasta con el stock disponible.
- CA-2 — Dado un material cuyo requerimiento excede el stock, cuando se genera el resultado, entonces aparece una sugerencia de compra por la cantidad faltante.
- CA-3 — Dado un material con stock suficiente, cuando se genera el resultado, entonces no produce sugerencia de compra.
- CA-4 — Dado el mismo cálculo ejecutado por un Bodeguero y por un Ejecutivo, cuando se comparan los resultados, entonces son idénticos, por compartir ambos el mismo motor.
Verificación: inventory/tests/test_mrp.py — técnica EP.
### TEX-28 · Consulta de requisitos de materiales de una orden
Como Jefe de Planta quiero ver los materiales que consumirá una orden antes de iniciarla para confirmar que la planta puede ejecutarla.

Criterios de aceptación
- CA-1 — Dado una orden con fórmula asociada, cuando consulto sus requisitos de materiales, entonces obtengo el listado de hilos base y químicos con la cantidad necesaria.
- CA-2 — Dado un material con stock insuficiente para la orden, cuando consulto los requisitos, entonces aparece señalizado como faltante.
Verificación: gestion/tests/test_production_views.py — técnicas EP, CB-D.
### TEX-29 · Registro de merma vendible
Como Bodeguero quiero que la merma aprovechable ingrese al inventario como producto vendible para no perder el valor del subproducto.

Criterios de aceptación
- CA-1 — Dado una merma clasificada como vendible, cuando se registra, entonces ingresa al inventario como producto disponible para venta.
- CA-2 — Dado una merma clasificada como no aprovechable, cuando se registra, entonces se contabiliza como pérdida sin afectar el stock vendible.
Verificación: gestion/tests/test_merma_stock_service.py — técnica EP.
## EP-05 · Comercial y Control de Crédito
Sprint 5 (30 Nov – 11 Dic) · Objetivo: Automatizar el ciclo de ventas, validación de créditos y pagos. Entregable: Módulo Comercial funcional.
### TEX-30 · Directorio de clientes con aislamiento de cartera
Como Vendedor quiero gestionar mis clientes asignados para trabajar mi cartera sin exponer la de mis compañeros.

Criterios de aceptación
- CA-1 — Dado mi rol de Vendedor, cuando consulto el directorio de clientes, entonces obtengo únicamente los clientes asignados a mi cartera, conforme a la regla de RF-03.
- CA-2 — Dado un cliente de la cartera de otro vendedor, cuando solicito su ficha por identificador, entonces el sistema responde 404.
- CA-3 — Dado mi rol de Administrador de Sede, cuando consulto el directorio, entonces obtengo todos los clientes de mi sede.
Verificación: gestion/tests/test_cliente_sede_filtering.py — técnica EP.
### TEX-31 · Registro de pedidos de venta
Como Vendedor quiero registrar pedidos indicando productos y condiciones para formalizar la venta en el sistema.

Criterios de aceptación
- CA-1 — Dado un cliente de mi cartera, cuando registro un pedido con productos, cantidades y condiciones de pago, entonces se crea el pedido y se genera el comprobante de venta.
- CA-2 — Dado un pedido sin líneas de detalle, cuando intento guardarlo, entonces el sistema lo rechaza.
- CA-3 — Dado un pedido confirmado, cuando consulto el estado de cuenta del cliente, entonces refleja el nuevo saldo pendiente.
Verificación: gestion/tests/test_catalog_views.py — técnicas EP, TD.
### TEX-32 · Validación automática de límite de crédito
Como gerente comercial quiero que el sistema bloquee pedidos que excedan el cupo del cliente para contener la exposición al riesgo de impago.

Criterios de aceptación
- CA-1 — Dado un cliente con cupo disponible suficiente, cuando se registra el pedido, entonces la validación lo aprueba y el pedido se confirma.
- CA-2 — Dado un cliente cuyo saldo más el pedido excede su límite de crédito, cuando se intenta confirmar, entonces el sistema bloquea el pedido indicando el cupo disponible.
- CA-3 — Dado un pedido que deja el saldo exactamente en el límite, cuando se confirma, entonces la operación se acepta, pues la condición de bloqueo es estrictamente mayor.
- CA-4 — Dado un cliente sin límite de crédito configurado, cuando registra un pedido, entonces se aplica la política por defecto definida para la sede.
Verificación: gestion/tests/test_catalog_views.py — técnicas BVA, TD.
### TEX-33 · Validación de precio mínimo de venta
Como gerente comercial quiero impedir que se venda por debajo del precio base para proteger el margen de la operación.

Criterios de aceptación
- CA-1 — Dado una línea de pedido con precio inferior al precio base del producto, cuando intento guardarla, entonces el sistema la rechaza, conforme a la regla de RF-03.
- CA-2 — Dado una línea con precio exactamente igual al precio base, cuando la guardo, entonces la operación se acepta.
Verificación: gestion/tests/test_serializers.py — técnica BVA.
### TEX-34 · Reconciliación de pagos con criterio FIFO
Como Vendedor quiero que los cobros se apliquen primero a las facturas más antiguas para que la antigüedad de cartera refleje la realidad.

Criterios de aceptación
- CA-1 — Dado un cliente con varias facturas pendientes, cuando registro un pago, entonces se aplica a las facturas en orden cronológico, de la más antigua a la más reciente.
- CA-2 — Dado un pago que cubre parcialmente una factura, cuando se aplica, entonces la factura queda con saldo parcial y las posteriores intactas.
- CA-3 — Dado un pago superior al total adeudado, cuando se aplica, entonces el excedente queda registrado como saldo a favor del cliente.
Verificación: gestion/tests/test_pago_reversion.py — técnica STT.
### TEX-35 · Reversión auditada de pagos
Como Administrador de Sede quiero revertir un pago mal registrado para corregir la cartera dejando rastro del ajuste.

Criterios de aceptación
- CA-1 — Dado un pago aplicado a varias facturas, cuando lo revierto, entonces todas las facturas afectadas recuperan su saldo anterior en una única transacción.
- CA-2 — Dado una reversión confirmada, cuando consulto la auditoría, entonces encuentro el registro con usuario, motivo y marca de tiempo.
- CA-3 — Dado un pago ya revertido, cuando intento revertirlo de nuevo, entonces el sistema impide la operación.
Verificación: gestion/tests/test_pago_reversion.py — técnica STT.
### TEX-36 · Estado de cuenta del cliente
Como Vendedor quiero consultar el estado de cuenta de un cliente para gestionar la cobranza con información fiable.

Criterios de aceptación
- CA-1 — Dado un cliente de mi cartera, cuando consulto su estado de cuenta, entonces obtengo facturas pendientes, pagos aplicados, saldo total y cupo disponible.
- CA-2 — Dado un pago recién registrado, cuando vuelvo a consultar el estado de cuenta, entonces refleja el saldo actualizado sin necesidad de recalcular manualmente.
Verificación: gestion/tests/test_catalog_views.py — técnica EP.
## EP-06 · Tintorería y Empaquetado
Sprint 6 (14 Dic – 25 Dic) · Objetivo: Estandarizar las recetas de tintorería y emitir etiquetas de empaque. Entregable: Módulos de Tintorería y Empaquetado funcionales.
### TEX-37 · Recetas de tintorería por fases
Como Tintorero quiero definir recetas organizadas en fases con sus insumos para estandarizar el proceso de teñido entre turnos.

Criterios de aceptación
- CA-1 — Dado mi rol de Tintorero, cuando creo una fórmula con sus fases y el detalle de químicos de cada una, entonces se guarda de forma atómica con todos sus detalles anidados.
- CA-2 — Dado una fórmula existente, cuando la duplico, entonces la copia incluye todas las fases y todos los insumos de la original.
- CA-3 — Dado mi rol de Operario, cuando intento crear una fórmula, entonces el sistema responde 403.
- CA-4 — Dado un listado de fórmulas, cuando filtro por estado, entonces obtengo únicamente las que se encuentran en ese estado.
Verificación: gestion/tests/test_formula_views.py — técnicas EP, TD, CB-D.
### TEX-38 · Versionamiento de fórmulas de color
Como Tintorero quiero que las modificaciones generen una nueva versión para poder reproducir un color exactamente como se hizo en el pasado.

Criterios de aceptación
- CA-1 — Dado una fórmula ya utilizada en producción, cuando la modifico, entonces el sistema crea una nueva versión y conserva la anterior intacta.
- CA-2 — Dado una orden de producción histórica, cuando consulto su fórmula, entonces obtengo la versión vigente en el momento de su ejecución, no la actual.
Verificación: gestion/tests/test_formula_views.py — técnicas EP, STT.
### TEX-39 · Calculadora de dosificación asociada a la orden
Como Tintorero quiero que el sistema calcule los gramos exactos de cada químico según el peso del baño para eliminar los errores de cálculo manual.

Criterios de aceptación
- CA-1 — Dado una fórmula con insumos expresados en gramos por litro, cuando indico el volumen del baño, entonces el sistema calcula la cantidad exacta de cada químico.
- CA-2 — Dado una fórmula con insumos expresados en porcentaje sobre peso, cuando indico el peso del material, entonces el sistema aplica la fórmula porcentual correspondiente.
- CA-3 — Dado un insumo con unidad no reconocida, cuando se calcula la dosificación, entonces el sistema aplica el comportamiento de respaldo definido sin interrumpir el cálculo del resto.
- CA-4 — Dado una dosificación menor o igual a cero, cuando se intenta registrar, entonces el serializador la rechaza.
Verificación: gestion/tests/test_services_formula.py — técnicas EP, BVA, CB-D.
### TEX-40 · Descarga automática de químicos al inventario
Como Bodeguero quiero que el consumo de químicos de una orden se descuente solo para no registrar manualmente cada dosificación.

Criterios de aceptación
- CA-1 — Dado una orden con fórmula y bodega de químicos configuradas, cuando se crea la orden, entonces el sistema descarga del inventario los químicos calculados.
- CA-2 — Dado una orden sin bodega de químicos configurada, cuando se crea, entonces el sistema informa la falta de configuración sin ejecutar descarga parcial.
- CA-3 — Dado stock insuficiente de un químico, cuando se intenta la descarga, entonces la transacción completa se revierte.
- CA-4 — Dado una descarga ejecutada, cuando consulto la auditoría, entonces encuentro el rastro completo de la operación.
Verificación: gestion/tests/test_descarga_quimicos_validaciones.py, test_descarga_quimicos_stock_p0.py — técnicas EP, BVA, CB-D, STT.
### TEX-41 · Registro de pesaje en estación de empaquetado
Como personal de Empaquetado quiero registrar el pesaje del bulto descontando la tara para que el peso neto declarado sea exacto.

Criterios de aceptación
- CA-1 — Dado un lote a empacar, cuando registro el peso bruto y la tara del empaque, entonces el sistema calcula y almacena el peso neto.
- CA-2 — Dado una tara mayor o igual al peso bruto, cuando intento registrarla, entonces el sistema rechaza la operación.
- CA-3 — Dado el flujo completo de pesaje, cuando se cuentan las interacciones, entonces no supera los tres pasos, conforme a RNF-05.
Verificación: gestion/tests/test_configuracion_empaque_sede.py — técnicas EP, BVA.
### TEX-42 · Emisión de etiqueta ZPL para impresoras Zebra
Como personal de Empaquetado quiero imprimir la etiqueta del bulto con su código para que el lote sea identificable y escaneable en bodega.

Criterios de aceptación
- CA-1 — Dado un bulto pesado, cuando solicito su etiqueta, entonces el microservicio genera código ZPL con el código del lote, producto, peso neto y código de barras o QR.
- CA-2 — Dado la petición de impresión, cuando llega al microservicio, entonces se autentica mediante JWT de servicio interno y rechaza peticiones sin token.
- CA-3 — Dado que la impresora no responde, cuando se solicita la impresión, entonces el sistema informa el fallo sin perder el registro del bulto.
Verificación: printing_service/tests, gestion/tests/test_production_views.py — técnicas EP, CB-D.
### TEX-43 · Equivalencias de empaque configurables por sede
Como Administrador de Sede quiero configurar las equivalencias de empaque de mi sede para que las conversiones respondan a la realidad de cada planta.

Criterios de aceptación
- CA-1 — Dado mi sede, cuando configuro la equivalencia de hilos (baño, fundas, conos), entonces el sistema la aplica solo a las conversiones de mi sede.
- CA-2 — Dado dos sedes con equivalencias distintas, cuando cada una realiza una conversión, entonces cada resultado emplea su propia configuración sin interferencia.
- CA-3 — Dado una sede sin configuración propia, cuando se realiza una conversión, entonces el sistema informa la ausencia de configuración en lugar de aplicar una constante del sistema.
Verificación: gestion/tests/test_configuracion_empaque_sede.py — técnicas EP, CB-D.
## EP-07 · Despacho y Dashboard Ejecutivo
Sprint 7 (04 Ene – 15 Ene) · Objetivo: Asegurar despachos con escáner y proveer tableros de control a gerencia. Entregable: Módulo de Despacho y panel ejecutivo funcionales.
### TEX-44 · Microservicio de escaneo de códigos QR y de barras
Como personal de Despacho quiero validar cada lote escaneando su código para confirmar en segundos que corresponde al pedido correcto.

Criterios de aceptación
- CA-1 — Dado un lote perteneciente al pedido en curso, cuando escaneo su código QR o de barras, entonces el sistema lo valida como correcto.
- CA-2 — Dado un lote que no pertenece al pedido del cliente, cuando lo escaneo, entonces el sistema lo rechaza indicando la discrepancia.
- CA-3 — Dado cualquier escaneo, cuando se mide el tiempo entre la lectura y la respuesta, entonces es inferior a 2500 ms, conforme a la métrica de RNF-03.
- CA-4 — Dado un código ilegible o inexistente, cuando se envía a validación, entonces el sistema responde con error controlado sin interrumpir la sesión.
Verificación: scanning_service/tests — técnicas EP, BVA, CB-D.
### TEX-45 · Despacho atómico con descarga de inventario
Como personal de Despacho quiero que el despacho se confirme por completo o no se confirme en absoluto para que nunca queden descargas parciales de inventario.

Criterios de aceptación
- CA-1 — Dado todos los lotes del pedido validados por escaneo, cuando confirmo el despacho, entonces el sistema descarga el inventario y genera la nota de despacho en una única transacción.
- CA-2 — Dado un pedido con algún lote sin escanear, cuando intento confirmar el despacho, entonces el sistema lo impide, conforme a la regla de RF-04.
- CA-3 — Dado un fallo en cualquier etapa (validación, descarga o generación de documentos), cuando ocurre, entonces toda la operación se revierte, sin descargas parciales ni notas incompletas.
- CA-4 — Dado un despacho confirmado por error, cuando se revierte, entonces el inventario y el estado del pedido recuperan su situación previa en cascada.
Verificación: inventory/tests/test_despacho_reversion.py — técnicas STT, CB-D.
### TEX-46 · Panel ejecutivo de indicadores
Como Ejecutivo quiero un tablero consolidado de producción, inventario y ventas para decidir sin depender de reportes manuales.

Criterios de aceptación
- CA-1 — Dado mi rol de Ejecutivo, cuando abro el panel, entonces obtengo indicadores financieros, productivos y de inventario con sus gráficos.
- CA-2 — Dado una operación registrada en planta, cuando recargo el panel, entonces los indicadores reflejan el dato actualizado, conforme a la regla de RF-05.
- CA-3 — Dado un usuario sin rol ejecutivo, cuando intenta acceder al panel, entonces el sistema responde 403.
- CA-4 — Dado el panel abierto en una resolución de escritorio, cuando se evalúa su presentación, entonces es responsivo y legible, conforme a la regla de RF-05.
Verificación: gestion/tests/test_kpi_views.py, inventory/tests/test_executive_kpi_service.py — técnicas TD, EP, CB-D.
### TEX-47 · Microservicio de reportes en Excel
Como Ejecutivo quiero exportar los reportes a Excel para analizarlos y compartirlos fuera del sistema.

Criterios de aceptación
- CA-1 — Dado un reporte en pantalla, cuando solicito la exportación, entonces el microservicio genera un archivo Excel descargable con los mismos datos.
- CA-2 — Dado la petición de exportación, cuando llega al microservicio, entonces se autentica por JWT de servicio interno.
- CA-3 — Dado que el microservicio no está disponible, cuando se solicita una exportación, entonces el sistema informa el fallo sin afectar el resto del panel.
Verificación: reporting_excel/tests — técnicas EP, CB-D.
### TEX-48 · Drill-down sobre los indicadores
Como Ejecutivo quiero abrir el detalle tras un indicador para entender qué compone la cifra antes de decidir.

Criterios de aceptación
- CA-1 — Dado un indicador del panel, cuando lo selecciono, entonces se abre el detalle de los registros que lo componen.
- CA-2 — Dado el detalle abierto, cuando filtro por sede, período o área, entonces la cifra se recalcula de forma consistente con el filtro aplicado.
Verificación: gestion/tests/test_kpi_views.py — técnicas EP, TD.
## EP-08 · Administración y Code Freeze
Sprint 8 (18 Ene – 29 Ene) · Objetivo: Permitir la autoadministración de catálogos y congelar el sistema para preproducción. Entregable: Sistema completo en staging, listo para validación.
### TEX-49 · Panel de Administrador de Sistemas
Como Administrador de Sistemas quiero administrar usuarios, sedes y áreas para operar el sistema sin depender del equipo de desarrollo.

Criterios de aceptación
- CA-1 — Dado mi rol de Administrador de Sistemas, cuando accedo al panel, entonces puedo crear, editar y desactivar usuarios asignándoles rol y sede.
- CA-2 — Dado el arranque inicial del sistema, cuando ejecuto la siembra de datos maestros, entonces se crean los grupos de permisos y la cuenta administradora, sin precrear sedes ni áreas ficticias.
- CA-3 — Dado mi rol de Administrador de Sistemas, cuando creo una sede y sus áreas, entonces quedan disponibles para asignación de usuarios.
Verificación: gestion/tests/test_catalog_views.py — técnicas TD, EP.
### TEX-50 · Panel de Administrador de Sede
Como Administrador de Sede quiero gestionar los usuarios y catálogos de mi sede para mantener mis datos maestros sin alcance sobre otras plantas.

Criterios de aceptación
- CA-1 — Dado mi rol de Administrador de Sede, cuando gestiono usuarios, entonces solo puedo actuar sobre los de mi propia sede.
- CA-2 — Dado un intento de acceder a datos de otra sede, cuando se procesa la petición, entonces el sistema responde 403 o 404 según corresponda.
Verificación: inventory/tests/test_roles_rbac.py — técnica TD.
### TEX-51 · Gestión de catálogos maestros
Como Administrador de Sede quiero mantener los catálogos de productos, químicos y proveedores para que la operación disponga de datos actualizados.

Criterios de aceptación
- CA-1 — Dado el catálogo de productos, cuando creo o edito un registro, entonces se guarda con su tipo, unidad de medida y precio base.
- CA-2 — Dado un nombre con acentos o caracteres alfanuméricos válidos, cuando lo registro, entonces el sistema lo acepta.
- CA-3 — Dado mi rol de Vendedor, cuando consulto el catálogo, entonces obtengo la vista restringida que me corresponde.
Verificación: gestion/tests/test_catalog_views.py, test_serializers.py — técnicas EP, TD, BVA.
### TEX-52 · Consulta del registro de auditoría
Como Administrador de Sede quiero consultar el histórico de auditoría para investigar cualquier operación registrada.

Criterios de aceptación
- CA-1 — Dado el panel de auditoría, cuando filtro por usuario, fecha o tipo de operación, entonces obtengo los registros coincidentes con su detalle completo.
- CA-2 — Dado mi rol de Administrador de Sede, cuando consulto la auditoría, entonces obtengo únicamente los registros de mi sede.
Verificación: gestion/tests/test_audit_middleware.py — técnicas EP, CB-D.
### TEX-53 · Persistencia del estado de navegación en la URL
Como usuario del sistema quiero que la vista en que estoy quede reflejada en la dirección para recargar o compartir sin perder el contexto.

Criterios de aceptación
- CA-1 — Dado una vista con filtros aplicados, cuando recargo la página, entonces se restauran la pestaña activa y los filtros.
- CA-2 — Dado una vista concreta, cuando comparto su dirección con otro usuario autorizado, entonces accede directamente a esa misma vista.
Verificación: frontend/src/components/**/*.test.tsx — técnica EP.
### TEX-54 · Congelamiento de código y despliegue en staging
Como responsable del proyecto quiero congelar el código y validarlo en staging para iniciar la fase de preproducción sobre una base estable.

Criterios de aceptación
- CA-1 — Dado el cierre del Sprint 8, cuando se aplica el congelamiento, entonces solo se admiten correcciones de defectos, sin nuevas funcionalidades.
- CA-2 — Dado el código congelado, cuando se despliega en staging, entonces el sistema completo opera con la suite en verde y la cobertura sobre el umbral exigido.
- CA-3 — Dado un despliegue con incidencias, cuando se decide revertir, entonces la reversión a la versión anterior se ejecuta en un solo paso.
Verificación: Pipeline de CI/CD y scripts/run_backend_tests.sh.
# 7. Resumen de distribución

# 8. Matriz de trazabilidad requisito ↔ historia

Los cinco requisitos funcionales y los cinco no funcionales quedan cubiertos por al menos una historia, sin elementos del backlog huérfanos de requisito.
# 9. Referencias
- Documento Capstone, §5.1 Metodología de Desarrollo y Planificación Ágil
- Documento Capstone, §5.2 y Tabla 14 Product Backlog y Plan de Releases
- docs/matriz_trazabilidad_pruebas.md — correspondencia requisito ↔ caso de prueba
- docs/historias-usuarios/ROLES_Y_PERMISOS.md — definición de los once roles
- ISTQB CTFL v4.0 — técnicas de diseño de pruebas aplicadas en la verificación

# Planificación de Sprints — TexCore
Proyecto: TexCore — Sistema de digitalización y seguimiento de Órdenes de Producción Organización: Interfibra S.A. Autor: Brandon Arellano Marco de trabajo: Scrum Fuente normativa: Anteproyecto_Capstone_Final_Version.docx, §5.1, §5.2 y Tabla 14 Documento complementario: PRODUCT_BACKLOG.md Fecha de elaboración: 23 de septiembre de 2026
## 1. Marco metodológico
El desarrollo de TexCore se estructura bajo Scrum, de naturaleza iterativa e incremental, combinado con prácticas de DevOps para la Integración y el Despliegue Continuos (CI/CD).
El trabajo se organiza en un Product Backlog priorizado, ejecutado a través de un Sprint 0 de preparación y ocho sprints de desarrollo, cada uno de dos semanas. Cada sprint cuenta con un objetivo definido (Sprint Goal), un conjunto de elementos del backlog seleccionados, un entregable funcional (incremento de producto) y una Definición de Hecho que establece los criterios de calidad para considerar completado el trabajo.
### 1.1 Ceremonias

### 1.2 Equipo y capacidad

## 2. Definición de Hecho transversal
Conforme al §5.1 del documento Capstone, todo incremento de los sprints de desarrollo debe cumplir sin excepción:
1. Código integrado en la rama principal a través del pipeline de CI/CD 2. Superación de los análisis estáticos: flake8, bandit, detect-secrets 3. Cobertura de pruebas automatizadas no inferior al 75 % en el núcleo 4. Registro de auditoría en las operaciones críticas 5. Despliegue verificado en el ambiente de staging
Un incremento que incumpla cualquiera de los cinco puntos no se considera hecho, con independencia de que la funcionalidad opere.
## 3. Calendario de releases

Hitos posteriores al desarrollo (§5.4 del Capstone):

# 4. Sprint Backlogs
## Sprint 0 — Infraestructura y DevOps
Fechas: 21 de septiembre – 02 de octubre de 2026 · Capacidad: 80 h · Comprometido: 21 puntos
### Objetivo del Sprint
Establecer la infraestructura y automatizar los despliegues.
### Sprint Backlog

### Entregable
Entorno de desarrollo operativo y backlog priorizado.
### Definición de Hecho específica
- Los contenedores levantan sin errores
- El pipeline ejecuta build y lint
- El backlog queda estimado y priorizado
Nota: el Sprint 0 es de preparación; la DoD transversal de cobertura del 75 % no le aplica, al no producir todavía código de negocio.
## Sprint 1 — Seguridad, RBAC y Auditoría
Fechas: 05 – 16 de octubre de 2026 · Capacidad: 80 h · Comprometido: 32 puntos
### Objetivo del Sprint
Habilitar el acceso seguro y la gestión de roles de la empresa.
### Sprint Backlog

### Entregable
Autenticación y seguridad funcional.
### Definición de Hecho específica
- Acceso restringido por rol verificado
- Pruebas de acceso no autorizado superadas
- Auditoría activa
### Riesgos del sprint
El aislamiento multi-sede (TEX-08) atraviesa todos los módulos posteriores. Un defecto aquí se propaga a cada consulta del sistema, por lo que la matriz de pruebas de RBAC debe quedar completa antes de cerrar el sprint.
## Sprint 2 — Producción y Órdenes de Producción
Fechas: 19 – 30 de octubre de 2026 · Capacidad: 80 h · Comprometido: 32 puntos
### Objetivo del Sprint
Digitalizar el registro en planta y el control de Órdenes de Producción.
### Sprint Backlog

### Entregable
Módulo de Producción operativo.
### Definición de Hecho específica
- La orden de producción transita correctamente entre estados
- El registro de lote es atómico
- Cobertura ≥ 75 %
### Riesgos del sprint
TEX-12 es la historia de mayor exposición operativa: es la que ejecuta el operario decenas de veces al día. Su criterio de usabilidad (no más de tres pasos, RNF-05) debe validarse con un usuario real antes de la Sprint Review.
## Sprint 3 — Kárdex de Inventario
Fechas: 02 – 13 de noviembre de 2026 · Capacidad: 80 h · Comprometido: 32 puntos
### Objetivo del Sprint
Sustituir los registros manuales de bodega por un Kárdex digital auditable.
### Sprint Backlog

### Entregable
Módulo de inventario base funcional.
### Definición de Hecho específica
- Los movimientos reflejan el saldo correcto
- Cada operación queda auditada
- No existen saldos inconsistentes
### Riesgos del sprint
La concurrencia sobre el saldo (TEX-18, CA-3) exige bloqueo a nivel de fila. Es un riesgo técnico difícil de detectar en pruebas secuenciales: debe probarse explícitamente con operaciones simultáneas.
## Sprint 4 — Transformación y MRP
Fechas: 16 – 27 de noviembre de 2026 · Capacidad: 80 h · Comprometido: 32 puntos
### Objetivo del Sprint
Conectar la producción con el inventario y sugerir compras de materiales.
### Sprint Backlog

### Entregable
Módulo de inventario y MRP completo.
### Definición de Hecho específica
- El MRP genera órdenes de compra sugeridas
- Las alertas son correctas
- Las pruebas de borde quedan superadas
### Riesgos del sprint
TEX-29 (merma vendible) es la única historia Could del proyecto y actúa como amortiguador: si la velocidad cae, se difiere sin comprometer el objetivo del sprint.
## Sprint 5 — Comercial y Control de Crédito
Fechas: 30 de noviembre – 11 de diciembre de 2026 · Capacidad: 80 h · Comprometido: 37 puntos
### Objetivo del Sprint
Automatizar el ciclo de ventas, validación de créditos y pagos.
### Sprint Backlog

### Entregable
Módulo Comercial funcional.
### Definición de Hecho específica
- La validación de crédito bloquea pedidos fuera de cupo
- El criterio FIFO se aplica cronológicamente
- La reversión queda auditada
### Riesgos del sprint
Sprint sobrecargado (37 puntos frente a una velocidad objetivo de 33). TEX-36 es la candidata a diferir. La lógica FIFO con reversión (TEX-34 y TEX-35) es la de mayor densidad de reglas del proyecto y conviene abordarla al inicio del sprint.
## Sprint 6 — Tintorería y Empaquetado
Fechas: 14 – 25 de diciembre de 2026 · Capacidad: 80 h · Comprometido: 37 puntos
### Objetivo del Sprint
Estandarizar las recetas de tintorería y emitir etiquetas de empaque.
### Sprint Backlog

### Entregable
Módulos de Tintorería y Empaquetado funcionales.
### Definición de Hecho específica
- La dosificación calcula gramos exactos
- La etiqueta ZPL se imprime con tara
- Las recetas quedan versionadas
### Riesgos del sprint
Riesgo de calendario: el sprint transcurre del 14 al 25 de diciembre, coincidiendo con el período festivo de Navidad. La capacidad real puede situarse por debajo de las 80 horas nominales. A ello se suma que es uno de los dos sprints sobrecargados (37 puntos) y que TEX-42 depende de hardware externo (impresoras Zebra), cuya disponibilidad para pruebas debe asegurarse antes del inicio del sprint.
Mitigación: diferir TEX-43 al Sprint 7 y adelantar la verificación de conectividad con la impresora al Sprint 5.
## Sprint 7 — Despacho y Dashboard Ejecutivo
Fechas: 04 – 15 de enero de 2027 · Capacidad: 80 h · Comprometido: 34 puntos
### Objetivo del Sprint
Asegurar despachos con escáner y proveer tableros de control a gerencia.
### Sprint Backlog

### Entregable
Módulo de Despacho y panel ejecutivo funcionales.
### Definición de Hecho específica
- El escaneo valida el lote contra el pedido
- El despacho es atómico, sin descargas parciales
- Los KPIs se presentan en tiempo real
### Riesgos del sprint
El requisito de menos de 2500 ms en la validación por escaneo (RNF-03) es el único umbral de rendimiento cuantificado del proyecto. Debe medirse en condiciones realistas de red de planta, no en entorno local, donde el resultado sería optimista.
## Sprint 8 — Administración y Code Freeze
Fechas: 18 – 29 de enero de 2027 · Capacidad: 80 h · Comprometido: 31 puntos
### Objetivo del Sprint
Permitir la autoadministración de catálogos y congelar el sistema para preproducción.
### Sprint Backlog

### Entregable
Sistema completo en staging, listo para validación.
### Definición de Hecho específica
- Los roles administrativos operan según su alcance
- La navegación es persistente
- El congelamiento de código queda aplicado
### Riesgos del sprint
Es el último sprint y absorbe cualquier deuda arrastrada. Se reserva deliberadamente por debajo de la velocidad objetivo (31 puntos frente a 33) para dejar margen a la corrección de defectos detectados en sprints previos.
# 5. Seguimiento y métricas
### 5.1 Métricas por sprint

### 5.2 Gráfico de avance
Se mantiene un burndown por sprint (puntos restantes por día) y un burnup acumulado del proyecto contra los 288 puntos totales.
# 6. Registro de riesgos del plan

# 7. Referencias
- Documento Capstone, §5.1 Metodología de Desarrollo y Planificación Ágil
- Documento Capstone, §5.2 y Tabla 14 Product Backlog y Plan de Releases
- Documento Capstone, §5.4 Plan de Adopción y Puesta en Marcha
- Documento Capstone, §5.5 Estimación de Costos
- PRODUCT_BACKLOG.md — detalle de las 54 historias con criterios de aceptación
- docs/matriz_trazabilidad_pruebas.md — correspondencia requisito ↔ caso de prueba
- Schwaber, K. y Sutherland, J. (2020). The Scrum Guide
- ISTQB CTFL v4.0 — técnicas de diseño de pruebas
| Puntos | Interpretación |
| --- | --- |
| 1 | Cambio trivial, sin lógica de negocio |
| 2 | Funcionalidad simple, un solo componente |
| 3 | Funcionalidad con validaciones, backend + frontend |
| 5 | Funcionalidad con lógica de negocio y transaccionalidad |
| 8 | Funcionalidad compleja, múltiples componentes acoplados |
| 13 | Muy compleja; candidata a descomponerse |
| Nivel | Significado |
| --- | --- |
| Must | Imprescindible. Sin esto el sprint no cumple su objetivo. |
| Should | Importante, pero el sprint entrega valor sin ello. |
| Could | Deseable. Primer candidato a salir si la velocidad baja. |
| Épica | Nombre | Sprint | Requisitos cubiertos | Puntos |
| --- | --- | --- | --- | --- |
| EP-00 | Infraestructura y DevOps | Sprint 0 | RNF-04 | 21 |
| EP-01 | Seguridad, RBAC y Auditoría | Sprint 1 | RNF-01, RNF-02 | 32 |
| EP-02 | Producción y Órdenes de Producción | Sprint 2 | RF-01 | 32 |
| EP-03 | Kárdex de Inventario | Sprint 3 | RF-02 | 32 |
| EP-04 | Transformación y MRP | Sprint 4 | RF-02 | 32 |
| EP-05 | Comercial y Control de Crédito | Sprint 5 | RF-03 | 37 |
| EP-06 | Tintorería y Empaquetado | Sprint 6 | RF-01, RNF-05 | 37 |
| EP-07 | Despacho y Dashboard Ejecutivo | Sprint 7 | RF-04, RF-05, RNF-03 | 34 |
| EP-08 | Administración y Code Freeze | Sprint 8 | RNF-02, RNF-05 | 31 |
|  |  |  | TOTAL | 288 |
| Rol | Panel principal | Caso de uso asociado |
| --- | --- | --- |
| Operario | Panel de Operario | Gestionar producción |
| Jefe de Área | Panel de Control de Área | Gestionar producción |
| Jefe de Planta | Panel de Jefe de Planta | Gestionar producción |
| Tintorero | Panel de Tintorería | Gestionar formulaciones de tintorería |
| Personal de Empaquetado | Estación de Empaquetado | Registrar pesaje y etiquetado de lotes |
| Personal de Despacho | Panel de Despacho | Despachar y validar lotes mediante QR |
| Bodeguero | Panel de Bodeguero | Gestionar inventario, kárdex y MRP |
| Vendedor | Panel de Ventas | Gestionar clientes, pedidos y cartera |
| Ejecutivo | Panel de Reportería Ejecutiva | Consultar panel ejecutivo y reportes |
| Administrador de Sede | Panel de Administrador de Sede | Administrar usuarios y auditoría |
| Administrador de Sistemas | Panel de Administración | Administrar usuarios, sedes y auditoría |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-00 | Sprint 0 | 5 | Must | RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-00 | Sprint 0 | 3 | Must | RNF-01, RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-00 | Sprint 0 | 5 | Must | RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-00 | Sprint 0 | 5 | Must | RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-00 | Sprint 0 | 3 | Should | RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-01 | Sprint 1 | 8 | Must | RNF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-01 | Sprint 1 | 8 | Must | RNF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-01 | Sprint 1 | 8 | Must | RNF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-01 | Sprint 1 | 5 | Must | RNF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-01 | Sprint 1 | 3 | Should | RNF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 5 | Must | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 5 | Must | RF-01, RNF-05 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 5 | Must | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 5 | Must | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 3 | Should | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 5 | Must | RF-01, RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-02 | Sprint 2 | 4 | Should | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-03 | Sprint 3 | 8 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-03 | Sprint 3 | 5 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-03 | Sprint 3 | 5 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-03 | Sprint 3 | 5 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-03 | Sprint 3 | 5 | Should | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-03 | Sprint 3 | 4 | Must | RNF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-04 | Sprint 4 | 8 | Must | RF-01, RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-04 | Sprint 4 | 5 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-04 | Sprint 4 | 5 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-04 | Sprint 4 | 8 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-04 | Sprint 4 | 3 | Should | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-04 | Sprint 4 | 3 | Could | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 5 | Must | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 5 | Must | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 8 | Must | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 3 | Must | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 8 | Must | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 5 | Must | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-05 | Sprint 5 | 3 | Should | RF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 8 | Must | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 5 | Must | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 8 | Must | RF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 5 | Must | RF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 3 | Must | RF-01, RNF-05 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 5 | Must | RF-01, RF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-06 | Sprint 6 | 3 | Should | RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-07 | Sprint 7 | 8 | Must | RF-04, RNF-03 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-07 | Sprint 7 | 8 | Must | RF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-07 | Sprint 7 | 8 | Must | RF-05 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-07 | Sprint 7 | 5 | Must | RF-05, RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-07 | Sprint 7 | 5 | Should | RF-05 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-08 | Sprint 8 | 8 | Must | RNF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-08 | Sprint 8 | 5 | Must | RNF-02 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-08 | Sprint 8 | 5 | Must | RNF-04 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-08 | Sprint 8 | 5 | Must | RNF-01 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-08 | Sprint 8 | 5 | Should | RNF-05 |
| Épica | Sprint | Puntos | Prioridad | Requisito |
| --- | --- | --- | --- | --- |
| EP-08 | Sprint 8 | 3 | Must | RNF-04 |
| Sprint | Épica | Historias | Puntos | Must | Should | Could |
| --- | --- | --- | --- | --- | --- | --- |
| Sprint 0 | EP-00 | 5 | 21 | 4 | 1 | 0 |
| Sprint 1 | EP-01 | 5 | 32 | 4 | 1 | 0 |
| Sprint 2 | EP-02 | 7 | 32 | 5 | 2 | 0 |
| Sprint 3 | EP-03 | 6 | 32 | 5 | 1 | 0 |
| Sprint 4 | EP-04 | 6 | 32 | 4 | 1 | 1 |
| Sprint 5 | EP-05 | 7 | 37 | 6 | 1 | 0 |
| Sprint 6 | EP-06 | 7 | 37 | 6 | 1 | 0 |
| Sprint 7 | EP-07 | 5 | 34 | 4 | 1 | 0 |
| Sprint 8 | EP-08 | 6 | 31 | 5 | 1 | 0 |
| Total | 9 épicas | 54 | 288 | 43 | 10 | 1 |
| Requisito | Descripción | Historias que lo implementan |
| --- | --- | --- |
| RF-01 | Digitalización del seguimiento de Órdenes de Producción | TEX-11, TEX-12, TEX-13, TEX-14, TEX-15, TEX-16, TEX-17, TEX-24, TEX-28, TEX-37, TEX-38, TEX-39, TEX-41, TEX-42 |
| RF-02 | Kárdex de Inventario Digital con Trazabilidad | TEX-16, TEX-18, TEX-19, TEX-20, TEX-21, TEX-22, TEX-24, TEX-25, TEX-26, TEX-27, TEX-29, TEX-40 |
| RF-03 | Gestión Comercial con Control de Crédito | TEX-30, TEX-31, TEX-32, TEX-33, TEX-34, TEX-35, TEX-36 |
| RF-04 | Despacho Validado por Código de barras o QR | TEX-42, TEX-44, TEX-45 |
| RF-05 | Dashboard Ejecutivo de KPIs | TEX-46, TEX-47, TEX-48 |
| RNF-01 | Seguridad de la Información | TEX-02, TEX-06, TEX-09, TEX-10, TEX-52 |
| RNF-02 | Seguridad (Control de acceso) | TEX-07, TEX-08, TEX-23, TEX-49, TEX-50 |
| RNF-03 | Rendimiento y Tiempo de Respuesta | TEX-17, TEX-22, TEX-44 |
| RNF-04 | Mantenibilidad y Escalabilidad | TEX-01, TEX-02, TEX-03, TEX-04, TEX-05, TEX-43, TEX-47, TEX-51, TEX-54 |
| RNF-05 | Usabilidad para el Usuario Operativo | TEX-12, TEX-41, TEX-53 |
| Ceremonia | Momento | Duración | Propósito |
| --- | --- | --- | --- |
| Sprint Planning | Primer día del sprint | 2 h | Seleccionar los elementos del backlog y acordar el Sprint Goal |
| Daily Scrum | Diario | 15 min | Sincronizar avance e identificar impedimentos |
| Sprint Review | Último día del sprint | 1,5 h | Presentar el incremento y recoger retroalimentación |
| Sprint Retrospective | Tras la Review | 1 h | Inspeccionar el proceso y acordar mejoras |
| Refinamiento | Mitad del sprint | 1 h | Preparar y estimar el backlog del sprint siguiente |
| Concepto | Valor |
| --- | --- |
| Tamaño del equipo | 1 desarrollador full stack |
| Jornada | 5 días por semana, 8 horas diarias |
| Duración del sprint | 2 semanas (10 días hábiles) |
| Capacidad por sprint | 80 horas |
| Esfuerzo total de desarrollo | 640 horas en 16 semanas |
| Velocidad objetivo | 33 puntos de historia por sprint |
| Factor de conversión | ≈ 2,4 horas por punto |
| Sprint | Inicio | Fin | Semanas | Puntos | Release asociado |
| --- | --- | --- | --- | --- | --- |
| Sprint 0 | 21 Sep 2026 | 02 Oct 2026 | 1–2 | 21 | — (preparación) |
| Sprint 1 | 05 Oct 2026 | 16 Oct 2026 | 3–4 | 32 | R1 — Núcleo seguro |
| Sprint 2 | 19 Oct 2026 | 30 Oct 2026 | 5–6 | 32 | R1 — Núcleo seguro |
| Sprint 3 | 02 Nov 2026 | 13 Nov 2026 | 7–8 | 32 | R2 — Operación de planta |
| Sprint 4 | 16 Nov 2026 | 27 Nov 2026 | 9–10 | 32 | R2 — Operación de planta |
| Sprint 5 | 30 Nov 2026 | 11 Dic 2026 | 11–12 | 37 | R3 — Ciclo comercial |
| Sprint 6 | 14 Dic 2026 | 25 Dic 2026 | 13–14 | 37 | R3 — Ciclo comercial |
| Sprint 7 | 04 Ene 2027 | 15 Ene 2027 | 15–16 | 34 | R4 — Sistema completo |
| Sprint 8 | 18 Ene 2027 | 29 Ene 2027 | 17–18 | 31 | R4 — Sistema completo |
| Hito | Fecha | Contenido |
| --- | --- | --- |
| Code Freeze | 29 Ene 2027 | Cierre del Sprint 8; solo correcciones de defectos |
| Pruebas integrales y preproducción | Febrero 2027 | QA integral y preparación del despliegue |
| Puesta en marcha (Fase 5) | Marzo 2027 | Sincronización con impresoras Zebra y hardware óptico; talleres operativos de máximo 2 horas por grupo |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-01 | Orquestación de contenedores con Docker Compose | 5 | Must |
| TEX-02 | Red de contenedores aislada y comunicación entre servicios | 3 | Must |
| TEX-03 | API Gateway con Nginx como punto único de entrada | 5 | Must |
| TEX-04 | Pipeline de CI con Quality Gates | 5 | Must |
| TEX-05 | Estructura base del repositorio y estándares de desarrollo | 3 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-06 | Autenticación con JWT en cookies HttpOnly | 8 | Must |
| TEX-07 | Control de acceso basado en roles para los once roles | 8 | Must |
| TEX-08 | Aislamiento multi-sede de la información | 8 | Must |
| TEX-09 | Registro de auditoría inmutable en operaciones críticas | 5 | Must |
| TEX-10 | Justificación obligatoria en modificación de datos maestros | 3 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-11 | Creación de Órdenes de Producción | 5 | Must |
| TEX-12 | Registro de lote de producción en un solo paso | 5 | Must |
| TEX-13 | Asignación de máquina y operario a una orden | 5 | Must |
| TEX-14 | Máquina de estados del ciclo de vida de la orden | 5 | Must |
| TEX-16 | Rechazo de lote con reversión de inventario | 5 | Must |
| TEX-15 | Gestión de maquinaria del área | 3 | Should |
| TEX-17 | Monitoreo del avance de planta | 4 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-18 | Kárdex transaccional con saldo en tiempo real | 8 | Must |
| TEX-19 | Entrada de materia prima con trazabilidad de lote | 5 | Must |
| TEX-20 | Transferencia de existencias entre bodegas | 5 | Must |
| TEX-21 | Edición auditada de movimientos de inventario | 5 | Must |
| TEX-23 | Filtrado de bodegas por rol y sede | 4 | Must |
| TEX-22 | Consulta y exportación del kárdex | 5 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-24 | Transformación de productos con cálculo de merma | 8 | Must |
| TEX-27 | Motor MRP de cálculo de requerimientos | 8 | Must |
| TEX-25 | Bloqueo de saldos negativos de inventario | 5 | Must |
| TEX-26 | Alertas de stock bajo | 5 | Must |
| TEX-28 | Consulta de requisitos de materiales de una orden | 3 | Should |
| TEX-29 | Registro de merma vendible | 3 | Could |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-32 | Validación automática de límite de crédito | 8 | Must |
| TEX-34 | Reconciliación de pagos con criterio FIFO | 8 | Must |
| TEX-30 | Directorio de clientes con aislamiento de cartera | 5 | Must |
| TEX-31 | Registro de pedidos de venta | 5 | Must |
| TEX-35 | Reversión auditada de pagos | 5 | Must |
| TEX-33 | Validación de precio mínimo de venta | 3 | Must |
| TEX-36 | Estado de cuenta del cliente | 3 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-37 | Recetas de tintorería por fases | 8 | Must |
| TEX-39 | Calculadora de dosificación asociada a la orden | 8 | Must |
| TEX-38 | Versionamiento de fórmulas de color | 5 | Must |
| TEX-40 | Descarga automática de químicos al inventario | 5 | Must |
| TEX-42 | Emisión de etiqueta ZPL para impresoras Zebra | 5 | Must |
| TEX-41 | Registro de pesaje en estación de empaquetado | 3 | Must |
| TEX-43 | Equivalencias de empaque configurables por sede | 3 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-44 | Microservicio de escaneo de códigos QR y de barras | 8 | Must |
| TEX-45 | Despacho atómico con descarga de inventario | 8 | Must |
| TEX-46 | Panel ejecutivo de indicadores | 8 | Must |
| TEX-47 | Microservicio de reportes en Excel | 5 | Must |
| TEX-48 | Drill-down sobre los indicadores | 5 | Should |
| ID | Historia | Puntos | Prioridad |
| --- | --- | --- | --- |
| TEX-49 | Panel de Administrador de Sistemas | 8 | Must |
| TEX-50 | Panel de Administrador de Sede | 5 | Must |
| TEX-51 | Gestión de catálogos maestros | 5 | Must |
| TEX-52 | Consulta del registro de auditoría | 5 | Must |
| TEX-54 | Congelamiento de código y despliegue en staging | 3 | Must |
| TEX-53 | Persistencia del estado de navegación en la URL | 5 | Should |
| Métrica | Definición | Fuente |
| --- | --- | --- |
| Velocidad | Puntos completados que cumplen la DoD | Tablero Jira |
| Cobertura de pruebas | Porcentaje de líneas cubiertas en el núcleo | coverage report |
| Quality Gates superados | Ejecuciones del pipeline en verde | Pipeline CI/CD |
| Defectos escapados | Defectos detectados tras cerrar el sprint | Incidencias en Jira |
| Compromiso cumplido | Puntos completados ÷ puntos comprometidos | Tablero Jira |
| ID | Riesgo | Sprint | Impacto | Probabilidad | Mitigación |
| --- | --- | --- | --- | --- | --- |
| R-01 | Período festivo reduce la capacidad real | 6 | Alto | Alta | Diferir TEX-43; reducir el compromiso a 34 puntos |
| R-02 | Indisponibilidad de impresoras Zebra para pruebas | 6 | Alto | Media | Verificar conectividad durante el Sprint 5 |
| R-03 | Umbral de 2500 ms no alcanzado en red de planta | 7 | Alto | Media | Medir en entorno real desde el inicio del sprint |
| R-04 | Defectos de concurrencia en el saldo de inventario | 3 | Alto | Media | Pruebas explícitas de operaciones simultáneas |
| R-05 | Sobrecarga sostenida en los sprints 5 y 6 | 5, 6 | Medio | Alta | Diferir las historias Should identificadas |
| R-06 | Cobertura por debajo del 75 % bloquea la integración | Todos | Medio | Media | Desarrollo guiado por pruebas desde el Sprint 1 |
| R-07 | Defecto en el aislamiento multi-sede se propaga | 1 | Alto | Baja | Matriz completa de pruebas RBAC antes de cerrar |