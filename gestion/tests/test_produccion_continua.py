from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import (
    CorridaProduccion,
    GenealogiaLote,
    LoteProduccion,
    OperacionProduccion,
    OrdenProduccion,
)
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    MaquinaFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    SedeFactory,
    StockBodegaFactory,
)
from inventory.models import MovimientoInventario, StockBodega


class ProduccionContinuaTestCase(TestCase):
    """
    Pruebas para Fase 3: Modalidad 1 - Producción Continua (Desacoplamiento OP y API MES).
    Convención ISTQB CTFL v4.0:
    test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede Producción Continua")
        self.area = AreaFactory(sede=self.sede, nombre="Área Tintorería Continua")
        self.maquina = MaquinaFactory(area=self.area, nombre="Rama Tensoras 01")
        self.bodega_origen = BodegaFactory(sede=self.sede, nombre="Bodega Tela Cruda")
        self.bodega_destino = BodegaFactory(sede=self.sede, nombre="Bodega Tela Terminada")

        self.supervisor = CustomUserFactory(sede=self.sede, username="supervisor_continua")
        self.operario = CustomUserFactory(sede=self.sede, username="operario_continua")

        self.producto_crudo = ProductoFactory(
            codigo="TEL-CRUD-01",
            tipo="producto_intermedio",
            sede=self.sede,
        )
        self.producto_acabado = ProductoFactory(
            codigo="TEL-ACAB-01",
            tipo="tela",
            sede=self.sede,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.supervisor)

        # Insumo de prueba con 1000 kg en stock
        self.lote_crudo = LoteProduccion.objects.create(
            producto=self.producto_crudo,
            codigo_lote="LOT-CRUD-TEST-01",
            peso_neto_producido=Decimal("1000.000"),
            operario=self.operario,
            maquina=self.maquina,
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        self.stock_crudo = StockBodegaFactory(
            bodega=self.bodega_origen,
            producto=self.producto_crudo,
            lote=self.lote_crudo,
            cantidad=Decimal("1000.000"),
        )

    def test_orden_dado_produccion_continua_cuando_se_crea_sin_peso_neto_entonces_persiste_correctamente(self):
        """
        GIVEN: Un escenario de producción continua o batch abierto donde el peso meta no se predefine
        WHEN: Se crea una OrdenProduccion con peso_neto_requerido=None
        THEN: Persiste en BD sin violar el CheckConstraint gestion_ordenproduccion_peso_neto_positivo
        """
        op = OrdenProduccion.objects.create(
            sede=self.sede,
            area=self.area,
            codigo="OP-CONT-001",
            producto_entrada=self.producto_crudo,
            producto_salida=self.producto_acabado,
            peso_neto_requerido=None,
            estado='en_proceso',
        )

        self.assertIsNotNone(op.pk)
        self.assertIsNone(op.peso_neto_requerido)
        self.assertEqual(op.codigo, "OP-CONT-001")

    def test_corrida_dado_parametros_validos_cuando_se_inicia_entonces_crea_corrida_activa(self):
        """
        GIVEN: Un supervisor autenticado en planta
        WHEN: Envía POST /api/corridas-produccion/iniciar-corrida/
        THEN: Retorna HTTP 201, estado='en_proceso' y genera código secuencial
        """
        payload = {
            'area_id': self.area.id,
            'maquina_principal_id': self.maquina.id,
            'modalidad': 'CONTINUA',
            'turno': 'Tarde',
            'observaciones': 'Inicio de turno continuo sin OP',
        }

        url = '/api/corridas-produccion/iniciar-corrida/'
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['modalidad'], 'CONTINUA')
        self.assertEqual(response.data['estado'], 'en_proceso')
        self.assertEqual(response.data['turno'], 'Tarde')
        self.assertTrue(response.data['codigo'].startswith('CORR-'))
        self.assertEqual(response.data['operaciones_count'], 0)

    def test_corrida_dado_operacion_continua_cuando_se_registra_operacion_entonces_actualiza_kardex_y_retorna_201(self):
        """
        GIVEN: Una corrida activa en planta
        WHEN: Se envía POST /api/corridas-produccion/{id}/registrar-operacion/
        THEN: Registra la transformación en máquina, actualiza StockBodega y emite Kardex
        """
        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            modalidad='CONTINUA',
            estado='en_proceso',
        )

        payload = {
            'maquina_id': self.maquina.id,
            'operario_id': self.operario.id,
            'observaciones': 'Acabado en rama continua',
            'consumos': [{
                'producto_id': self.producto_crudo.id,
                'bodega_origen_id': self.bodega_origen.id,
                'lote_origen_id': self.lote_crudo.id,
                'cantidad_consumida': '200.000',
            }],
            'salidas': [{
                'producto_id': self.producto_acabado.id,
                'bodega_destino_id': self.bodega_destino.id,
                'cantidad_neta': '190.000',
                'codigo_lote': 'LOT-RAMA-ACAB-01',
                'clasificacion_calidad': 'primera',
                'cantidad_metros': '570.0000',
            }],
            'mermas': [{
                'peso_merma': '10.000',
                'tipo_merma': 'corte',
            }],
        }

        url = f'/api/corridas-produccion/{corrida.id}/registrar-operacion/'
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], 'completada')
        self.assertEqual(response.data['numero_secuencia'], 1)

        # Verificar actualización de saldos
        self.stock_crudo.refresh_from_db()
        self.assertEqual(self.stock_crudo.cantidad, Decimal("800.000"))

        stock_acab = StockBodega.objects.get(
            bodega=self.bodega_destino,
            producto=self.producto_acabado,
            lote__codigo_lote='LOT-RAMA-ACAB-01',
        )
        self.assertEqual(stock_acab.cantidad, Decimal("190.000"))

    def test_corrida_dado_operacion_con_desbalance_cuando_se_registra_entonces_retorna_400(self):
        """
        GIVEN: Entrada de 200 kg y salida declarada de 150 kg (desbalance 50 kg)
        WHEN: Se envía POST /api/corridas-produccion/{id}/registrar-operacion/
        THEN: Retorna HTTP 400 Bad Request indicando desbalance de masa
        """
        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            modalidad='CONTINUA',
            estado='en_proceso',
        )

        payload = {
            'maquina_id': self.maquina.id,
            'operario_id': self.operario.id,
            'consumos': [{
                'producto_id': self.producto_crudo.id,
                'bodega_origen_id': self.bodega_origen.id,
                'lote_origen_id': self.lote_crudo.id,
                'cantidad_consumida': '200.000',
            }],
            'salidas': [{
                'producto_id': self.producto_acabado.id,
                'bodega_destino_id': self.bodega_destino.id,
                'cantidad_neta': '150.000',
                'codigo_lote': 'LOT-DESBAL-API-01',
            }],
        }

        url = f'/api/corridas-produccion/{corrida.id}/registrar-operacion/'
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Desbalance de masa detectado', str(response.data))

    def test_corrida_dado_corrida_en_proceso_cuando_se_finaliza_entonces_guarda_hora_fin_y_estado_finalizada(self):
        """
        GIVEN: Una corrida en estado 'en_proceso'
        WHEN: Se invoca POST /api/corridas-produccion/{id}/finalizar-corrida/
        THEN: Retorna HTTP 200 con estado='finalizada' y fecha_fin asignada
        """
        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            estado='en_proceso',
        )

        url = f'/api/corridas-produccion/{corrida.id}/finalizar-corrida/'
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'finalizada')
        self.assertIsNotNone(response.data['hora_fin'])

    def test_corrida_dado_corrida_activa_cuando_se_pausa_y_reanuda_entonces_alterna_estado(self):
        """
        GIVEN: Una corrida en proceso
        WHEN: Se invoca POST /api/corridas-produccion/{id}/pausar/ dos veces sucesivas
        THEN: Primero pasa a 'pausada' y luego retorna a 'en_proceso'
        """
        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            estado='en_proceso',
        )

        url = f'/api/corridas-produccion/{corrida.id}/pausar/'
        res1 = self.client.post(url, {}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['estado'], 'pausada')

        res2 = self.client.post(url, {}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['estado'], 'en_proceso')

    def test_corrida_dado_operacion_existente_cuando_se_solicita_reversion_entonces_restituye_stock(self):
        """
        GIVEN: Una corrida con una operación registrada que consumió 100 kg y produjo 95 kg
        WHEN: Se invoca POST /api/corridas-produccion/{id}/revertir-operacion/
        THEN: Retorna HTTP 200, marca la operación como 'revertida' y restaura saldos en bodega
        """
        corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            estado='en_proceso',
        )

        # Registrar operación previa
        from gestion.services.ejecucion_produccion import EjecucionProduccionService
        op = EjecucionProduccionService.registrar_operacion(
            corrida=corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=[{
                'producto': self.producto_crudo,
                'bodega_origen': self.bodega_origen,
                'cantidad_consumida': Decimal('100.000'),
                'lote_origen': self.lote_crudo,
            }],
            salidas_data=[{
                'producto': self.producto_acabado,
                'bodega_destino': self.bodega_destino,
                'cantidad_neta': Decimal('95.000'),
                'codigo_lote': 'LOT-REV-API-01',
            }],
            mermas_data=[{
                'peso_merma': Decimal('5.000'),
                'tipo_merma': 'maquina',
            }],
            user=self.operario,
        )

        # Solicitar reversión vía API
        url = f'/api/corridas-produccion/{corrida.id}/revertir-operacion/'
        payload = {
            'operacion_id': op.id,
            'justificacion': 'Error en la especificación de acabado del tejido',
        }
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'revertida')

        # Verificar restitución
        self.stock_crudo.refresh_from_db()
        self.assertEqual(self.stock_crudo.cantidad, Decimal("1000.000"))

    def test_corrida_dado_lote_con_genealogia_cuando_se_consulta_trazabilidad_entonces_retorna_grafo_dag(self):
        """
        GIVEN: Un lote hijo conectado a su lote padre mediante GenealogiaLote
        WHEN: Se invoca GET /api/corridas-produccion/trazabilidad-lote/?codigo=LOT-HIJO-01&direccion=atras
        THEN: Retorna HTTP 200 con estructura de grafo DAG completa
        """
        lote_hijo = LoteProduccion.objects.create(
            producto=self.producto_acabado,
            codigo_lote="LOT-HIJO-01",
            peso_neto_producido=Decimal("95.000"),
            operario=self.operario,
            maquina=self.maquina,
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        corrida = CorridaProduccionFactory(sede=self.sede, area=self.area)
        op = OperacionProduccion.objects.create(
            corrida=corrida,
            maquina=self.maquina,
            operario=self.operario,
            hora_inicio=timezone.now(),
            hora_fin=timezone.now(),
            estado='completada',
        )
        GenealogiaLote.objects.create(
            lote_padre=self.lote_crudo,
            lote_hijo=lote_hijo,
            operacion=op,
            cantidad_padre_usada=Decimal("100.000"),
        )

        url = '/api/corridas-produccion/trazabilidad-lote/?codigo=LOT-HIJO-01&direccion=atras'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nodo_raiz']['codigo_lote'], 'LOT-HIJO-01')
        self.assertEqual(response.data['total_ancestros'], 1)
        self.assertEqual(response.data['ancestros'][0]['codigo_lote'], self.lote_crudo.codigo_lote)
        self.assertEqual(len(response.data['aristas']), 1)
