# ADR-011 — Equivalencias de empaque por sede, sin constante del sistema (TexCore)

> Numeración continua con ADR-010 (`ADR_010_RENDIMIENTO_STOCK_Y_AUDITORIA.md`).
**Tema:** Qué hace el sistema cuando una sede no tiene equivalencias de empaque
**Fecha:** 7-oct-2026 · **Estado:** Aceptada (decisión del usuario) · **Origen:** TEX-43, la única historia sin implementación completa en la auditoría del backlog

## 1. Contexto

Las equivalencias de hilo son **ejemplos de referencia por sede** (`CLAUDE.md`), no constantes del sistema. Por ejemplo: 1 baño = 15 fundas = 225 conos.

`ConfiguracionEmpaqueSede` existía desde el 2-sep, pero no tenía API ni pantalla. Una sede sin fila usaba **225/15 en silencio** en dos lugares:
- `LoteProduccion.clean()`, al registrar un lote por baño o funda sin unidades;
- `MRPEngine`, al convertir pedidos a baños.

TEX-43 CA-3 exige lo contrario: *«el sistema informa la ausencia de configuración en lugar de aplicar una constante del sistema»*.

## 2. Decisión

1. **Quién configura:**
   - el **Administrador de Sede**, la suya (pestaña **Configuración** de su panel);
   - el **Administrador de Sistemas**, cualquier sede (**Gestión → Sedes**, con la sede del menú lateral).

   API: `GET`/`PUT /api/configuracion-empaque/`. Es un dato maestro: cambiarlo exige una justificación de al menos 10 caracteres y queda en el AuditLog (TEX-10).
2. **Sin configuración:**
   - el registro de un lote por baño o funda sin unidades se rechaza con «La sede X no tiene configuradas las equivalencias de empaque»;
   - el MRP omite los pedidos de esa sede y lo avisa en la respuesta de `ejecutar-mrp`, porque el motor corre en segundo plano.

   No hay valor por defecto en el modelo.
3. **Despliegue sin cambio de comportamiento:** la migración `gestion/0006_configuracion_empaque_explicita` crea la configuración 15/15 de cada sede existente. Las sedes nuevas no la reciben; la registra su administrador.
4. **Comandos de datos** (`seed_data`, `simular_operacion`, `stress_test_data`, `stress_ventas_data`, `load_million`): crean la configuración de las sedes que generan.

## 3. Consecuencias

* Cada conversión usa una equivalencia que alguien registró y justificó en la sede.
* Una sede nueva debe configurar sus equivalencias antes de registrar lotes por baño o funda sin unidades, y antes de que el MRP calcule sus pedidos. Los manuales del Admin de Sede, Admin de Sistemas, Empaquetado, Bodeguero y Ejecutivo lo explican.
* La equivalencia de telas (baño → metros) sigue fuera de alcance, porque ninguna conversión la usa hoy.
