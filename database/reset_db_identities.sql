-- ============================================================
-- SCRIPT: Reset completo de datos e identidades (MSSQL)
-- ENV:    Solo desarrollo / pruebas
-- EFECTO: Borra TODA la data y resetea PKs desde 1
-- ============================================================

PRINT 'Deshabilitando todas las FK constraints...';
EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';

-- -------------------------------------------------------
-- Borrar en orden inverso de dependencias
-- -------------------------------------------------------
PRINT 'Borrando datos...';

DELETE FROM gestion_auditlog;
DELETE FROM gestion_bultoempaque;
DELETE FROM inventory_detallehistorialdespacho;
DELETE FROM inventory_historialdespachodetalle;
DELETE FROM inventory_historialdespacho;
DELETE FROM inventory_movimientoinventario;
DELETE FROM inventory_stockbodega;
DELETE FROM inventory_sugerenciareposicion;
DELETE FROM inventory_requerimientoinventario;
DELETE FROM gestion_detallepedido;
DELETE FROM gestion_pedidoventa;
DELETE FROM gestion_pagocliente;
DELETE FROM gestion_descargaquimicoop;
DELETE FROM gestion_loteproduccion;
DELETE FROM gestion_ordenproduccion;
DELETE FROM gestion_detalleformula;
DELETE FROM gestion_fasereceta;
DELETE FROM gestion_formulacolor;
DELETE FROM gestion_configuracionempaque;
DELETE FROM gestion_cliente;
DELETE FROM gestion_batch;
DELETE FROM gestion_maquina_operarios;
DELETE FROM gestion_maquina;
DELETE FROM gestion_processstep;
DELETE FROM gestion_proveedor;
DELETE FROM gestion_bodega;
DELETE FROM gestion_producto;
DELETE FROM gestion_customuser_bodegas_asignadas;
DELETE FROM gestion_customuser_superior;
DELETE FROM gestion_customuser_groups;
DELETE FROM gestion_customuser_user_permissions;
DELETE FROM gestion_customuser;
DELETE FROM gestion_area;
DELETE FROM gestion_sede;

-- Django internals
DELETE FROM django_admin_log;
DELETE FROM django_session;
DELETE FROM auth_permission;
DELETE FROM auth_group_permissions;
DELETE FROM auth_group;
DELETE FROM django_content_type;

-- -------------------------------------------------------
-- Resetear identity seeds a 0 (próximo INSERT será 1)
-- -------------------------------------------------------
PRINT 'Reseteando identity seeds...';

DBCC CHECKIDENT ('gestion_sede',              RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_area',              RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_customuser',        RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_producto',          RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_batch',             RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_proveedor',         RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_bodega',            RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_maquina',           RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_processstep',       RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_formulacolor',      RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_fasereceta',        RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_detalleformula',    RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_configuracionempaque', RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_cliente',           RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_pagocliente',       RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_ordenproduccion',   RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_descargaquimicoop', RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_loteproduccion',    RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_pedidoventa',       RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_detallepedido',     RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_bultoempaque',      RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('gestion_auditlog',          RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('inventory_stockbodega',     RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('inventory_movimientoinventario', RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('inventory_historialdespacho',    RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('auth_group',               RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('auth_permission',          RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('django_content_type',      RESEED, 0) WITH NO_INFOMSGS;

-- -------------------------------------------------------
-- Re-habilitar FK constraints
-- -------------------------------------------------------
PRINT 'Re-habilitando FK constraints...';
EXEC sp_MSforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT ALL';

PRINT '✓ Reset completo. Todos los identity seeds inician desde 1.';
