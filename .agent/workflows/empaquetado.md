---
description: Pesaje y etiquetado de producto terminado.
---

1.  **Registro de Empaques**: Crear registros de bultos o cajas vinculados a una **Orden de Producción** activa.
2.  **Cálculo de Pesaje**: Ingresar el Peso Bruto y Tara para que el sistema calcule el **Peso Neto**.
3.  **Generación de Etiquetas**: Al registrar el lote se imprime automáticamente la etiqueta **ORIGINAL** (versión 1). La impresión intenta primero **Zebra Browser Print** (ZPL nativo); si no hay impresora Zebra disponible, genera un **PDF** (100×150mm) y abre el diálogo de impresión del navegador; como último recurso copia el ZPL al portapapeles.
4.  **Reimpresión gobernada**: Desde "Historial Reciente" o el **Buscador de Lotes**, el botón de impresora abre un modal que exige seleccionar un **motivo** (etiqueta dañada, perdida, atasco de impresora, etc.) antes de reimprimir una copia idéntica. Cada reimpresión queda registrada en auditoría (usuario, motivo, fecha) sin alterar los datos del lote.
5.  **Reetiquetado con cambio de datos** *(solo Jefe de Área / Jefe de Planta / Admin)*: Permite corregir peso neto o reclasificar la calidad de un lote ya registrado. Requiere motivo obligatorio, anula la etiqueta anterior y emite una nueva versión (`v2`, `v3`, ...). Si cambia el peso neto, ajusta automáticamente el stock de bodega. El código de lote y el QR de trazabilidad **nunca cambian**.
6.  **Búsqueda de Lotes**: Buscador dedicado por rango de fechas, turno, código de lote y calidad, con paginación, para localizar lotes de otras fechas y reimprimir/reetiquetar.
7.  **Selección de Contexto**: Asignar el lote producido a la máquina y turno correspondiente.

> Ver [docs/modulos/GESTION_ETIQUETAS.md](../../docs/modulos/GESTION_ETIQUETAS.md) para el diseño completo (modelo `EventoEtiqueta`, endpoints, RBAC y fundamento industrial).
