from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import (
    Bodega,
    DetallePlanProduccion,
    LoteProduccion,
    OrdenProduccion,
    PlanProduccion,
    Producto,
)
from gestion.services.ejecucion_produccion import EjecucionProduccionService
from inventory.models import StockBodega
from inventory.services.reposicion_service import ReposicionService
from .factories import (
    AreaFactory,
    BodegaFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    DetallePlanProduccionFactory,
    LineaProduccionFactory,
    MaquinaFactory,
    PlanProduccionFactory,
    ProductoFactory,
    SedeFactory,
)


class ProduccionContraStockTestCase(TestCase):
    """
    Suite de pruebas para Producción Contra Stock (MTS), planes de reposición,
    control estricto de desviación (Caso 9 y Caso 13) y trazabilidad MES.
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede Textil Central")
        self.otra_sede = SedeFactory(nombre="Sede Periférica")
        self.area = AreaFactory(sede=self.sede, nombre="Tejeduría")
        self.linea = LineaProduccionFactory(area=self.area)
        self.maquina = MaquinaFactory(area=self.area)
        self.linea.maquinas.add(self.maquina)
        self.supervisor = CustomUserFactory(sede=self.sede)

        self.bodega_mp = BodegaFactory(sede=self.sede, nombre="Bodega Materia Prima")
        self.bodega_pt = BodegaFactory(sede=self.sede, nombre="Bodega Producto Terminado")

        self.prod_hilo = ProductoFactory(
            sede=self.sede,
            codigo="HILO-ALGODON-24-1",
            tipo="materia_prima",
            unidad_medida="kg",
            stock_minimo=Decimal('50.000'),
        )
        self.prod_tela = ProductoFactory(
            sede=self.sede,
            codigo="TELA-JERSEY-PREMIUM",
            tipo="tela",
            unidad_medida="kg",
            stock_minimo=Decimal('100.000'),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.supervisor)

    # -------------------------------------------------------------------------
    # 1. Validaciones del Modelo PlanProduccion y DetallePlanProduccion
    # -------------------------------------------------------------------------

    def test_plan_produccion_dado_fechas_invalidas_cuando_valida_entonces_lanza_validation_error(self):
        plan = PlanProduccion(
            codigo="PLAN-INVALID-01",
            sede=self.sede,
            fecha_inicio=date(2026, 6, 10),
            fecha_fin=date(2026, 6, 5),  # Fin anterior a Inicio
            estado="borrador",
            supervisor=self.supervisor,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.clean()
        self.assertIn('fecha_fin', ctx.exception.message_dict)

    def test_detalle_plan_dado_producto_de_otra_sede_cuando_valida_entonces_lanza_validation_error(self):
        plan = PlanProduccionFactory(sede=self.sede)
        prod_ajeno = ProductoFactory(sede=self.otra_sede, codigo="PROD-AJENO")

        detalle = DetallePlanProduccion(
            plan=plan,
            producto_objetivo=prod_ajeno,
            cantidad_planificada=Decimal('100.0000'),
        )
        with self.assertRaises(ValidationError) as ctx:
            detalle.clean()
        self.assertIn('producto_objetivo', ctx.exception.message_dict)

    def test_detalle_plan_dado_cantidad_invalida_cuando_valida_entonces_lanza_validation_error(self):
        plan = PlanProduccionFactory(sede=self.sede)
        detalle = DetallePlanProduccion(
            plan=plan,
            producto_objetivo=self.prod_tela,
            cantidad_planificada=Decimal('0.0000'),
        )
        with self.assertRaises(ValidationError):
            detalle.clean()

    # -------------------------------------------------------------------------
    # 2. Generación de Orden de Producción desde Plan
    # -------------------------------------------------------------------------

    def test_generar_orden_dado_plan_borrador_cuando_intenta_generar_entonces_rechaza_por_estado(self):
        plan = PlanProduccionFactory(sede=self.sede, estado='borrador')
        detalle = DetallePlanProduccionFactory(plan=plan, producto_objetivo=self.prod_tela)

        with self.assertRaises(ValidationError) as ctx:
            ReposicionService.generar_orden_desde_plan(detalle_plan=detalle, user=self.supervisor)
        self.assertIn("El plan debe estar 'Aprobado'", str(ctx.exception))

    def test_generar_orden_dado_plan_aprobado_cuando_genera_op_entonces_crea_op_con_saldo_y_pasa_a_en_ejecucion(self):
        plan = PlanProduccionFactory(sede=self.sede, estado='aprobado')
        detalle = DetallePlanProduccionFactory(
            plan=plan,
            producto_objetivo=self.prod_tela,
            cantidad_planificada=Decimal('500.0000'),
            cantidad_aceptada=Decimal('100.0000'),
            cantidad_ejecutada=Decimal('100.0000'),
            estado='en_proceso',
        )

        op = ReposicionService.generar_orden_desde_plan(
            detalle_plan=detalle,
            user=self.supervisor,
            bodega_salida=self.bodega_pt,
            prioridad='alta',
        )

        self.assertIsNotNone(op.pk)
        self.assertEqual(op.producto_salida, self.prod_tela)
        self.assertEqual(op.peso_neto_requerido, Decimal('400.00'))  # 500 - 100
        self.assertEqual(op.plan_produccion, plan)
        self.assertEqual(op.detalle_plan, detalle)
        self.assertEqual(op.prioridad, 'alta')

        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'en_ejecucion')

    # -------------------------------------------------------------------------
    # 3. Flujo MES: Avance Cualitativo/Cuantitativo y Desviación (Caso 9 y Caso 13)
    # -------------------------------------------------------------------------

    def test_actualizar_avance_dado_operacion_con_calidades_cuando_registra_entonces_actualiza_plan_correctamente(self):
        plan = PlanProduccionFactory(sede=self.sede, estado='aprobado')
        detalle = DetallePlanProduccionFactory(
            plan=plan,
            producto_objetivo=self.prod_tela,
            cantidad_planificada=Decimal('200.0000'),
        )

        op = ReposicionService.generar_orden_desde_plan(
            detalle_plan=detalle,
            user=self.supervisor,
            bodega_salida=self.bodega_pt,
        )

        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            orden_produccion=op,
            plan_produccion=plan,
            detalle_plan=detalle,
            modalidad='STOCK',
        )

        lote_mp = LoteProduccion.objects.create(
            producto=self.prod_hilo,
            codigo_lote="LOTE-HILO-MTS-01",
            peso_neto_producido=Decimal('200.000'),
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        StockBodega.objects.create(
            bodega=self.bodega_mp,
            producto=self.prod_hilo,
            lote=lote_mp,
            cantidad=Decimal('200.000'),
        )

        # Operación: Consumo 100 kg -> Salida Primera 85 kg, Salida Segunda 10 kg, Merma 5 kg
        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=corrida,
            operacion_data={
                'maquina': self.maquina,
                'operario': self.supervisor,
            },
            consumos_data=[{
                'producto': self.prod_hilo,
                'bodega_origen': self.bodega_mp,
                'lote_origen': lote_mp,
                'cantidad_consumida': Decimal('100.000'),
            }],
            salidas_data=[
                {
                    'producto': self.prod_tela,
                    'bodega_destino': self.bodega_pt,
                    'cantidad_neta': Decimal('85.000'),
                    'clasificacion_calidad': 'primera',
                },
                {
                    'producto': self.prod_tela,
                    'bodega_destino': self.bodega_pt,
                    'cantidad_neta': Decimal('10.000'),
                    'clasificacion_calidad': 'segunda',
                },
            ],
            mermas_data=[{
                'peso_merma': Decimal('5.000'),
                'tipo_merma': 'maquina',
            }],
            user=self.supervisor,
        )

        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_ejecutada, Decimal('95.0000'))
        self.assertEqual(detalle.cantidad_aceptada, Decimal('85.0000'))
        self.assertEqual(detalle.cantidad_segunda, Decimal('10.0000'))
        self.assertEqual(detalle.saldo_pendiente, Decimal('115.0000'))  # 200 - 85
        self.assertEqual(detalle.estado, 'en_proceso')
        self.assertEqual(detalle.cumplimiento_porcentaje, Decimal('42.50'))  # 85/200 * 100
        self.assertEqual(detalle.desviacion_porcentaje, Decimal('-52.50'))  # (95-200)/200 * 100

    def test_actualizar_avance_dado_sobreproduccion_cuando_supera_105_porciento_entonces_marca_sobreproducido(self):
        """Caso 9 / Caso 13: Desviación superior a la planificada (> 105%)."""
        plan = PlanProduccionFactory(sede=self.sede, estado='aprobado')
        detalle = DetallePlanProduccionFactory(
            plan=plan,
            producto_objetivo=self.prod_tela,
            cantidad_planificada=Decimal('100.0000'),
        )

        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            plan_produccion=plan,
            detalle_plan=detalle,
            modalidad='STOCK',
        )

        lote_mp = LoteProduccion.objects.create(
            producto=self.prod_hilo,
            codigo_lote="LOTE-HILO-MTS-OVER",
            peso_neto_producido=Decimal('150.000'),
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        StockBodega.objects.create(
            bodega=self.bodega_mp,
            producto=self.prod_hilo,
            lote=lote_mp,
            cantidad=Decimal('150.000'),
        )

        # Producir 110 kg de primera (110% de la meta)
        EjecucionProduccionService.registrar_operacion(
            corrida=corrida,
            operacion_data={
                'maquina': self.maquina,
                'operario': self.supervisor,
            },
            consumos_data=[{
                'producto': self.prod_hilo,
                'bodega_origen': self.bodega_mp,
                'lote_origen': lote_mp,
                'cantidad_consumida': Decimal('110.000'),
            }],
            salidas_data=[{
                'producto': self.prod_tela,
                'bodega_destino': self.bodega_pt,
                'cantidad_neta': Decimal('110.000'),
                'clasificacion_calidad': 'primera',
            }],
            mermas_data=[],
            user=self.supervisor,
        )

        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_aceptada, Decimal('110.0000'))
        self.assertEqual(detalle.estado, 'sobreproducido')
        self.assertEqual(detalle.desviacion_porcentaje, Decimal('10.00'))  # +10%
        self.assertEqual(detalle.saldo_pendiente, Decimal('0.0000'))

        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'cerrado')

    def test_revertir_operacion_dado_plan_vinculado_cuando_revierte_entonces_descuenta_cantidades_del_plan(self):
        plan = PlanProduccionFactory(sede=self.sede, estado='aprobado')
        detalle = DetallePlanProduccionFactory(
            plan=plan,
            producto_objetivo=self.prod_tela,
            cantidad_planificada=Decimal('100.0000'),
        )

        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            plan_produccion=plan,
            detalle_plan=detalle,
            modalidad='STOCK',
        )

        lote_mp = LoteProduccion.objects.create(
            producto=self.prod_hilo,
            codigo_lote="LOTE-REV-01",
            peso_neto_producido=Decimal('50.000'),
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        StockBodega.objects.create(
            bodega=self.bodega_mp,
            producto=self.prod_hilo,
            lote=lote_mp,
            cantidad=Decimal('50.000'),
        )

        op = EjecucionProduccionService.registrar_operacion(
            corrida=corrida,
            operacion_data={
                'maquina': self.maquina,
                'operario': self.supervisor,
            },
            consumos_data=[{
                'producto': self.prod_hilo,
                'bodega_origen': self.bodega_mp,
                'lote_origen': lote_mp,
                'cantidad_consumida': Decimal('50.000'),
            }],
            salidas_data=[{
                'producto': self.prod_tela,
                'bodega_destino': self.bodega_pt,
                'cantidad_neta': Decimal('48.000'),
                'clasificacion_calidad': 'primera',
            }],
            mermas_data=[{
                'peso_merma': Decimal('2.000'),
                'tipo_merma': 'maquina',
            }],
            user=self.supervisor,
        )

        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_aceptada, Decimal('48.0000'))

        # Revertir operación
        EjecucionProduccionService.revertir_operacion(
            operacion=op,
            user=self.supervisor,
            justificacion="Error en calibración de pesaje",
        )

        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_aceptada, Decimal('0.0000'))
        self.assertEqual(detalle.cantidad_ejecutada, Decimal('0.0000'))
        self.assertEqual(detalle.estado, 'pendiente')

    # -------------------------------------------------------------------------
    # 4. Análisis de Necesidades y Creación Automática de Plan desde Alertas
    # -------------------------------------------------------------------------

    def test_analizar_necesidades_dado_stock_bajo_minimo_cuando_analiza_entonces_detecta_deficit_agrupado(self):
        # prod_tela tiene stock_minimo=100.0000. Creemos stock actual de 30.0000 en 2 lotes
        lote1 = LoteProduccion.objects.create(
            producto=self.prod_tela,
            codigo_lote="LOTE-EXIST-01",
            peso_neto_producido=Decimal('10.000'),
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        lote2 = LoteProduccion.objects.create(
            producto=self.prod_tela,
            codigo_lote="LOTE-EXIST-02",
            peso_neto_producido=Decimal('20.000'),
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        StockBodega.objects.create(bodega=self.bodega_pt, producto=self.prod_tela, lote=lote1, cantidad=Decimal('10.000'))
        StockBodega.objects.create(bodega=self.bodega_pt, producto=self.prod_tela, lote=lote2, cantidad=Decimal('20.000'))

        necesidades = ReposicionService.analizar_necesidades_reposicion(sede_id=self.sede.id)
        self.assertTrue(len(necesidades) >= 1)

        item = next((n for n in necesidades if n['producto_id'] == self.prod_tela.id), None)
        self.assertIsNotNone(item)
        self.assertEqual(item['stock_actual'], Decimal('30.0000'))
        self.assertEqual(item['stock_minimo'], Decimal('100.0000'))
        self.assertEqual(item['deficit'], Decimal('70.0000'))

    def test_crear_plan_desde_alertas_dado_deficits_cuando_crea_plan_entonces_persiste_plan_con_detalles(self):
        deficits = [
            {'producto_id': self.prod_tela.id, 'deficit': Decimal('70.0000')},
            {'producto_id': self.prod_hilo.id, 'deficit': Decimal('35.0000')},
        ]
        plan = ReposicionService.crear_plan_desde_alertas(
            sede=self.sede,
            productos_deficit=deficits,
            supervisor=self.supervisor,
            aprobar_inmediatamente=True,
        )

        self.assertIsNotNone(plan.pk)
        self.assertEqual(plan.estado, 'aprobado')
        self.assertEqual(plan.detalles.count(), 2)

        det_tela = plan.detalles.get(producto_objetivo=self.prod_tela)
        self.assertEqual(det_tela.cantidad_planificada, Decimal('70.0000'))
        self.assertEqual(det_tela.estado, 'pendiente')

    # -------------------------------------------------------------------------
    # 5. Pruebas de Endpoints REST API
    # -------------------------------------------------------------------------

    def test_api_plan_produccion_dado_usuario_autenticado_cuando_flujo_completo_entonces_crea_aprueba_y_genera_op(self):
        # 1. Crear Plan
        create_payload = {
            'codigo': 'PLAN-REST-2026-001',
            'sede': self.sede.id,
            'fecha_inicio': (timezone.localdate()).isoformat(),
            'fecha_fin': (timezone.localdate() + timedelta(days=5)).isoformat(),
            'estado': 'borrador',
            'observaciones': 'Plan de reposición mensual',
        }
        res_create = self.client.post('/api/planes-produccion/', create_payload, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        plan_id = res_create.data['id']

        # Crear un detalle
        detalle = DetallePlanProduccion.objects.create(
            plan_id=plan_id,
            producto_objetivo=self.prod_tela,
            cantidad_planificada=Decimal('150.0000'),
        )

        # 2. Aprobar Plan
        res_aprobar = self.client.post(f'/api/planes-produccion/{plan_id}/aprobar/')
        self.assertEqual(res_aprobar.status_code, status.HTTP_200_OK)
        self.assertEqual(res_aprobar.data['estado'], 'aprobado')

        # 3. Generar Orden desde Plan
        gen_payload = {
            'detalle_plan_id': detalle.id,
            'bodega_salida_id': self.bodega_pt.id,
            'prioridad': 'urgente',
        }
        res_op = self.client.post(f'/api/planes-produccion/{plan_id}/generar-orden/', gen_payload, format='json')
        self.assertEqual(res_op.status_code, status.HTTP_201_CREATED)
        self.assertIn('orden_id', res_op.data)
        self.assertEqual(res_op.data['peso_neto_requerido'], '150.00')

        # 4. Verificar consulta de necesidades de reposición
        res_necesidades = self.client.get(f'/api/planes-produccion/necesidades-reposicion/?sede={self.sede.id}')
        self.assertEqual(res_necesidades.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res_necesidades.data, list)
