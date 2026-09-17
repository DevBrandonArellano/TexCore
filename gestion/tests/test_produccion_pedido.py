from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import (
    Bodega,
    DetallePedido,
    LoteProduccion,
    OrdenProduccion,
    PedidoVenta,
    Producto,
)
from gestion.services.ejecucion_produccion import EjecucionProduccionService
from inventory.models import StockBodega
from inventory.services.despacho_reversion import DespachoReversionService
from inventory.services.reserva_service import ReservaService
from .factories import (
    AreaFactory,
    BodegaFactory,
    ClienteFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    DetallePedidoFactory,
    LineaProduccionFactory,
    LoteProduccionFactory,
    MaquinaFactory,
    PedidoVentaFactory,
    ProductoFactory,
    SedeFactory,
    StockBodegaFactory,
)


class ProduccionBajoPedidoMTOTestCase(TestCase):
    """
    Suite de pruebas para Producción Bajo Pedido (Make-to-Order / MTO),
    reserva inmutable de lotes, aislamiento de despacho comercial (Caso 10 y Caso 11)
    y trazabilidad integral en el motor MES.
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede Textil MTO")
        self.otra_sede = SedeFactory(nombre="Sede Externa")
        self.area = AreaFactory(sede=self.sede, nombre="Hilandería y Tejeduría")
        self.linea = LineaProduccionFactory(area=self.area)
        self.maquina = MaquinaFactory(area=self.area)
        self.linea.maquinas.add(self.maquina)

        self.supervisor = CustomUserFactory(
            sede=self.sede,
            groups=['admin_sistemas', 'vendedor', 'despacho']
        )
        self.cliente_a = ClienteFactory(sede=self.sede, nombre_razon_social="Textiles Andinos S.A.")
        self.cliente_b = ClienteFactory(sede=self.sede, nombre_razon_social="Confecciones del Norte Cía.")

        self.bodega_mp = BodegaFactory(sede=self.sede, nombre="Bodega Materia Prima MTO")
        self.bodega_pt = BodegaFactory(sede=self.sede, nombre="Bodega Producto Terminado MTO")

        self.prod_hilo = ProductoFactory(
            sede=self.sede,
            codigo="HILO-PEINADO-30-1",
            tipo="materia_prima",
            unidad_medida="kg",
        )
        self.prod_tela_mto = ProductoFactory(
            sede=self.sede,
            codigo="TELA-PIQUE-ESPECIAL-MTO",
            tipo="tela",
            unidad_medida="kg",
        )

        self.pedido_a = PedidoVentaFactory(
            sede=self.sede,
            cliente=self.cliente_a,
            guia_remision="GUIA-MTO-001",
            vendedor_asignado=self.supervisor,
            estado='pendiente',
        )
        self.detalle_a = DetallePedidoFactory(
            pedido_venta=self.pedido_a,
            producto=self.prod_tela_mto,
            peso=Decimal('100.000'),
            cantidad=10,
            piezas=10,
            precio_unitario=Decimal('12.500'),
            cantidad_fabricada=Decimal('0.000'),
            estado_fabricacion='pendiente',
        )

        self.pedido_b = PedidoVentaFactory(
            sede=self.sede,
            cliente=self.cliente_b,
            guia_remision="GUIA-MTO-002",
            vendedor_asignado=self.supervisor,
            estado='pendiente',
        )
        self.detalle_b = DetallePedidoFactory(
            pedido_venta=self.pedido_b,
            producto=self.prod_tela_mto,
            peso=Decimal('100.000'),
            cantidad=10,
            piezas=10,
            precio_unitario=Decimal('12.500'),
            cantidad_fabricada=Decimal('0.000'),
            estado_fabricacion='pendiente',
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.supervisor)

    # -------------------------------------------------------------------------
    # 1. Creación de Órdenes MTO (ReservaService.crear_orden_desde_pedido)
    # -------------------------------------------------------------------------

    def test_crear_orden_dado_detalle_pedido_valido_cuando_se_genera_orden_entonces_crea_op_vinculada_y_estado_en_proceso(self):
        op = ReservaService.crear_orden_desde_pedido(
            detalle_pedido=self.detalle_a,
            user=self.supervisor,
            bodega_salida=self.bodega_pt,
            prioridad='alta',
        )

        self.assertIsNotNone(op.pk)
        self.assertEqual(op.pedido_venta, self.pedido_a)
        self.assertEqual(op.detalle_pedido, self.detalle_a)
        self.assertEqual(op.producto_salida, self.prod_tela_mto)
        self.assertEqual(op.peso_neto_requerido, Decimal('100.00'))
        self.assertEqual(op.prioridad, 'alta')
        self.assertTrue(op.codigo.startswith(f"MTO-PED-{self.pedido_a.id}"))

        self.detalle_a.refresh_from_db()
        self.assertEqual(self.detalle_a.estado_fabricacion, 'en_proceso')

    def test_crear_orden_dado_pedido_anulado_cuando_se_genera_orden_entonces_lanza_validation_error(self):
        self.pedido_a.anulado = True
        self.pedido_a.save()

        with self.assertRaises(ValidationError) as ctx:
            ReservaService.crear_orden_desde_pedido(
                detalle_pedido=self.detalle_a,
                user=self.supervisor,
            )
        self.assertIn("No se pueden crear órdenes de producción para pedidos anulados", str(ctx.exception))

    def test_crear_orden_dado_pedido_ya_despachado_cuando_se_genera_orden_entonces_lanza_validation_error(self):
        self.pedido_a.estado = 'despachado'
        self.pedido_a.save()

        with self.assertRaises(ValidationError) as ctx:
            ReservaService.crear_orden_desde_pedido(
                detalle_pedido=self.detalle_a,
                user=self.supervisor,
            )
        self.assertIn("No se pueden generar órdenes para un pedido en estado", str(ctx.exception))

    def test_crear_orden_dado_detalle_completamente_fabricado_cuando_se_genera_orden_entonces_lanza_validation_error(self):
        self.detalle_a.cantidad_fabricada = Decimal('100.000')
        self.detalle_a.estado_fabricacion = 'fabricado'
        self.detalle_a.save()

        with self.assertRaises(ValidationError) as ctx:
            ReservaService.crear_orden_desde_pedido(
                detalle_pedido=self.detalle_a,
                user=self.supervisor,
            )
        self.assertIn("ya ha completado su requerimiento de fabricación", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 2. Reserva y Liberación de Lotes (ReservaService)
    # -------------------------------------------------------------------------

    def test_reserva_lote_dado_lote_conforme_cuando_se_reserva_para_pedido_entonces_compromete_stock_y_actualiza_pedido(self):
        now = timezone.now()
        lote = LoteProduccionFactory(
            codigo_lote="LOTE-MTO-TEST-01",
            peso_neto_producido=Decimal('60.000'),
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        stock = StockBodegaFactory(
            bodega=self.bodega_pt,
            producto=self.prod_tela_mto,
            lote=lote,
            cantidad=Decimal('60.000'),
            stock_comprometido=Decimal('0.000'),
        )

        ReservaService.reservar_lote_para_pedido(
            lote=lote,
            pedido=self.pedido_a,
            detalle_pedido=self.detalle_a,
            cantidad=Decimal('60.000'),
            user=self.supervisor,
        )

        lote.refresh_from_db()
        stock.refresh_from_db()
        self.detalle_a.refresh_from_db()

        self.assertEqual(lote.pedido_venta_reserva, self.pedido_a)
        self.assertEqual(stock.stock_comprometido, Decimal('60.000'))
        self.assertEqual(stock.stock_disponible, Decimal('0.000'))
        self.assertEqual(self.detalle_a.cantidad_fabricada, Decimal('60.000'))
        self.assertEqual(self.detalle_a.estado_fabricacion, 'en_proceso')
        self.assertEqual(self.detalle_a.saldo_pendiente_fabricacion, Decimal('40.000'))

    def test_reserva_lote_dado_lote_ya_reservado_a_otro_pedido_cuando_se_intenta_reservar_entonces_lanza_validation_error(self):
        now = timezone.now()
        lote = LoteProduccionFactory(
            codigo_lote="LOTE-MTO-RESERVADO",
            peso_neto_producido=Decimal('50.000'),
            pedido_venta_reserva=self.pedido_a,
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )

        with self.assertRaises(ValidationError) as ctx:
            ReservaService.reservar_lote_para_pedido(
                lote=lote,
                pedido=self.pedido_b,
                user=self.supervisor,
            )
        self.assertIn("ya está reservado para el Pedido", str(ctx.exception))

    def test_liberar_reserva_dado_lote_reservado_cuando_se_libera_reserva_entonces_restaura_stock_comprometido_y_saldo_pedido(self):
        now = timezone.now()
        lote = LoteProduccionFactory(
            codigo_lote="LOTE-MTO-LIBERABLE",
            peso_neto_producido=Decimal('50.000'),
            producto=self.prod_tela_mto,
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        stock = StockBodegaFactory(
            bodega=self.bodega_pt,
            producto=self.prod_tela_mto,
            lote=lote,
            cantidad=Decimal('50.000'),
            stock_comprometido=Decimal('0.000'),
        )

        ReservaService.reservar_lote_para_pedido(
            lote=lote,
            pedido=self.pedido_a,
            detalle_pedido=self.detalle_a,
            user=self.supervisor,
        )

        stock.refresh_from_db()
        self.assertEqual(stock.stock_comprometido, Decimal('50.000'))

        ReservaService.liberar_reserva_lote(
            lote=lote,
            user=self.supervisor,
            justificacion="Liberación para reasignación",
        )

        lote.refresh_from_db()
        stock.refresh_from_db()
        self.detalle_a.refresh_from_db()

        self.assertIsNone(lote.pedido_venta_reserva)
        self.assertEqual(stock.stock_comprometido, Decimal('0.000'))
        self.assertEqual(stock.stock_disponible, Decimal('50.000'))
        self.assertEqual(self.detalle_a.cantidad_fabricada, Decimal('0.000'))
        self.assertEqual(self.detalle_a.estado_fabricacion, 'pendiente')

    # -------------------------------------------------------------------------
    # 3. Flujo MES Make-to-Order E2E (Caso 10)
    # -------------------------------------------------------------------------

    def test_flujo_mto_completo_dado_corrida_pedido_cuando_se_registra_operacion_entonces_genera_lote_auto_reservado_y_comprometido(self):
        # 1. Crear Orden MTO desde detalle de pedido
        op_mto = ReservaService.crear_orden_desde_pedido(
            detalle_pedido=self.detalle_a,
            user=self.supervisor,
            bodega_salida=self.bodega_pt,
        )

        # 2. Inicializar Stock de Materia Prima
        now = timezone.now()
        lote_mp = LoteProduccionFactory(
            codigo_lote="LOTE-MP-IN-01",
            peso_neto_producido=Decimal('100.000'),
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        stock_mp = StockBodegaFactory(
            bodega=self.bodega_mp,
            producto=self.prod_hilo,
            lote=lote_mp,
            cantidad=Decimal('100.000'),
        )

        # 3. Crear Corrida MTO asociada a la OP y al Pedido
        corrida = CorridaProduccionFactory(
            codigo="CORR-MTO-001",
            sede=self.sede,
            area=self.area,
            linea=self.linea,
            maquina_principal=self.maquina,
            modalidad='PEDIDO',
            orden_produccion=op_mto,
            pedido_venta=self.pedido_a,
            turno='Mañana',
            supervisor=self.supervisor,
        )

        # 4. Registrar Operación con salida conforme de 100 kg
        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=corrida,
            operacion_data={
                'maquina_id': self.maquina.id,
                'operario_id': self.supervisor.id,
            },
            consumos_data=[{
                'producto_id': self.prod_hilo.id,
                'bodega_origen_id': self.bodega_mp.id,
                'lote_origen_id': lote_mp.id,
                'cantidad_consumida': Decimal('100.000'),
            }],
            salidas_data=[{
                'producto_id': self.prod_tela_mto.id,
                'bodega_destino_id': self.bodega_pt.id,
                'cantidad_neta': Decimal('100.000'),
                'codigo_lote': 'LOTE-MTO-OUT-100',
                'clasificacion_calidad': 'primera',
            }],
            mermas_data=[],
            user=self.supervisor,
        )

        self.assertEqual(operacion.salidas.count(), 1)
        salida = operacion.salidas.first()
        lote_generado = salida.lote_generado

        # Verificar que el lote quedó automáticamente reservado para el Pedido A
        self.assertIsNotNone(lote_generado)
        self.assertEqual(lote_generado.pedido_venta_reserva, self.pedido_a)

        # Verificar stock comprometido en StockBodega
        stock_pt = StockBodega.objects.get(lote=lote_generado, bodega=self.bodega_pt)
        self.assertEqual(stock_pt.cantidad, Decimal('100.000'))
        self.assertEqual(stock_pt.stock_comprometido, Decimal('100.000'))
        self.assertEqual(stock_pt.stock_disponible, Decimal('0.000'))

        # Verificar que el DetallePedido quedó con estado 'fabricado'
        self.detalle_a.refresh_from_db()
        self.assertEqual(self.detalle_a.cantidad_fabricada, Decimal('100.000'))
        self.assertEqual(self.detalle_a.estado_fabricacion, 'fabricado')
        self.assertEqual(self.detalle_a.saldo_pendiente_fabricacion, Decimal('0.000'))

    # -------------------------------------------------------------------------
    # 4. Aislamiento e Integridad en Despacho Comercial (Caso 11)
    # -------------------------------------------------------------------------

    def test_despacho_mto_aislamiento_dado_lote_reservado_cuando_se_intenta_despachar_a_otro_pedido_entonces_bloqueado(self):
        now = timezone.now()
        lote_reservado = LoteProduccionFactory(
            codigo_lote="LOTE-EXCLUSIVO-CLIENTE-A",
            peso_neto_producido=Decimal('100.000'),
            pedido_venta_reserva=self.pedido_a,
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        StockBodegaFactory(
            bodega=self.bodega_pt,
            producto=self.prod_tela_mto,
            lote=lote_reservado,
            cantidad=Decimal('100.000'),
            stock_comprometido=Decimal('100.000'),
        )

        # 1. Validación previa en ValidateLoteAPIView con pedido ajeno (Pedido B)
        resp_validate = self.client.post('/api/scanning/validate', {
            'code': lote_reservado.codigo_lote,
            'pedido_id': self.pedido_b.id,
        }, format='json')
        self.assertEqual(resp_validate.status_code, status.HTTP_200_OK)
        self.assertFalse(resp_validate.data.get('valid'))
        self.assertIn("está reservado para el Pedido", resp_validate.data.get('reason'))

        # 2. Intento de despacho en ProcessDespachoAPIView para Pedido B
        resp_despacho = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [self.pedido_b.id],
            'lotes': [lote_reservado.codigo_lote],
            'observaciones': 'Intento de despacho cruzado',
            'confirmar_incompleto': True,
        }, format='json')

        self.assertEqual(resp_despacho.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("está reservado exclusivamente para el Pedido", str(resp_despacho.data))

        # El stock comprometido debe permanecer intacto
        stock = StockBodega.objects.get(lote=lote_reservado, bodega=self.bodega_pt)
        self.assertEqual(stock.cantidad, Decimal('100.000'))
        self.assertEqual(stock.stock_comprometido, Decimal('100.000'))

    def test_despacho_mto_dado_lote_reservado_cuando_se_despacha_al_pedido_correcto_entonces_despacho_exitoso_y_decrementa_comprometido(self):
        now = timezone.now()
        lote_reservado = LoteProduccionFactory(
            codigo_lote="LOTE-CORRECTO-A",
            peso_neto_producido=Decimal('100.000'),
            pedido_venta_reserva=self.pedido_a,
            producto=self.prod_tela_mto,
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        # Asignar producto de salida a la orden de producción del lote para que el despacho identifique el producto
        op = lote_reservado.orden_produccion
        op.producto_salida = self.prod_tela_mto
        op.pedido_venta = self.pedido_a
        op.save()

        StockBodegaFactory(
            bodega=self.bodega_pt,
            producto=self.prod_tela_mto,
            lote=lote_reservado,
            cantidad=Decimal('100.000'),
            stock_comprometido=Decimal('100.000'),
        )

        # 1. Validar con pedido correcto
        resp_validate = self.client.post('/api/scanning/validate', {
            'code': lote_reservado.codigo_lote,
            'pedido_id': self.pedido_a.id,
        }, format='json')
        self.assertEqual(resp_validate.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_validate.data.get('valid'))
        self.assertEqual(resp_validate.data['lote']['reservado_para_pedido'], self.pedido_a.id)

        # 2. Despachar al Pedido A
        resp_despacho = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [self.pedido_a.id],
            'lotes': [lote_reservado.codigo_lote],
            'observaciones': 'Despacho legítimo MTO',
            'confirmar_incompleto': True,
        }, format='json')

        self.assertEqual(resp_despacho.status_code, status.HTTP_200_OK)

        # El stock debe haber quedado en 0 y el stock_comprometido en 0
        stock = StockBodega.objects.get(lote=lote_reservado, bodega=self.bodega_pt)
        self.assertEqual(stock.cantidad, Decimal('0.000'))
        self.assertEqual(stock.stock_comprometido, Decimal('0.000'))

    # -------------------------------------------------------------------------
    # 5. Reversión de Operación MES y Reversión de Despacho MTO
    # -------------------------------------------------------------------------

    def test_reversion_operacion_mto_dado_lote_reservado_cuando_se_revierte_operacion_entonces_libera_reserva_y_restaura_pedido(self):
        op_mto = ReservaService.crear_orden_desde_pedido(
            detalle_pedido=self.detalle_a,
            user=self.supervisor,
            bodega_salida=self.bodega_pt,
        )

        now = timezone.now()
        lote_mp = LoteProduccionFactory(
            codigo_lote="LOTE-MP-REV-01",
            peso_neto_producido=Decimal('50.000'),
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        StockBodegaFactory(
            bodega=self.bodega_mp,
            producto=self.prod_hilo,
            lote=lote_mp,
            cantidad=Decimal('50.000'),
        )

        corrida = CorridaProduccionFactory(
            codigo="CORR-MTO-REV-001",
            sede=self.sede,
            area=self.area,
            linea=self.linea,
            maquina_principal=self.maquina,
            modalidad='PEDIDO',
            orden_produccion=op_mto,
            pedido_venta=self.pedido_a,
            turno='Mañana',
            supervisor=self.supervisor,
        )

        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=corrida,
            operacion_data={
                'maquina_id': self.maquina.id,
                'operario_id': self.supervisor.id,
            },
            consumos_data=[{
                'producto_id': self.prod_hilo.id,
                'bodega_origen_id': self.bodega_mp.id,
                'lote_origen_id': lote_mp.id,
                'cantidad_consumida': Decimal('50.000'),
            }],
            salidas_data=[{
                'producto_id': self.prod_tela_mto.id,
                'bodega_destino_id': self.bodega_pt.id,
                'cantidad_neta': Decimal('50.000'),
                'codigo_lote': 'LOTE-MTO-REV-OUT',
                'clasificacion_calidad': 'primera',
            }],
            mermas_data=[],
            user=self.supervisor,
        )

        self.detalle_a.refresh_from_db()
        self.assertEqual(self.detalle_a.cantidad_fabricada, Decimal('50.000'))

        # Revertir la operación
        EjecucionProduccionService.revertir_operacion(
            operacion=operacion,
            user=self.supervisor,
            justificacion="Defecto de hilado detectado tras tejeduría",
        )

        operacion.refresh_from_db()
        self.assertEqual(operacion.estado, 'revertida')

        salida = operacion.salidas.first()
        lote_gen = salida.lote_generado
        lote_gen.refresh_from_db()
        self.assertIsNone(lote_gen.pedido_venta_reserva)

        stock_salida = StockBodega.objects.get(lote=lote_gen, bodega=self.bodega_pt)
        self.assertEqual(stock_salida.cantidad, Decimal('0.000'))
        self.assertEqual(stock_salida.stock_comprometido, Decimal('0.000'))

        self.detalle_a.refresh_from_db()
        self.assertEqual(self.detalle_a.cantidad_fabricada, Decimal('0.000'))
        self.assertEqual(self.detalle_a.estado_fabricacion, 'pendiente')

    def test_reversion_despacho_mto_dado_lote_reservado_cuando_se_revierte_despacho_entonces_restituye_stock_comprometido(self):
        now = timezone.now()
        lote_reservado = LoteProduccionFactory(
            codigo_lote="LOTE-DESP-REV-A",
            peso_neto_producido=Decimal('100.000'),
            pedido_venta_reserva=self.pedido_a,
            hora_inicio=now,
            hora_final=now,
            maquina=self.maquina,
        )
        op = lote_reservado.orden_produccion
        op.producto_salida = self.prod_tela_mto
        op.pedido_venta = self.pedido_a
        op.save()

        StockBodegaFactory(
            bodega=self.bodega_pt,
            producto=self.prod_tela_mto,
            lote=lote_reservado,
            cantidad=Decimal('100.000'),
            stock_comprometido=Decimal('100.000'),
        )

        # 1. Despachar
        resp_despacho = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [self.pedido_a.id],
            'lotes': [lote_reservado.codigo_lote],
            'observaciones': 'Despacho a revertir',
            'confirmar_incompleto': True,
        }, format='json')
        self.assertEqual(resp_despacho.status_code, status.HTTP_200_OK)
        historial_id = resp_despacho.data['despacho_id']

        # 2. Revertir despacho
        resp_revert = self.client.post(f'/api/inventory/historial-despachos/{historial_id}/revertir/', {
            'justificacion': 'Camión de transporte accidentado, retorno a planta',
        }, format='json')
        self.assertEqual(resp_revert.status_code, status.HTTP_200_OK)

        # Verificar que el stock y el stock_comprometido vuelven a estar comprometidos para Pedido A
        stock = StockBodega.objects.get(lote=lote_reservado, bodega=self.bodega_pt)
        self.assertEqual(stock.cantidad, Decimal('100.000'))
        self.assertEqual(stock.stock_comprometido, Decimal('100.000'))
        self.assertEqual(stock.stock_disponible, Decimal('0.000'))

    # -------------------------------------------------------------------------
    # 6. Endpoint API Generar Orden MTO (/api/pedidos-venta/{id}/generar-orden-mto/)
    # -------------------------------------------------------------------------

    def test_endpoint_generar_orden_mto_dado_detalle_valido_cuando_se_invoca_api_entonces_retorna_201_y_op_generada(self):
        url = f"/api/pedidos-venta/{self.pedido_a.id}/generar-orden-mto/"
        resp = self.client.post(url, {
            'detalle_pedido_id': self.detalle_a.id,
            'prioridad': 'urgente',
            'peso_solicitado': '100.000',
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('orden_id', resp.data)
        self.assertTrue(resp.data['codigo'].startswith(f"MTO-PED-{self.pedido_a.id}"))
        self.assertEqual(resp.data['peso_neto_requerido'], '100.00')

        op = OrdenProduccion.objects.get(pk=resp.data['orden_id'])
        self.assertEqual(op.pedido_venta, self.pedido_a)
        self.assertEqual(op.prioridad, 'urgente')
