"""
Tests del printing_service — lógica de cálculo de NotaVentaRequest.
Aplica técnicas ISTQB:
  - Partición de Equivalencia (EP): detalles con/sin IVA
  - Análisis de Valores Límite (BVA): 0 detalles, 1 detalle, N detalles

Convención: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]

Estos tests son puramente unitarios — no requieren red, base de datos
ni WeasyPrint instalado.
"""
import sys
import os

# Añadir src/ al path para importar el módulo directamente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from main import DetallePedido, NotaVentaRequest, EtiquetaRequest


def _make_detalle(peso: float, precio: float, incluye_iva: bool = False) -> DetallePedido:
    return DetallePedido(
        producto_descripcion="Hilo Nylon 100%",
        cantidad=1.0,
        piezas=1,
        peso=peso,
        precio_unitario=precio,
        incluye_iva=incluye_iva,
    )


def _make_nota(detalles, valor_retencion: float = 0.0) -> NotaVentaRequest:
    return NotaVentaRequest(
        id=1,
        fecha_pedido="2026-03-27T10:00:00",
        detalles=detalles,
        valor_retencion=valor_retencion,
    )


# ---------------------------------------------------------------------------
# Cálculo de subtotal
# ---------------------------------------------------------------------------

class TestNotaVentaSubtotal:
    """ISTQB EP — clases de equivalencia para detalles con y sin IVA."""

    def test_nota_dado_un_detalle_sin_iva_cuando_calcular_subtotal_entonces_es_peso_por_precio(self):
        """BVA: 1 detalle exacto — caso mínimo con datos."""
        nota = _make_nota([_make_detalle(peso=10.0, precio=5.0)])
        assert nota.subtotal == pytest.approx(50.0)

    def test_nota_dado_detalle_con_iva_cuando_calcular_subtotal_entonces_iva_no_afecta_subtotal(self):
        """EP — incluye_iva solo afecta el campo iva, no el subtotal."""
        nota = _make_nota([_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)])
        assert nota.subtotal == pytest.approx(50.0)

    def test_nota_dado_multiples_detalles_cuando_calcular_subtotal_entonces_suma_todos(self):
        detalles = [
            _make_detalle(peso=5.0, precio=10.0),   # 50
            _make_detalle(peso=2.0, precio=20.0),   # 40
            _make_detalle(peso=3.0, precio=5.0),    # 15
        ]
        nota = _make_nota(detalles)
        assert nota.subtotal == pytest.approx(105.0)

    def test_nota_dado_lista_vacia_cuando_calcular_subtotal_entonces_es_cero(self):
        """BVA: 0 detalles — límite inferior."""
        nota = _make_nota([])
        assert nota.subtotal == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Cálculo de IVA
# ---------------------------------------------------------------------------

class TestNotaVentaIva:
    """ISTQB EP — solo los detalles con incluye_iva=True generan IVA (15%)."""

    def test_nota_dado_detalle_sin_iva_cuando_calcular_iva_entonces_es_cero(self):
        nota = _make_nota([_make_detalle(peso=10.0, precio=5.0, incluye_iva=False)])
        assert nota.iva == pytest.approx(0.0)

    def test_nota_dado_detalle_con_iva_cuando_calcular_iva_entonces_es_15_porciento(self):
        """IVA Ecuador: 15% sobre peso × precio."""
        nota = _make_nota([_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)])
        # subtotal = 50, iva = 50 * 0.15 = 7.50
        assert nota.iva == pytest.approx(7.5)

    def test_nota_dado_mezcla_detalles_cuando_calcular_iva_entonces_solo_aplica_a_gravados(self):
        """EP — solo los detalles gravados contribuyen al IVA."""
        detalles = [
            _make_detalle(peso=10.0, precio=5.0, incluye_iva=True),   # gravado: 50 * 0.15 = 7.5
            _make_detalle(peso=10.0, precio=5.0, incluye_iva=False),  # exento
        ]
        nota = _make_nota(detalles)
        assert nota.iva == pytest.approx(7.5)


# ---------------------------------------------------------------------------
# Cálculo de total
# ---------------------------------------------------------------------------

class TestNotaVentaTotal:
    """ISTQB BVA — total = subtotal + iva - retención."""

    def test_nota_dado_sin_retencion_cuando_calcular_total_entonces_es_subtotal_mas_iva(self):
        nota = _make_nota([_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)])
        assert nota.total == pytest.approx(50.0 + 7.5)

    def test_nota_dado_retencion_cuando_calcular_total_entonces_se_descuenta(self):
        nota = _make_nota(
            [_make_detalle(peso=10.0, precio=5.0)],
            valor_retencion=5.0,
        )
        # subtotal=50, iva=0, retencion=5 → total=45
        assert nota.total == pytest.approx(45.0)

    def test_nota_dado_retencion_igual_a_total_bruto_cuando_calcular_total_entonces_es_cero(self):
        """BVA: retención que absorbe todo el valor."""
        nota = _make_nota(
            [_make_detalle(peso=10.0, precio=5.0)],
            valor_retencion=50.0,
        )
        assert nota.total == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Validación de EtiquetaRequest
# ---------------------------------------------------------------------------

class TestEtiquetaRequestValidacion:
    """EP — campos requeridos vs. opcionales de EtiquetaRequest."""

    def test_etiqueta_dado_campos_requeridos_cuando_crear_entonces_es_valida(self):
        etiqueta = EtiquetaRequest(
            producto_desc="Hilo Poliéster Texturizado",
            lote_codigo="LOTE-00123",
            peso_neto=25.5,
            qr_data="https://texcore.local/lotes/LOTE-00123",
        )
        assert etiqueta.lote_codigo == "LOTE-00123"
        assert etiqueta.peso_neto == 25.5

    def test_etiqueta_dado_empresa_omitida_cuando_crear_entonces_usa_default(self):
        etiqueta = EtiquetaRequest(
            producto_desc="Hilo",
            lote_codigo="L-001",
            peso_neto=1.0,
            qr_data="data",
        )
        assert etiqueta.empresa == "TexCore Industrial"

    def test_etiqueta_dado_unidad_omitida_cuando_crear_entonces_usa_kg(self):
        etiqueta = EtiquetaRequest(
            producto_desc="Hilo",
            lote_codigo="L-001",
            peso_neto=1.0,
            qr_data="data",
        )
        assert etiqueta.unidad == "kg"
