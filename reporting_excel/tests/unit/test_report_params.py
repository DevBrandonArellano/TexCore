"""
Tests unitarios para src/schemas/report_params.py.
EP + BVA sobre validadores Pydantic de cada schema.
"""
import pytest
from datetime import date
from pydantic import ValidationError

from src.schemas.report_params import KardexParams, RangoFechaParams, VendedorParams, StockParams


class TestKardexParams:

    def test_kardex_dado_parametros_minimos_cuando_crea_entonces_ok(self):
        p = KardexParams(bodega_id=1)
        assert p.bodega_id == 1
        assert p.format == "xlsx"

    def test_kardex_dado_formato_csv_cuando_crea_entonces_ok(self):
        p = KardexParams(bodega_id=1, format="csv")
        assert p.format == "csv"

    def test_kardex_dado_formato_invalido_cuando_crea_entonces_validation_error(self):
        with pytest.raises(ValidationError):
            KardexParams(bodega_id=1, format="pdf")

    def test_kardex_dado_todos_los_campos_cuando_crea_entonces_ok(self):
        p = KardexParams(
            bodega_id=1,
            producto_id=10,
            proveedor_id=5,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 3, 31),
            lote_codigo="LOT-001",
            format="xlsx",
        )
        assert p.producto_id == 10
        assert p.lote_codigo == "LOT-001"


class TestRangoFechaParams:

    def test_rango_dado_fechas_validas_cuando_crea_entonces_ok(self):
        p = RangoFechaParams(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 3, 31))
        assert p.format == "xlsx"
        assert p.sede_id is None

    def test_rango_dado_formato_csv_cuando_crea_entonces_ok(self):
        p = RangoFechaParams(
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 3, 31),
            format="csv",
        )
        assert p.format == "csv"

    def test_rango_dado_formato_invalido_cuando_crea_entonces_validation_error(self):
        with pytest.raises(ValidationError):
            RangoFechaParams(
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 3, 31),
                format="pdf",
            )

    def test_rango_dado_sede_id_cuando_crea_entonces_ok(self):
        p = RangoFechaParams(
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 3, 31),
            sede_id=2,
        )
        assert p.sede_id == 2


class TestVendedorParams:

    def test_vendedor_dado_parametros_validos_cuando_crea_entonces_ok(self):
        p = VendedorParams(
            vendedor_id=5,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 3, 31),
        )
        assert p.vendedor_id == 5
        assert p.format == "xlsx"

    def test_vendedor_dado_formato_csv_cuando_crea_entonces_ok(self):
        p = VendedorParams(
            vendedor_id=5,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 3, 31),
            format="csv",
        )
        assert p.format == "csv"

    def test_vendedor_dado_sin_vendedor_id_cuando_crea_entonces_validation_error(self):
        with pytest.raises(ValidationError):
            VendedorParams(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 3, 31))


class TestStockParams:

    def test_stock_dado_bodega_id_cuando_crea_entonces_ok(self):
        p = StockParams(bodega_id=3)
        assert p.bodega_id == 3
        assert p.producto_id is None
        assert p.format == "xlsx"

    def test_stock_dado_bodega_y_producto_cuando_crea_entonces_ok(self):
        p = StockParams(bodega_id=3, producto_id=7)
        assert p.producto_id == 7

    def test_stock_dado_sin_bodega_id_cuando_crea_entonces_validation_error(self):
        with pytest.raises(ValidationError):
            StockParams()
