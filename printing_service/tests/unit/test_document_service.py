"""
Tests unitarios de DocumentService.
Migrados desde test_nota_venta_calculos.py — misma lógica, nueva ubicación.
No requieren HTTP ni WeasyPrint.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): un detalle / lista vacia / detalle con iva / multiples detalles / detalle sin
  iva.
- Análisis de valores límite (BVA): lista vacia / todo cero.
"""

import pytest

from src.schemas.printing import DetallePedido, NotaVentaRequest
from src.services.document_service import DocumentService


def _make_detalle(peso: float, precio: float, incluye_iva: bool = False) -> DetallePedido:
    return DetallePedido(
        producto_descripcion="Hilo Nylon 100%",
        cantidad=1.0,
        piezas=1,
        peso=peso,
        precio_unitario=precio,
        incluye_iva=incluye_iva,
    )


class TestDocumentService_Subtotal:
    def test_subtotal_dado_un_detalle_cuando_calcular_entonces_es_peso_por_precio(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0)]
        assert DocumentService.calcular_subtotal(detalles) == pytest.approx(50.0)

    def test_subtotal_dado_lista_vacia_cuando_calcular_entonces_es_cero(self):
        assert DocumentService.calcular_subtotal([]) == pytest.approx(0.0)

    def test_subtotal_dado_detalle_con_iva_cuando_calcular_entonces_iva_no_afecta_subtotal(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)]
        assert DocumentService.calcular_subtotal(detalles) == pytest.approx(50.0)

    def test_subtotal_dado_multiples_detalles_cuando_calcular_entonces_suma_todos(self):
        detalles = [_make_detalle(5.0, 2.0), _make_detalle(3.0, 4.0)]
        assert DocumentService.calcular_subtotal(detalles) == pytest.approx(22.0)


class TestDocumentService_Iva:
    def test_iva_dado_detalle_sin_iva_cuando_calcular_entonces_es_cero(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0, incluye_iva=False)]
        assert DocumentService.calcular_iva(detalles) == pytest.approx(0.0)

    def test_iva_dado_detalle_con_iva_cuando_calcular_entonces_es_15_porciento(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)]
        assert DocumentService.calcular_iva(detalles) == pytest.approx(7.5)

    def test_iva_dado_mix_iva_cuando_calcular_entonces_solo_suma_los_que_aplican(self):
        detalles = [
            _make_detalle(peso=10.0, precio=5.0, incluye_iva=True),
            _make_detalle(peso=10.0, precio=5.0, incluye_iva=False),
        ]
        assert DocumentService.calcular_iva(detalles) == pytest.approx(7.5)


class TestDocumentService_Total:
    def test_total_dado_sin_retencion_cuando_calcular_entonces_es_subtotal_mas_iva(self):
        assert DocumentService.calcular_total(50.0, 7.5, 0.0) == pytest.approx(57.5)

    def test_total_dado_retencion_cuando_calcular_entonces_se_descuenta(self):
        assert DocumentService.calcular_total(50.0, 0.0, 5.0) == pytest.approx(45.0)

    def test_total_dado_todo_cero_cuando_calcular_entonces_es_cero(self):
        assert DocumentService.calcular_total(0.0, 0.0, 0.0) == pytest.approx(0.0)


