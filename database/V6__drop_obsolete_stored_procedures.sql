-- =============================================================================
-- TEXCORE — ELIMINACIÓN DE STORED PROCEDURES OBSOLETOS (SQL SERVER 2022)
-- =============================================================================
-- Contexto: Auditoría de performance del 31 de agosto de 2026.
-- Los 21 Stored Procedures de reportes constituían código muerto, ya que toda
-- la lógica de extracción de datos opera a través de Django ORM e internal_api
-- con índices de soporte (V2, V4 y V5). Este script elimina los procedimientos
-- remanentes de la base de datos de manera idempotente.
-- =============================================================================

USE [texcore_db];
GO

DROP PROCEDURE IF EXISTS dbo.sp_GetKardexBodega;
DROP PROCEDURE IF EXISTS dbo.sp_GetProductosCatalogo;
DROP PROCEDURE IF EXISTS dbo.sp_GetUsuariosSistema;
DROP PROCEDURE IF EXISTS dbo.sp_GetStockActualBodega;
DROP PROCEDURE IF EXISTS dbo.sp_GetValorizacionInventario;
DROP PROCEDURE IF EXISTS dbo.sp_GetInventarioAging;
DROP PROCEDURE IF EXISTS dbo.sp_GetRotacionInventario;
DROP PROCEDURE IF EXISTS dbo.sp_GetStockCeroBodega;
DROP PROCEDURE IF EXISTS dbo.sp_GetResumenMovimientos;
DROP PROCEDURE IF EXISTS dbo.sp_GetVentasPorVendedor;
DROP PROCEDURE IF EXISTS dbo.sp_GetTopClientesPorVendedor;
DROP PROCEDURE IF EXISTS dbo.sp_GetDeudoresPorVendedor;
DROP PROCEDURE IF EXISTS dbo.sp_GetVentasGerencial;
DROP PROCEDURE IF EXISTS dbo.sp_GetTopClientesGerencial;
DROP PROCEDURE IF EXISTS dbo.sp_GetDeudoresGerencial;
DROP PROCEDURE IF EXISTS dbo.sp_GetOrdenesProduccionGerencial;
DROP PROCEDURE IF EXISTS dbo.sp_GetLotesProduccionGerencial;
DROP PROCEDURE IF EXISTS dbo.sp_GetTendenciaProduccionGerencial;
DROP PROCEDURE IF EXISTS dbo.sp_GetStockAgrupadoPorSede;
DROP PROCEDURE IF EXISTS dbo.sp_GetRetroKardex;
DROP PROCEDURE IF EXISTS dbo.sp_GetReporteOrdenProduccionPorId;
GO
