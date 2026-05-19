from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from gestion.tests.factories import (
    CustomUserFactory, SedeFactory, ProductoFactory, 
    FormulaColorFactory, BodegaFactory, AreaFactory,
    FaseRecetaFactory, DetalleFormulaFactory
)
from gestion.models import OrdenProduccion, DescargaQuimicoOP
from inventory.models import StockBodega
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
            concentracion_gr_l=Decimal('10.00'), # 10 gr/L
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
        self.assertEqual(stock_final := stock_descontado, Decimal('90.00'))

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
