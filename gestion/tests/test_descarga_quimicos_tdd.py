from rest_framework.test import APITestCase
from rest_framework import status
from gestion.tests.factories import (
    CustomUserFactory, SedeFactory, ProductoFactory,
    FormulaColorFactory, BodegaFactory, AreaFactory,
    FaseRecetaFactory, DetalleFormulaFactory
)
from gestion.models import OrdenProduccion, DescargaQuimicoOP
from inventory.models import StockBodega, MovimientoInventario
from decimal import Decimal


class DescargaQuimicosTDDTestCase(APITestCase):
    """
    Test Suite para validar la descarga automática de químicos (TDD).
    Verifica que la integración entre el endpoint de OP y el inventario sea robusta.
    """

    def setUp(self):
        # 1. Configuración de Infraestructura
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        # Asignar grupo para pasar validación de permisos en ViewSet
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.user)

        # 2. Configuración de Negocio (Fórmula y Químicos)
        self.producto_tela = ProductoFactory(tipo='tela', sede=self.sede)
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede, descripcion="Soda Cáustica")

        # Bodega de Químicos con Stock
        self.bodega = BodegaFactory(sede=self.sede, nombre="Bodega Químicos")
        self.stock_inicial = Decimal('100.00')

        # Asignar justificación correctamente según AuditableModelMixin
        stock = StockBodega(
            bodega=self.bodega,
            producto=self.quimico,
            cantidad=self.stock_inicial
        )
        stock._justificacion_auditoria = "Stock inicial para test"
        stock.save()

        # Crear Fórmula (Nombre de campos reales: nombre_color, description)
        self.formula = FormulaColorFactory(
            nombre_color="Azul TDD",
            sede=self.sede,
            estado='aprobada'
        )
        self.fase = FaseRecetaFactory(formula=self.formula, nombre='tintura')
        # DetalleFormula (Nombre de campos reales: producto, concentracion_gr_l)
        self.detalle = DetalleFormulaFactory(
            fase=self.fase,
            producto=self.quimico,
            concentracion_gr_l=Decimal('10.00'),  # 10 gr/L
            tipo_calculo='gr_l'
        )

    def test_crear_op_con_descarga_exitosa(self):
        """
        Verifica que al crear una OP, se calculen y descuenten los químicos.
        Lógica: 100 kg tela * 10 (relación baño fija en servicio) = 1000 L.
        1000 L * 10 gr/L = 10,000 gr = 10 kg.
        """
        url = '/api/ordenes-produccion/'
        data = {
            'codigo': 'OP-TDD-001',
            'producto': self.producto_tela.id,
            'formula_color': self.formula.id,
            'peso_neto_requerido': '100.00',
            'sede': self.sede.id,
            'area': self.area.id,
            'bodega_quimicos': self.bodega.id
        }

        response = self.client.post(url, data, format='json')

        # Validación de respuesta
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Error en creación: {response.data}")

        # Validación de Descarga de Químicos
        op = OrdenProduccion.objects.get(codigo='OP-TDD-001')
        descargas = DescargaQuimicoOP.objects.filter(orden_produccion=op)
        self.assertTrue(descargas.exists(), "No se generaron registros de descarga")

        # Validación de Cálculos (10 kg esperados)
        descarga_soda = descargas.get(producto=self.quimico)
        # Usamos string en Decimal para evitar problemas de precisión float
        self.assertEqual(Decimal(str(descarga_soda.cantidad_calculada_kg.normalize())), Decimal('10').normalize())

        # Validación de Inventario
        stock_final = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico).cantidad
        # 100 kg - 10 kg = 90 kg
        self.assertEqual(stock_final, Decimal('90.00'))

    def test_crear_op_sin_bodega_quimicos_no_descarga(self):
        """
        Verifica que si no se especifica bodega de químicos, no hay descarga.
        """
        url = '/api/ordenes-produccion/'
        data = {
            'codigo': 'OP-TDD-002',
            'producto': self.producto_tela.id,
            'formula_color': self.formula.id,
            'peso_neto_requerido': '50.00',
            'sede': self.sede.id,
            'area': self.area.id
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        op = OrdenProduccion.objects.get(codigo='OP-TDD-002')
        self.assertFalse(DescargaQuimicoOP.objects.filter(orden_produccion=op).exists())

    def test_reversion_descarga_al_eliminar_op(self):
        """
        TDD: Verifica que al eliminar una OP (DELETE), se revierta la descarga de químicos.
        """
        # 1. Crear OP con descarga
        url_create = '/api/ordenes-produccion/'
        data = {
            'codigo': 'OP-REVERT-001',
            'producto': self.producto_tela.id,
            'formula_color': self.formula.id,
            'peso_neto_requerido': '100.00',
            'sede': self.sede.id,
            'area': self.area.id,
            'bodega_quimicos': self.bodega.id
        }
        resp = self.client.post(url_create, data, format='json')
        op_id = resp.data['id']

        # Verificar stock descontado
        stock_descontado = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico).cantidad
        self.assertEqual(stock_descontado, Decimal('90.00'))

        # 2. Eliminar OP (Requiere justificación en el payload para el servicio de descarga)
        url_delete = f'/api/ordenes-produccion/{op_id}/'
        # El ViewSet debe manejar la justificación para llamar al servicio de reversión
        response = self.client.delete(url_delete, data={'justificacion': 'Error en pedido'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 3. Verificar stock revertido (Prueba de Estado - Crítica)
        stock_revertido = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico).cantidad
        self.assertEqual(stock_revertido, self.stock_inicial)

        # 4. Verificar que el registro de descarga fue eliminado por cascada (Comportamiento actual)
        self.assertFalse(DescargaQuimicoOP.objects.filter(orden_produccion_id=op_id).exists())

    def _crear_op(self, codigo, peso='100.00', **extra):
        data = {
            'codigo': codigo, 'producto_entrada': self.producto_tela.id,
            'formula_color': self.formula.id, 'peso_neto_requerido': peso,
            'sede': self.sede.id, 'area': self.area.id, 'bodega_quimicos': self.bodega.id,
            **extra,
        }
        return self.client.post('/api/ordenes-produccion/', data, format='json')

    def test_crear_op_dado_formula_con_gr_l_y_pct_cuando_descarga_entonces_ambos_calculados_y_registra_consumo_y_auditoria(self):
        """
        Migrado de tests_integrados.py::DescargaQuimicosOPTestCase (Fase 6.2 del barrido de
        higiene): una fórmula con un insumo gr/L y otro % debe descargar ambos correctamente,
        dejar un MovimientoInventario CONSUMO por cada uno, y registrar quién/cuándo descargó.
        """
        quimico_pct = ProductoFactory(tipo='quimico', sede=self.sede, descripcion='Tinte Reactivo')
        DetalleFormulaFactory(
            fase=self.fase, producto=quimico_pct, tipo_calculo='pct', porcentaje=Decimal('2.00'),
        )
        stock_pct = StockBodega(bodega=self.bodega, producto=quimico_pct, cantidad=Decimal('50.00'))
        stock_pct._justificacion_auditoria = 'Stock inicial para test'
        stock_pct.save()

        resp = self._crear_op('OP-TDD-DOSPCT')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        op = OrdenProduccion.objects.get(codigo='OP-TDD-DOSPCT')
        descargas = DescargaQuimicoOP.objects.filter(orden_produccion=op, estado='aplicada')
        self.assertEqual(descargas.count(), 2, "Debe haber 2 descargas (gr/L + pct)")

        descarga_gr_l = descargas.get(producto=self.quimico)
        self.assertEqual(descarga_gr_l.cantidad_calculada_kg, Decimal('10.000000'))
        descarga_pct = descargas.get(producto=quimico_pct)
        self.assertEqual(descarga_pct.cantidad_calculada_kg, Decimal('2.000000'))

        # Auditoría: la descarga registra quién y cuándo
        self.assertEqual(descarga_gr_l.descargado_por, self.user)
        self.assertIsNotNone(descarga_gr_l.fecha_descarga)

        stock_gr_l_final = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico).cantidad
        self.assertEqual(stock_gr_l_final, Decimal('90.00'))
        stock_pct_final = StockBodega.objects.get(bodega=self.bodega, producto=quimico_pct).cantidad
        self.assertEqual(stock_pct_final, Decimal('48.00'))

        movimientos = MovimientoInventario.objects.filter(
            tipo_movimiento='CONSUMO', documento_ref=f'OP-{op.codigo}')
        self.assertEqual(movimientos.count(), 2, "Debe haber 2 MovimientoInventario de CONSUMO")

    def test_modificar_op_dado_sin_justificacion_cuando_cambia_peso_entonces_400(self):
        resp_create = self._crear_op('OP-TDD-MOD1')
        op_id = resp_create.data['id']

        resp = self.client.patch(f'/api/ordenes-produccion/{op_id}/', {
            'peso_neto_requerido': '150.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_modificar_op_dado_con_justificacion_cuando_cambia_peso_entonces_reajusta_descarga_y_registra_justificacion(self):
        resp_create = self._crear_op('OP-TDD-MOD2')
        op_id = resp_create.data['id']
        orden = OrdenProduccion.objects.get(id=op_id)

        resp = self.client.patch(f'/api/ordenes-produccion/{op_id}/', {
            'peso_neto_requerido': '150.00', 'justificacion': 'Error en cálculo de peso, se corrige a 150 kg',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        orden.refresh_from_db()
        self.assertEqual(orden.peso_neto_requerido, Decimal('150.00'))

        # Descarga original (100kg -> 10kg) revertida, nueva (150kg -> 15kg) aplicada
        stock_final = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico).cantidad
        self.assertEqual(stock_final, self.stock_inicial - Decimal('15.000000'))

        descargas_revertidas = orden.descargas_quimicos.filter(estado='revertida')
        self.assertEqual(descargas_revertidas.count(), 1)
        self.assertEqual(
            descargas_revertidas.first().justificacion, 'Error en cálculo de peso, se corrige a 150 kg')
        self.assertEqual(orden.descargas_quimicos.filter(estado='aplicada').count(), 1)

    def test_eliminar_op_dado_sin_justificacion_cuando_elimina_entonces_400(self):
        resp_create = self._crear_op('OP-TDD-DEL1')
        op_id = resp_create.data['id']

        resp = self.client.delete(f'/api/ordenes-produccion/{op_id}/', format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_eliminar_op_dado_con_justificacion_cuando_elimina_entonces_registra_movimiento_devolucion(self):
        resp_create = self._crear_op('OP-TDD-DEL2')
        op_id = resp_create.data['id']

        resp = self.client.delete(
            f'/api/ordenes-produccion/{op_id}/', {'justificacion': 'OP errónea'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        movimientos_devolucion = MovimientoInventario.objects.filter(
            tipo_movimiento='DEVOLUCION', producto=self.quimico)
        self.assertGreater(movimientos_devolucion.count(), 0, "Debe existir MovimientoInventario DEVOLUCION")

    def test_stock_quimicos_endpoint_dado_stock_bajo_minimo_cuando_consulta_entonces_marca_alerta(self):
        """
        Migrado de tests_integrados.py::DescargaQuimicosOPTestCase (Fase 6.2): GET
        /api/ordenes-produccion/stock-quimicos/ marca alerta=true cuando cantidad < stock_minimo.
        """
        tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.quimico.stock_minimo = Decimal('5.00')
        self.quimico.save()
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico)
        stock.cantidad = Decimal('1.50')
        stock._justificacion_auditoria = 'Bajar stock bajo el mínimo para test'
        stock.save()

        self.client.force_authenticate(user=tintorero)
        resp = self.client.get(f'/api/ordenes-produccion/stock-quimicos/?sede_id={self.sede.id}')

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        stock_resp = next((s for s in resp.data if s['producto_id'] == self.quimico.id), None)
        self.assertIsNotNone(stock_resp)
        self.assertTrue(stock_resp['alerta'])