class TestDocumentService_FormatearFecha:
    def test_formatear_fecha_dado_iso_valido_cuando_formatear_entonces_retorna_ddmmyyyy(self):
        result = DocumentService.formatear_fecha("2026-03-27T10:00:00")
        assert result == "27/03/2026 10:00"

    def test_formatear_fecha_dado_string_invalido_cuando_formatear_entonces_retorna_original(self):
        result = DocumentService.formatear_fecha("no-es-fecha")
        assert result == "no-es-fecha"

    def test_formatear_fecha_dado_utc_z_cuando_formatear_entonces_parsea_correctamente(self):
        result = DocumentService.formatear_fecha("2026-03-27T10:00:00Z")
        assert "2026" in result

    def test_formatear_fecha_dado_fecha_sin_hora_cuando_formatear_entonces_incluye_hora_cero(self):
        result = DocumentService.formatear_fecha("2026-01-15T00:00:00")
        assert result == "15/01/2026 00:00"

    # El backend guarda en UTC; el documento se lee con el reloj de la planta (Ecuador, UTC-5).
    def test_formatear_fecha_dado_utc_cuando_formatear_entonces_hora_de_la_planta(self):
        assert DocumentService.formatear_fecha("2026-10-27T18:23:00Z") == "27/10/2026 13:23"

    # BVA: pasada la medianoche UTC sigue siendo el día anterior en la planta.
    def test_formatear_fecha_dado_madrugada_utc_cuando_formatear_entonces_fecha_del_dia_anterior(self):
        assert DocumentService.formatear_fecha("2026-10-28T02:00:00+00:00") == "27/10/2026 21:00"

    def test_formatear_fecha_dado_texto_ya_formateado_cuando_formatear_entonces_lo_deja_igual(self):
        assert DocumentService.formatear_fecha("27/10/2026 13:23") == "27/10/2026 13:23"


class TestFiltroFechaHoraEnPlantillas:
    """Las plantillas muestran `generado_en` en hora de la planta, no el ISO crudo en UTC."""

    def test_filtro_dado_entorno_pdf_cuando_se_crea_entonces_registra_fecha_hora(self):
        from src.routers.pdf import get_pdf_strategy

        assert "fecha_hora" in get_pdf_strategy()._env.filters

    def test_plantillas_dado_generado_en_iso_utc_cuando_renderizan_entonces_hora_de_la_planta(self):
        from jinja2 import ChainableUndefined

        from src.routers.pdf import get_pdf_strategy

        # Solo se pasa generado_en: ChainableUndefined deja vacío el resto de los datos.
        env = get_pdf_strategy()._env.overlay(undefined=ChainableUndefined)
        plantillas = [
            "reporte_avance.html",
            "reporte_balance.html",
            "historial_despachos.html",
            "produccion_por_producto.html",
            "formula_dosificacion.html",
            "historial_mantenimiento.html",
        ]
        for nombre in plantillas:
            html = env.get_template(nombre).render(
                generado_en="2026-10-27T18:23:00Z",
                filtros={},
                totales={"horas_total": 0, "horas_planificadas": 0, "paros_en_curso": 0},
                detalles=[],
                despachos=[],
                productos=[],
                fases=[],
                detalle=[],
                resumen=[],
                peso_kg=0,
                litros_bano=0,
                relacion_bano=0,
            )
            assert "27/10/2026 13:23" in html, nombre
            assert "2026-10-27T18:23:00Z" not in html, nombre


class TestDocumentService_ConstruirContexto:
    def test_construir_contexto_dado_request_valido_cuando_construir_entonces_tiene_subtotal(self):
        request = NotaVentaRequest(
            id=1,
            fecha_pedido="2026-03-27T10:00:00",
            detalles=[_make_detalle(peso=10.0, precio=5.0)],
        )
        ctx = DocumentService.construir_contexto(request)
        assert ctx.subtotal == pytest.approx(50.0)
        assert ctx.fecha_pedido_formatted == "27/03/2026 10:00"

    def test_construir_contexto_dado_detalles_con_iva_cuando_construir_entonces_calcula_total_correcto(self):
        request = NotaVentaRequest(
            id=2,
            fecha_pedido="2026-03-27T10:00:00",
            valor_retencion=5.0,
            detalles=[_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)],
        )
        ctx = DocumentService.construir_contexto(request)
        assert ctx.subtotal == pytest.approx(50.0)
        assert ctx.iva == pytest.approx(7.5)
        assert ctx.total == pytest.approx(52.5)
