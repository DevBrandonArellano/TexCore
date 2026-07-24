---
description: Pesaje y etiquetado de producto terminado.
---

1.  **Registro de Empaques**: Crear registros de bultos o cajas vinculados a una **Orden de Producción** activa.
2.  **Cálculo de Pesaje y Control de Tolerancia**: Ingresar el Peso Bruto y Tara para que el sistema calcule el **Peso Neto**. Si el peso difiere más del 10% del requerimiento o promedio, se requiere confirmación explícita mediante casilla de tolerancia.
3.  **Generación y Selección de Impresora**: Al registrar el lote se imprime automáticamente la etiqueta **ORIGINAL** (versión 1). El usuario puede seleccionar en la cabecera su preferencia de impresión (Zebra Nativo ZPL, PDF Universal o Automático), la cual se persiste en `localStorage`.
4.  **Reimpresión gobernada**: Desde "Historial Reciente" o el **Buscador de Lotes**, el botón de impresora abre un modal que exige seleccionar un **motivo** (etiqueta dañada, perdida, atasco de impresora, etc.) antes de reimprimir una copia idéntica. Cada reimpresión queda registrada en auditoría (usuario, motivo, fecha) sin alterar los datos del lote.
5.  **Reetiquetado Supervisado con In-Situ Override**: Permite corregir peso neto o reclasificar la calidad de un lote ya registrado. Si la acción la ejecuta un empacador/operario, el modal exige ingresar el **Usuario y Contraseña del Jefe de Área/Supervisor** in-situ sin cerrar ni cambiar la sesión activa. El supervisor autenticado se registra inmutablemente en `EventoEtiqueta`. La operación anula la versión anterior y emite una nueva (`v2`, `v3`, ...), ajustando el stock en bodega. El código de lote y el QR **nunca cambian**.
6.  **Panel de KPIs Operativos**: Visualización en tiempo real de *Bultos Empacados Hoy*, *Peso Total Registrado (kg)* y *Promedio por Bulto (kg/bulto)*.
7.  **Búsqueda de Lotes por Fechas**: Buscador dedicado por rango de fechas, turno, código de lote y calidad, con paginación, disponible en la Estación de Empaque y en los paneles de Jefe de Área y Jefe de Planta.
8.  **Selección de Contexto**: Asignar el lote producido a la máquina y turno correspondiente.

> Ver [docs/modulos/GESTION_ETIQUETAS.md](../../docs/modulos/GESTION_ETIQUETAS.md) para el diseño completo (modelo `EventoEtiqueta`, endpoints, RBAC y fundamento industrial).

