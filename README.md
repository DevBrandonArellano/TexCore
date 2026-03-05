# TexCore - Sistema Integral de Gestión para la Industria Textil

TexCore es una plataforma empresarial robusta diseñada para optimizar los procesos de **Producción, Inventario y Ventas** en el sector textil. Construido con una arquitectura moderna bajo el paradigma de microservicios contenerizados, el sistema ofrece trazabilidad total desde la orden de venta hasta el despacho de producto terminado.

---

## 🛠 Arquitectura y Tecnologías

El sistema utiliza un stack tecnológico de alto rendimiento preparado para entornos de producción:

*   **Backend**: Python 3.12 + Django 5.x + Django REST Framework (DRF).
*   **Microservicio de Impresión**: FastAPI + WeasyPrint (PDF/ZPL).
*   **Microservicio de Exportación a Excel**: FastAPI + PyODBC + Pandas (`reporting_excel`).
*   **Frontend**: React + TypeScript + Vite + TailwindCSS + Shadcn/UI.
*   **Base de Datos**: Microsoft SQL Server 2022.
*   **Infraestructura**: Docker & Docker Compose (Arquitectura Dual Linux/Windows).
*   **Servidor de Producción**: Nginx + Gunicorn.
*   **CI/CD**: GitLab CI con estrategias de Rollback automático.

> [!TIP]
> Para detalles técnicos sobre la optimización de consultas (N+1) e indexación, consulta: [**Recursos Algorítmicos**](documentation/recursos_algoritmicos.md).

---

## 🚀 Guía de Inicio Rápido

Para garantizar la portabilidad entre Windows y Linux, utiliza los scripts de despliegue unificados.

### 1. Iniciar el Entorno
Ejecuta el script correspondiente a tu sistema operativo desde la raíz:
```bash
# Linux / macOS / WSL2
./deploy.sh

# Windows (PowerShell)
./deploy.ps1
```

### 2. Acceso al Sistema
*   **Frontend**: [http://localhost:3000](http://localhost:3000)
*   **API (Swagger/Docs)**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

### 3. Datos de Prueba (Seed)
Carga un entorno completo con usuarios, productos y bodegas:
```bash
docker exec texcore-backend-1 python manage.py seed_data
```
*Credenciales: Todos los usuarios de prueba (`user_admin_sistemas`, `user_vendedor`, etc.) usan la contraseña `password123`.*

---

---

## 📈 Lógica de Negocio y Operaciones

TexCore implementa reglas de negocio críticas para la salud financiera y logística, con módulos especializados por rol:

### 🏭 Módulo de Producción (Nuevo)
Flujo completo de manufactura textil con roles definidos:
*   **Jefe de Planta**: Planificación de órdenes y gestión de fórmulas.
*   **Jefe de Área**: Asignación de recursos (máquinas/operarios) y monitoreo de carga real.
*   **Operario**: Ejecución y registro de lotes "One-Click" con trazabilidad total.

📚 **[Ver Manual de Producción y Roles](docs/MANUAL_PRODUCCION_Y_ROLES.md)**

### 💼 Gestión Comercial y Logística
*   **Gestión de Crédito**: Validación atómica de pedidos contra el límite de crédito del cliente.
*   **Beneficios Dinámicos**: Lógica de descuentos para clientes normales y precios preferenciales para mayoristas.
*   **Empaquetado y Despacho**: Control de unidades logísticas (cajas, rollos) con generación automática de etiquetas ZPL y cálculo de tara.
*   **Kardex de Inventario**: Trazabilidad con precisión decimal para el control exacto de telas e hilos.

Para ver los diagramas de flujo y el esquema técnico de la base de datos, visita:
👉 [**Modelo de Datos y Procesos**](documentation/modelo_datos_proceso.md)

---

## 🧪 Validaciones y Calidad (Testing)

Contamos con una suite de pruebas integradas que validan el 100% de la lógica crítica en cada despliegue.

```bash
# Ejecutar suite unificada de lógica de negocio e inventario
docker exec texcore-backend-1 python manage.py test gestion.tests_integrados
```

### Microservicio de Exportación a Excel (`reporting_excel`)
Para proteger el código de futuros "rompimientos" o caídas del driver durante actualizaciones de Django, se implementó un Sandbox de Pruebas. Puedes ejecutar en cualquier momento para comprobar la salud absoluta de la exportación a Excel:

```bash
docker compose run --rm -e PYTHONPATH=/app reporting_excel pytest -v tests/
```


---

## 📚 Documentación Técnica Completa

Para acceder al índice maestro de toda la documentación técnica, operativa y de negocio, visita:

👉 **[Índice de Documentación (Wiki)](documentation/README.md)**

### Accesos Directos Destacados
*   [**Configuración de Docker**](documentation/docker_setup.md): Guía principal de infraestructura y solución de problemas.
*   [**Comandos de Producción**](documentation/comandos_produccion.md): "Cheatsheet" para sysadmins.
*   [**Modelo de Datos**](documentation/modelo_datos_proceso.md): Esquemas SQL y flujos de negocio.
*   [**Análisis Estratégico**](documentation/analisis_estrategico.md): Contexto de negocio (FODA, Ishikawa).

### Gestión del Proyecto
*   [**Roadmap**](ROADMAP.md): Hitos y visión a futuro.
*   [**Changelog**](CHANGELOG.md): Registro de cambios.

---

## 🤝 Contribución
Para mantener la consistencia del proyecto:
1. Mantén los finales de línea en **LF** (configura `core.autocrlf false`).
2. Actualiza siempre `gestion/tests_integrados.py` al modificar reglas de negocio.
3. No dupliques archivos de documentación; utiliza los enlaces del índice superior.
