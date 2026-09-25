"""
Pruebas de internal_api/services/report_dispatch.resolve_report: mapeo de cada report_path a su
función de datos y a su nombre de archivo (compartido por el flujo síncrono y el asíncrono).

Técnicas ISTQB:
- Tabla de decisión (TD): una fila por report_path soportado -> función de reporting_data + filename.
- Partición de equivalencia / valores límite (EP/BVA): `dias` del aging (válidos 30/60/90/180,
  no numérico, fuera de la lista) y `producto_id` del kardex ("0", vacío, numérico).
- Ruta no soportada -> ValueError.
"""
from unittest import mock

from django.test import SimpleTestCase

from internal_api.services import report_dispatch
from internal_api.services import reporting_data as rd

FILAS = [{'fila': 1}]
PARAMS = {'fecha_inicio': '2026-09-01', 'fecha_fin': '2026-09-30', 'sede_id': '3', 'bodega_id': '7'}

# report_path -> (función de reporting_data, filename esperado)
TABLA = {
    'export/productos': ('get_productos', 'catalogo_productos'),
    'export/usuarios': ('get_usuarios', 'directorio_usuarios'),
    'export/stock-actual': ('get_stock_actual', 'stock_actual_bodega_7'),
    'export/valorizacion': ('get_valorizacion', 'valorizacion_bodega_7'),
    'export/rotacion': ('get_rotacion', 'rotacion_bodega_7'),
    'export/stock-cero': ('get_stock_cero', 'stock_cero_bodega_7'),
    'export/stock-bajo': ('get_stock_bajo', 'stock_bajo_bodega_7'),
    'export/resumen-movimientos': ('get_resumen_movimientos', 'resumen_movimientos_bodega_7'),
    'gerencial/ventas': ('get_ventas_gerencial', 'ventas_gerencial_2026-09-01_2026-09-30'),
    'gerencial/top-clientes': ('get_top_clientes_gerencial', 'top_clientes_gerencial_2026-09-01_2026-09-30'),
    'gerencial/deudores': ('get_deudores_gerencial', 'clientes_deudores_gerencial'),
    'produccion/ordenes': ('get_ordenes_produccion', 'ordenes_produccion_2026-09-01_2026-09-30'),
    'produccion/lotes': ('get_lotes_produccion', 'lotes_produccion_2026-09-01_2026-09-30'),
    'produccion/tendencia': ('get_tendencia_produccion', 'tendencia_produccion_2026-09-01_2026-09-30'),
    'vendedores/12/ventas': ('get_ventas_vendedor', 'ventas_vendedor_12_2026-09-01_2026-09-30'),
    'vendedores/12/top-clientes': ('get_top_clientes_vendedor', 'top_clientes_vendedor_12_2026-09-01_2026-09-30'),
    'vendedores/12/deudores': ('get_deudores_vendedor', 'clientes_deudores_vendedor_12'),
}


class ResolveReportTestCase(SimpleTestCase):

    def _resolver(self, path, funcion, params=None):
        with mock.patch.object(rd, funcion, return_value=FILAS) as simulada:
            filas, nombre = report_dispatch.resolve_report(path, params or PARAMS)
        return filas, nombre, simulada

    def test_resolve_dado_cada_ruta_soportada_cuando_resuelve_entonces_llama_su_funcion_y_nombra_el_archivo(self):
        for path, (funcion, nombre_esperado) in TABLA.items():
            with self.subTest(path=path):
                filas, nombre, simulada = self._resolver(path, funcion)
                simulada.assert_called_once()
                self.assertEqual((filas, nombre), (FILAS, nombre_esperado))

    def test_resolve_dado_ruta_de_vendedor_cuando_resuelve_entonces_pasa_el_id_del_vendedor(self):
        _, _, simulada = self._resolver('vendedores/12/ventas', 'get_ventas_vendedor')
        simulada.assert_called_once_with('12', fecha_desde='2026-09-01', fecha_hasta='2026-09-30')

    def test_resolve_dado_ruta_gerencial_cuando_resuelve_entonces_filtra_por_sede_y_fechas(self):
        _, _, simulada = self._resolver('gerencial/ventas', 'get_ventas_gerencial')
        simulada.assert_called_once_with(sede_id='3', fecha_desde='2026-09-01', fecha_hasta='2026-09-30')

    # --- Kardex: producto_id ---
    def test_kardex_dado_producto_cuando_resuelve_entonces_lo_convierte_a_entero_y_nombra_por_producto(self):
        _, nombre, simulada = self._resolver(
            'export/kardex', 'get_kardex', dict(PARAMS, producto_id='5', lote_codigo='L-01'))
        simulada.assert_called_once_with(
            '7', producto_id=5, fecha_desde='2026-09-01', fecha_hasta='2026-09-30', lote_codigo='L-01')
        self.assertEqual(nombre, 'kardex_7_5')

    def test_kardex_dado_producto_cero_o_vacio_cuando_resuelve_entonces_es_de_toda_la_bodega(self):
        for producto_id in ('0', '', None):
            with self.subTest(producto_id=producto_id):
                _, nombre, simulada = self._resolver(
                    'export/kardex', 'get_kardex', dict(PARAMS, producto_id=producto_id, lote_codigo=''))
                self.assertIsNone(simulada.call_args.kwargs['producto_id'])
                self.assertIsNone(simulada.call_args.kwargs['lote_codigo'])
                self.assertEqual(nombre, 'movimientos_bodega_7')

    # --- Aging: dias ---
    def test_aging_dado_dias_validos_cuando_resuelve_entonces_los_respeta(self):
        for dias in ('30', '60', '90', '180'):
            with self.subTest(dias=dias):
                _, nombre, simulada = self._resolver('export/aging', 'get_aging', dict(PARAMS, dias=dias))
                simulada.assert_called_once_with('7', dias_minimos=int(dias))
                self.assertEqual(nombre, 'aging_inventario_bodega_7')

    def test_aging_dado_dias_invalidos_o_ausentes_cuando_resuelve_entonces_usa_30(self):
        for dias in ('45', 'abc', None, '0'):
            with self.subTest(dias=dias):
                params = dict(PARAMS) if dias is None else dict(PARAMS, dias=dias)
                _, _, simulada = self._resolver('export/aging', 'get_aging', params)
                simulada.assert_called_once_with('7', dias_minimos=30)

    # --- Rutas no soportadas ---
    def test_resolve_dado_ruta_no_soportada_cuando_resuelve_entonces_value_error(self):
        for path in ('export/inexistente', 'vendedores/12/otra-cosa', 'vendedores/12', ''):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    report_dispatch.resolve_report(path, PARAMS)
