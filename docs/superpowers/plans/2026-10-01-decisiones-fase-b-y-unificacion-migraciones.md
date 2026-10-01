# Decisiones pendientes de la Fase B y unificación de migraciones — Implementation Plan

**Estado:** completado el 1-oct-2026 (5/5).

**Goal:** aplicar las decisiones del usuario del 1-oct-2026 sobre los pendientes de la Fase B y dejar las migraciones de `gestion` e `inventory` unificadas en una inicial por app.

**Origen:** pendientes del plan `docs/superpowers/plans/2026-10-01-fase-b-rutas-sin-consumidor.md`.

Cada paso: prueba primero (roja), implementación, prueba verde. Backend en SQL Server (`scripts/run_backend_tests.sh`, que corre las migraciones reales); frontend con `npx tsc --noEmit` y `npm test`.

## Decisiones del usuario (1-oct-2026)

1. **Venta de contado sin pago registrado: se permite.** Se da un día para pagar; el personal adelanta la facturación pero no entrega el producto hasta el pago, y eso es gestión interna. Crear un pedido con `esta_pagado: true` omite el límite de crédito y el bloqueo por cartera vencida, como hasta ahora.
2. **El Administrador de Sede es un rol gerencial de monitoreo:** ve lo que pasa y toma decisiones, pero no opera el sistema. En transferencias interárea: puede listarlas y no crearlas.
3. **Migraciones unificadas:** el sistema corre en un solo servidor de pruebas y el resto está en desarrollo; la base de ese servidor se puede rehacer.

## Pasos

1. [x] **Venta de contado:** prueba que fija la regla (pedido con `esta_pagado: true` para un cliente sobre su límite → 201) y documentación en `ROLES_Y_PERMISOS.md`.
2. [x] **Transferencias interárea:** `create` solo Jefe de Planta y Admin de Sistemas; `list` también Admin de Sede (y Jefe de Área, el de su área).
3. [x] **Unificación de migraciones:**
   - `gestion`: las 17 migraciones pasan a una inicial generada desde los modelos actuales. Se conserva `fix_token_blacklist_mssql` (RunPython que quita una restricción de `token_blacklist` en SQL Server; también hace falta en una base nueva).
   - `inventory`: las 4 migraciones pasan a una inicial.
   - Se descartan las migraciones de datos que solo transformaban datos existentes (`0004` precarga de empaque, `0013` producto intermedio → colorante, `0014` fases → procesos de tintorería, `inventory/0004` enlace de compras con su lote de MP) y sus pruebas (`MigracionFasesAProcesosTestCase`, `EnlaceComprasExistentesTestCase`).
   - La corrección de datos de las transformaciones anteriores a B2 ya no hace falta: al rehacer la base, esos movimientos desaparecen.
   - `makemigrations --check` sin cambios; suite completa en SQL Server (crea la base con las migraciones nuevas).
4. [x] **Procedimiento para el servidor de pruebas** (en el CHANGELOG): respaldo, base nueva, `migrate`, `seed_production_masters`.
5. [x] Suites completas, CHANGELOG, `graphify update .`.

## Decisión posterior

- **El Administrador de Sede conserva sus permisos de escritura** en órdenes, lotes, ventas, catálogo, inventario, despacho y MRP (decisión del usuario, 1-oct-2026). Solo cambia lo de transferencias interárea: puede listarlas y no crearlas.
