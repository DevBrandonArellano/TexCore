from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestion.models import (
    CorridaProduccion,
    GenealogiaLote,
    LoteProduccion,
    MateriaPrimaLote,
    OperacionProduccion,
)
from gestion.services.ejecucion_produccion import EjecucionProduccionService
from gestion.services.genealogia_service import GenealogiaService
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    ClienteFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    MaquinaFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    ProveedorFactory,
    SedeFactory,
    StockBodegaFactory,
)
from inventory.models import (
    DetalleHistorialDespacho,
    DetalleHistorialDespachoPedido,
    HistorialDespacho,
    MovimientoInventario,
    StockBodega,
)


class EjecucionProduccionServiceTestCase(TestCase):
    """
    Pruebas unitarias y de integración para el Motor MES (EjecucionProduccionService y GenealogiaService).
    Convención ISTQB CTFL v4.0:
    test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede MES Test")
        self.area = AreaFactory(sede=self.sede, nombre="Área Hilatura")
        self.bodega_origen = BodegaFactory(sede=self.sede, nombre="Bodega Fibras")
        self.bodega_destino = BodegaFactory(sede=self.sede, nombre="Bodega Hilos PT")
        self.bodega_subproducto = BodegaFactory(sede=self.sede, nombre="Bodega Desperdicios")

        self.maquina = MaquinaFactory(area=self.area, nombre="Hiladora Vortex 01")
        self.operario = CustomUserFactory(sede=self.sede, username="operario_mes")
        self.supervisor = CustomUserFactory(sede=self.sede, username="supervisor_mes")

        self.producto_fibra = ProductoFactory(
            codigo="FIB-ALGODON",
            descripcion="Fibra de Algodón Peinado",
            tipo="materia_prima",
            sede=self.sede,
        )
        self.producto_hilo = ProductoFactory(
            codigo="HIL-24-1",
            descripcion="Hilo 24/1 Algodón",
            tipo="hilo",
            sede=self.sede,
        )
        self.producto_borra = ProductoFactory(
            codigo="SUB-BORRA",
            descripcion="Borra de Algodón Recuperable",
            tipo="subproducto",
            sede=self.sede,
        )

        self.corrida = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            maquina_principal=self.maquina,
            modalidad="CONTINUA",
            turno="Mañana",
            supervisor=self.supervisor,
            codigo="CORR-2026-001",
        )

        # Lote de entrada con 500 kg en stock
        self.lote_entrada = LoteProduccion.objects.create(
            producto=self.producto_fibra,
            codigo_lote="LOT-FIBRA-ORIGEN-01",
            peso_neto_producido=Decimal("500.000"),
            operario=self.operario,
            maquina=self.maquina,
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        self.stock_origen = StockBodegaFactory(
            bodega=self.bodega_origen,
            producto=self.producto_fibra,
            lote=self.lote_entrada,
            cantidad=Decimal("500.000"),
        )

    def test_operacion_dado_insumos_y_salida_balanceados_cuando_se_registra_entonces_persiste_y_descuenta_inventario_correctamente(self):
        """
        GIVEN: Un lote de entrada con 500 kg en stock
        WHEN: Se registra una operación con 100 kg consumo, 95 kg salida y 5 kg merma
        THEN: Descuenta stock de origen, incrementa stock de destino, crea movimientos y arista DAG
        """
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
            'costo_unitario': Decimal("2.500"),
        }]
        salidas = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("95.000"),
            'codigo_lote': "LOT-HIL-001",
            'clasificacion_calidad': "primera",
            'peso_bruto': Decimal("96.000"),
            'tara': Decimal("1.000"),
            'unidades_empaque': 15,
        }]
        mermas = [{
            'peso_merma': Decimal("5.000"),
            'tipo_merma': "maquina",
            'es_subproducto_vendible': False,
        }]

        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos,
            salidas_data=salidas,
            mermas_data=mermas,
            user=self.operario,
        )

        self.assertEqual(operacion.estado, 'completada')
        self.assertEqual(operacion.numero_secuencia, 1)

        # Verificar saldo origen (500 - 100 = 400)
        self.stock_origen.refresh_from_db()
        self.assertEqual(self.stock_origen.cantidad, Decimal("400.000"))

        # Verificar stock destino generado (95 kg)
        stock_dest = StockBodega.objects.get(
            bodega=self.bodega_destino,
            producto=self.producto_hilo,
            lote__codigo_lote="LOT-HIL-001",
        )
        self.assertEqual(stock_dest.cantidad, Decimal("95.000"))

        # Verificar movimientos Kardex
        mov_consumo = MovimientoInventario.objects.filter(tipo_movimiento='CONSUMO').first()
        self.assertIsNotNone(mov_consumo)
        self.assertEqual(mov_consumo.cantidad, Decimal("100.000"))
        self.assertEqual(mov_consumo.saldo_resultante, Decimal("400.000"))

        mov_prod = MovimientoInventario.objects.filter(tipo_movimiento='PRODUCCION').first()
        self.assertIsNotNone(mov_prod)
        self.assertEqual(mov_prod.cantidad, Decimal("95.000"))

        mov_merma = MovimientoInventario.objects.filter(tipo_movimiento='MERMA').first()
        self.assertIsNotNone(mov_merma)
        self.assertEqual(mov_merma.cantidad, Decimal("5.000"))

        # Verificar arista DAG en GenealogiaLote
        genealogia = GenealogiaLote.objects.filter(
            lote_padre=self.lote_entrada,
            lote_hijo__codigo_lote="LOT-HIL-001",
        ).first()
        self.assertIsNotNone(genealogia)
        self.assertEqual(genealogia.cantidad_padre_usada, Decimal("100.000"))

    def test_operacion_dado_desbalance_de_masa_cuando_se_registra_entonces_lanza_validation_error(self):
        """
        GIVEN: Entrada de 100 kg
        WHEN: Salida + Merma suman 85 kg (desbalance de 15 kg > tolerancia 0.050 kg)
        THEN: Se lanza ValidationError y el stock queda intacto
        """
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("80.000"),
            'codigo_lote': "LOT-DESBAL-01",
        }]
        mermas = [{
            'peso_merma': Decimal("5.000"),
            'tipo_merma': "maquina",
        }]

        with self.assertRaises(ValidationError) as ctx:
            EjecucionProduccionService.registrar_operacion(
                corrida=self.corrida,
                operacion_data={'maquina': self.maquina, 'operario': self.operario},
                consumos_data=consumos,
                salidas_data=salidas,
                mermas_data=mermas,
                user=self.operario,
            )

        self.assertIn("Desbalance de masa detectado", str(ctx.exception))
        self.stock_origen.refresh_from_db()
        self.assertEqual(self.stock_origen.cantidad, Decimal("500.000"))
        self.assertFalse(LoteProduccion.objects.filter(codigo_lote="LOT-DESBAL-01").exists())

    def test_operacion_dado_stock_insuficiente_cuando_se_registra_entonces_lanza_validation_error(self):
        """
        GIVEN: Saldo disponible de 500 kg
        WHEN: Se intenta consumir 600 kg
        THEN: Lanza ValidationError indicando stock insuficiente
        """
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("600.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("600.000"),
            'codigo_lote': "LOT-FAIL-01",
        }]

        with self.assertRaises(ValidationError) as ctx:
            EjecucionProduccionService.registrar_operacion(
                corrida=self.corrida,
                operacion_data={'maquina': self.maquina, 'operario': self.operario},
                consumos_data=consumos,
                salidas_data=salidas,
                user=self.operario,
            )

        self.assertIn("Stock insuficiente", str(ctx.exception))

    def test_operacion_dado_merma_vendible_cuando_se_registra_entonces_ingresa_stock_de_subproducto(self):
        """
        GIVEN: Consumo de 100 kg con 85 kg PT y 15 kg de borra vendible
        WHEN: Se registra la operación con es_subproducto_vendible=True
        THEN: Ingresa stock de subproducto en Bodega Desperdicios con MovimientoInventario PRODUCCION
        """
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("85.000"),
            'codigo_lote': "LOT-HIL-SUB-01",
        }]
        mermas = [{
            'peso_merma': Decimal("15.000"),
            'tipo_merma': "maquina",
            'es_subproducto_vendible': True,
            'producto_subproducto': self.producto_borra,
            'bodega_subproducto': self.bodega_subproducto,
        }]

        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos,
            salidas_data=salidas,
            mermas_data=mermas,
            user=self.operario,
        )

        stock_sub = StockBodega.objects.get(
            bodega=self.bodega_subproducto,
            producto=self.producto_borra,
        )
        self.assertEqual(stock_sub.cantidad, Decimal("15.000"))

        mov_sub = MovimientoInventario.objects.filter(
            producto=self.producto_borra,
            bodega_destino=self.bodega_subproducto,
            tipo_movimiento='PRODUCCION',
        ).first()
        self.assertIsNotNone(mov_sub)
        self.assertEqual(mov_sub.cantidad, Decimal("15.000"))

    def test_operacion_dado_mezcla_multiple_cuando_se_registra_entonces_crea_aristas_genealogicas_proporcionales(self):
        """
        GIVEN: Dos lotes insumo A (60 kg) y B (40 kg)
        WHEN: Se mezclan para producir lote C (98 kg) + 2 kg merma
        THEN: Crea 2 aristas dirigidas en GenealogiaLote con cantidad usada exacta de cada padre
        """
        lote_b = LoteProduccion.objects.create(
            producto=self.producto_fibra,
            codigo_lote="LOT-FIBRA-ORIGEN-02",
            peso_neto_producido=Decimal("200.000"),
            operario=self.operario,
            maquina=self.maquina,
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        StockBodegaFactory(
            bodega=self.bodega_origen,
            producto=self.producto_fibra,
            lote=lote_b,
            cantidad=Decimal("200.000"),
        )

        consumos = [
            {
                'producto': self.producto_fibra,
                'bodega_origen': self.bodega_origen,
                'cantidad_consumida': Decimal("60.000"),
                'lote_origen': self.lote_entrada,
            },
            {
                'producto': self.producto_fibra,
                'bodega_origen': self.bodega_origen,
                'cantidad_consumida': Decimal("40.000"),
                'lote_origen': lote_b,
            },
        ]
        salidas = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("98.000"),
            'codigo_lote': "LOT-HIL-MEZCLA-01",
        }]
        mermas = [{
            'peso_merma': Decimal("2.000"),
            'tipo_merma': "maquina",
        }]

        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos,
            salidas_data=salidas,
            mermas_data=mermas,
            user=self.operario,
        )

        aristas = GenealogiaLote.objects.filter(lote_hijo__codigo_lote="LOT-HIL-MEZCLA-01")
        self.assertEqual(aristas.count(), 2)

        arista_a = aristas.get(lote_padre=self.lote_entrada)
        self.assertEqual(arista_a.cantidad_padre_usada, Decimal("60.000"))

        arista_b = aristas.get(lote_padre=lote_b)
        self.assertEqual(arista_b.cantidad_padre_usada, Decimal("40.000"))

    def test_operacion_dado_division_un_lote_a_multiples_cuando_se_registra_entonces_crea_grafo_split(self):
        """
        GIVEN: Un lote insumo de 100 kg
        WHEN: Se divide en Lote C1 (50 kg primera) y Lote C2 (45 kg segunda) + 5 kg merma
        THEN: El lote padre queda conectado a ambos lotes hijos en GenealogiaLote proporcionalmente
        """
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas = [
            {
                'producto': self.producto_hilo,
                'bodega_destino': self.bodega_destino,
                'cantidad_neta': Decimal("50.000"),
                'codigo_lote': "LOT-SPLIT-C1",
                'clasificacion_calidad': "primera",
            },
            {
                'producto': self.producto_hilo,
                'bodega_destino': self.bodega_destino,
                'cantidad_neta': Decimal("45.000"),
                'codigo_lote': "LOT-SPLIT-C2",
                'clasificacion_calidad': "segunda",
            },
        ]
        mermas = [{
            'peso_merma': Decimal("5.000"),
            'tipo_merma': "maquina",
        }]

        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos,
            salidas_data=salidas,
            mermas_data=mermas,
            user=self.operario,
        )

        aristas = GenealogiaLote.objects.filter(lote_padre=self.lote_entrada)
        self.assertEqual(aristas.count(), 2)
        hijos_codigos = set(a.lote_hijo.codigo_lote for a in aristas)
        self.assertEqual(hijos_codigos, {"LOT-SPLIT-C1", "LOT-SPLIT-C2"})

    def test_operacion_dado_operacion_completada_cuando_se_revierte_entonces_restaura_saldos_y_marca_revertida(self):
        """
        GIVEN: Una operación confirmada que consumió 100 kg y produjo 95 kg
        WHEN: Se ejecuta revertir_operacion() con justificación
        THEN: Restaura los 100 kg a bodega de origen, descuenta los 95 kg de destino, emite contrasientos y marca 'revertida'
        """
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("95.000"),
            'codigo_lote': "LOT-REV-01",
        }]
        mermas = [{
            'peso_merma': Decimal("5.000"),
            'tipo_merma': "maquina",
        }]

        operacion = EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos,
            salidas_data=salidas,
            mermas_data=mermas,
            user=self.operario,
        )

        # Ejecutar reversión
        op_revertida = EjecucionProduccionService.revertir_operacion(
            operacion=operacion,
            user=self.supervisor,
            justificacion="Error de calibración en celda de pesaje",
        )

        self.assertEqual(op_revertida.estado, 'revertida')
        self.assertEqual(op_revertida.motivo_reversion, "Error de calibración en celda de pesaje")

        # Saldos restaurados
        self.stock_origen.refresh_from_db()
        self.assertEqual(self.stock_origen.cantidad, Decimal("500.000"))

        stock_dest = StockBodega.objects.get(
            bodega=self.bodega_destino,
            producto=self.producto_hilo,
            lote__codigo_lote="LOT-REV-01",
        )
        self.assertEqual(stock_dest.cantidad, Decimal("0.000"))

        # Contrasientos Kardex
        mov_dev = MovimientoInventario.objects.filter(tipo_movimiento='DEVOLUCION').first()
        self.assertIsNotNone(mov_dev)
        self.assertEqual(mov_dev.cantidad, Decimal("100.000"))

        mov_ajuste = MovimientoInventario.objects.filter(tipo_movimiento='AJUSTE').first()
        self.assertIsNotNone(mov_ajuste)
        self.assertEqual(mov_ajuste.cantidad, Decimal("95.000"))

        # Aristas DAG eliminadas
        self.assertFalse(GenealogiaLote.objects.filter(operacion=operacion).exists())

    def test_operacion_dado_lote_hijo_ya_transformado_cuando_se_intenta_revertir_entonces_rechaza_reversion(self):
        """
        GIVEN: Operación 1 que produjo el Lote X, y Operación 2 que consumió el Lote X
        WHEN: Se intenta revertir la Operación 1
        THEN: Lanza ValidationError impidiendo romper la integridad histórica del grafo
        """
        # Op 1: Fibra -> Hilo (LOT-X)
        consumos_1 = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas_1 = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("95.000"),
            'codigo_lote': "LOT-X-INTERMEDIO",
        }]
        mermas_1 = [{
            'peso_merma': Decimal("5.000"),
            'tipo_merma': "maquina",
        }]

        op_1 = EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos_1,
            salidas_data=salidas_1,
            mermas_data=mermas_1,
            user=self.operario,
        )
        lote_x = LoteProduccion.objects.get(codigo_lote="LOT-X-INTERMEDIO")

        # Op 2: Hilo (LOT-X) -> Hilo Retorcido (LOT-Y)
        consumos_2 = [{
            'producto': self.producto_hilo,
            'bodega_origen': self.bodega_destino,
            'cantidad_consumida': Decimal("95.000"),
            'lote_origen': lote_x,
        }]
        salidas_2 = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("93.000"),
            'codigo_lote': "LOT-Y-FINAL",
        }]
        mermas_2 = [{
            'peso_merma': Decimal("2.000"),
            'tipo_merma': "maquina",
        }]

        EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos_2,
            salidas_data=salidas_2,
            mermas_data=mermas_2,
            user=self.operario,
        )

        # Intento de revertir Op 1 debe fallar
        with self.assertRaises(ValidationError) as ctx:
            EjecucionProduccionService.revertir_operacion(
                operacion=op_1,
                user=self.supervisor,
                justificacion="Intento de anular operación inicial",
            )

        self.assertIn("ya fue transformado en operaciones productivas posteriores", str(ctx.exception))

    def test_genealogia_dado_cadena_productiva_cuando_se_consulta_hacia_atras_entonces_retorna_ancestros_y_materias_primas(self):
        """
        GIVEN: Cadena MP Proveedor -> Lote Fibra -> Lote Hilo -> Lote Tela
        WHEN: Se invoca GenealogiaService.obtener_trazabilidad_hacia_atras() desde Lote Tela
        THEN: Retorna todos los ancestros y localiza la materia prima original del proveedor
        """
        proveedor = ProveedorFactory(sede=self.sede, nombre="Fibras del Pacífico")
        mp = MateriaPrimaLote.objects.create(
            sede=self.sede,
            proveedor=proveedor,
            producto=self.producto_fibra,
            bodega_recepcion=self.bodega_origen,
            lote_proveedor="PROV-FIB-999",
            fecha_recepcion=timezone.now().date(),
            cantidad_kg=Decimal("1000.000"),
            costo_unitario=Decimal("2.200"),
            numero_documento_entrada="GUIA-00123",
        )
        self.lote_entrada.materia_prima_lote = mp
        self.lote_entrada.save()

        # Op 1: Fibra -> Hilo
        consumos_1 = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas_1 = [{
            'producto': self.producto_hilo,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("95.000"),
            'codigo_lote': "LOT-HIL-TRACE",
        }]
        mermas_1 = [{
            'peso_merma': Decimal("5.000"),
            'tipo_merma': "maquina",
        }]
        EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos_1,
            salidas_data=salidas_1,
            mermas_data=mermas_1,
            user=self.operario,
        )
        lote_hilo = LoteProduccion.objects.get(codigo_lote="LOT-HIL-TRACE")

        # Op 2: Hilo -> Tela
        producto_tela = ProductoFactory(codigo="TEL-PIQUE", tipo="tela", sede=self.sede)
        consumos_2 = [{
            'producto': self.producto_hilo,
            'bodega_origen': self.bodega_destino,
            'cantidad_consumida': Decimal("95.000"),
            'lote_origen': lote_hilo,
        }]
        salidas_2 = [{
            'producto': producto_tela,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("92.000"),
            'codigo_lote': "LOT-TELA-TRACE",
        }]
        mermas_2 = [{
            'peso_merma': Decimal("3.000"),
            'tipo_merma': "maquina",
        }]
        EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos_2,
            salidas_data=salidas_2,
            mermas_data=mermas_2,
            user=self.operario,
        )
        lote_tela = LoteProduccion.objects.get(codigo_lote="LOT-TELA-TRACE")

        # Consulta Trace-Back
        trazabilidad = GenealogiaService.obtener_trazabilidad_hacia_atras(lote_tela)

        self.assertEqual(trazabilidad['nodo_raiz']['codigo_lote'], "LOT-TELA-TRACE")
        self.assertEqual(trazabilidad['total_ancestros'], 2)
        codigos_ancestros = [a['codigo_lote'] for a in trazabilidad['ancestros']]
        self.assertIn("LOT-HIL-TRACE", codigos_ancestros)
        self.assertIn("LOT-FIBRA-ORIGEN-01", codigos_ancestros)

        self.assertEqual(trazabilidad['total_materias_primas'], 1)
        mp_info = trazabilidad['materias_primas_origen'][0]
        self.assertEqual(mp_info['lote_proveedor'], "PROV-FIB-999")
        self.assertEqual(mp_info['proveedor_nombre'], "Fibras del Pacífico")
        self.assertEqual(mp_info['numero_documento_entrada'], "GUIA-00123")

    def test_genealogia_dado_lote_con_despacho_cuando_se_consulta_hacia_adelante_entonces_retorna_descendientes_y_clientes_afectados(self):
        """
        GIVEN: Lote de hilo transformado en tela y despachado al Cliente ABC
        WHEN: Se ejecuta GenealogiaService.obtener_trazabilidad_hacia_adelante() desde el lote de hilo
        THEN: Localiza la tela producida y reporta el cliente y pedido despachado (Recall)
        """
        # Producción de Tela desde Hilo
        producto_tela = ProductoFactory(codigo="TEL-JERSEY", tipo="tela", sede=self.sede)
        consumos = [{
            'producto': self.producto_fibra,
            'bodega_origen': self.bodega_origen,
            'cantidad_consumida': Decimal("100.000"),
            'lote_origen': self.lote_entrada,
        }]
        salidas = [{
            'producto': producto_tela,
            'bodega_destino': self.bodega_destino,
            'cantidad_neta': Decimal("96.000"),
            'codigo_lote': "LOT-TEL-DESPACHO-01",
        }]
        mermas = [{
            'peso_merma': Decimal("4.000"),
            'tipo_merma': "maquina",
        }]
        EjecucionProduccionService.registrar_operacion(
            corrida=self.corrida,
            operacion_data={'maquina': self.maquina, 'operario': self.operario},
            consumos_data=consumos,
            salidas_data=salidas,
            mermas_data=mermas,
            user=self.operario,
        )
        lote_tela = LoteProduccion.objects.get(codigo_lote="LOT-TEL-DESPACHO-01")

        # Simular Despacho a Cliente
        cliente = ClienteFactory(sede=self.sede, nombre_razon_social="Confecciones Andinas SA", ruc_cedula="1799999999001")
        from gestion.models import PedidoVenta
        pedido = PedidoVenta.objects.create(
            cliente=cliente,
            sede=self.sede,
            guia_remision="GUIA-PED-001",
            estado='despachado',
        )
        historial = HistorialDespacho.objects.create(
            usuario=self.supervisor,
            total_bultos=2,
            total_peso=Decimal("96.000"),
        )
        DetalleHistorialDespachoPedido.objects.create(
            historial=historial,
            pedido=pedido,
            cantidad_despachada=Decimal("96.000"),
        )
        DetalleHistorialDespacho.objects.create(
            historial=historial,
            lote=lote_tela,
            producto=producto_tela,
            peso=Decimal("96.000"),
        )

        # Consulta Trace-Forward Recall desde el lote original de fibra
        recall = GenealogiaService.obtener_trazabilidad_hacia_adelante(self.lote_entrada)

        self.assertEqual(recall['total_descendientes'], 1)
        self.assertEqual(recall['descendientes'][0]['codigo_lote'], "LOT-TEL-DESPACHO-01")

        self.assertEqual(recall['total_clientes_afectados'], 1)
        despacho_info = recall['despachos_clientes'][0]
        self.assertEqual(despacho_info['cliente_nombre'], "Confecciones Andinas SA")
        self.assertEqual(despacho_info['cliente_ruc'], "1799999999001")
        self.assertEqual(despacho_info['peso_despachado'], "96.000")
