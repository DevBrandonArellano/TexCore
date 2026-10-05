from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from gestion.services.produccion_kpi_service import ProduccionKPIService


class ProduccionKPIServiceTest(SimpleTestCase):

    @patch('gestion.services.produccion_kpi_service.OrdenProduccion.objects.all')
    def test_kpi_produccion_dado_ops_por_estado_cuando_agrupa_entonces_cuenta_cada_estado(self, mock_ops_all):
        mock_qs = MagicMock()
        mock_qs.values.return_value.annotate.return_value = [
            {'estado': 'pendiente', 'total': 10},
            {'estado': 'en_proceso', 'total': 5},
            {'estado': 'finalizada', 'total': 20},
        ]
        mock_ops_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._ops_por_estado()

        self.assertEqual(resultado.pendiente, 10)
        self.assertEqual(resultado.en_proceso, 5)
        self.assertEqual(resultado.finalizada, 20)

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_kpi_produccion_dado_lotes_en_rango_cuando_suma_kg_entonces_retorna_total(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.aggregate.return_value = {'total': Decimal("150.5")}
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._kg_lotes(date(2026, 1, 1), date(2026, 1, 31))

        self.assertEqual(resultado, Decimal("150.5"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_kpi_produccion_dado_sin_lotes_cuando_suma_kg_entonces_retorna_cero(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.aggregate.return_value = {'total': None}
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._kg_lotes(date(2026, 1, 1), date(2026, 1, 31))

        self.assertEqual(resultado, Decimal("0"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    @patch('gestion.services.produccion_kpi_service.OrdenProduccion.objects.all')
    def test_kpi_produccion_dado_sede_id_cuando_arma_consultas_entonces_filtra_por_sede(
            self, mock_ops_all, mock_lotes_all):
        mock_ops_qs = MagicMock()
        mock_ops_all.return_value = mock_ops_qs

        mock_lotes_qs = MagicMock()
        mock_lotes_all.return_value = mock_lotes_qs

        service = ProduccionKPIService(sede_id=5)

        service._base_ops_qs()
        mock_ops_qs.filter.assert_called_once_with(sede_id=5)

        service._base_lotes_qs()
        mock_lotes_qs.filter.assert_called_once_with(orden_produccion__sede_id=5)


class ProduccionKPIServiceTendenciaTest(TestCase):

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_tendencia_diaria_dado_dias_sin_lotes_cuando_calcula_entonces_los_rellena_en_cero(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {'fecha': date(2026, 4, 11), 'kg': Decimal("50.5")}
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._tendencia_diaria(date(2026, 4, 10), date(2026, 4, 12))

        self.assertEqual(len(resultado), 3)
        self.assertEqual(resultado[0].fecha, "2026-04-10")
        self.assertEqual(resultado[0].kg, Decimal("0"))

        self.assertEqual(resultado[1].fecha, "2026-04-11")
        self.assertEqual(resultado[1].kg, Decimal("50.5"))

        self.assertEqual(resultado[2].fecha, "2026-04-12")
        self.assertEqual(resultado[2].kg, Decimal("0"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_tendencia_diaria_dado_rango_sin_lotes_cuando_calcula_entonces_todo_en_cero(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = []
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._tendencia_diaria(date(2026, 4, 10), date(2026, 4, 11))

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0].kg, Decimal("0"))
        self.assertEqual(resultado[1].kg, Decimal("0"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_tendencia_diaria_dado_rango_de_un_dia_cuando_calcula_entonces_retorna_un_punto(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {'fecha': date(2026, 4, 10), 'kg': Decimal("100.0")}
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._tendencia_diaria(date(2026, 4, 10), date(2026, 4, 10))

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].fecha, "2026-04-10")
        self.assertEqual(resultado[0].kg, Decimal("100.0"))


class ProduccionKPIServicePorProductoTest(SimpleTestCase):
    """CU-EJ-08: producción agrupada por producto — drill-down ejecutivo."""

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_produccion_por_producto_dado_lotes_de_varios_productos_cuando_agrupa_entonces_un_item_por_producto(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {
                'orden_produccion__producto_salida_id': 1,
                'orden_produccion__producto_salida__codigo': 'HIL-001',
                'orden_produccion__producto_salida__descripcion': 'Hilo Nylon 40/1',
                'kg_total': Decimal('320.500'),
                'num_lotes': 6,
            },
            {
                'orden_produccion__producto_salida_id': 2,
                'orden_produccion__producto_salida__codigo': 'TEL-007',
                'orden_produccion__producto_salida__descripcion': 'Tela Jersey',
                'kg_total': Decimal('150.000'),
                'num_lotes': 2,
            },
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._produccion_por_producto(date(2026, 8, 1), date(2026, 8, 25))

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0].producto_id, 1)
        self.assertEqual(resultado[0].producto_codigo, 'HIL-001')
        self.assertEqual(resultado[0].producto_nombre, 'Hilo Nylon 40/1')
        self.assertEqual(resultado[0].kg_total, Decimal('320.500'))
        self.assertEqual(resultado[0].num_lotes, 6)
        self.assertEqual(resultado[1].producto_id, 2)

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_produccion_por_producto_dado_sin_lotes_en_rango_cuando_agrupa_entonces_lista_vacia(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = []
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._produccion_por_producto(date(2026, 8, 1), date(2026, 8, 25))

        self.assertEqual(resultado, [])

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_produccion_por_producto_dado_kg_total_nulo_cuando_agrupa_entonces_decimal_cero(
        self, mock_lotes_all
    ):
        # Borde defensivo: Sum() nunca debería ser None con num_lotes > 0, pero
        # el contrato del dataclass no debe romper si el driver lo devuelve así.
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {
                'orden_produccion__producto_salida_id': 3,
                'orden_produccion__producto_salida__codigo': 'X',
                'orden_produccion__producto_salida__descripcion': None,
                'kg_total': None,
                'num_lotes': 1,
            },
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._produccion_por_producto(date(2026, 8, 1), date(2026, 8, 25))

        self.assertEqual(resultado[0].kg_total, Decimal('0'))
        self.assertEqual(resultado[0].producto_nombre, '')


class PanelJefePlantaRendimientoTest(TestCase):
    """
    RNF-03 · TEX-17 CA-3 — el panel de Jefe de Planta carga en menos de 3000 ms
    con la sede completa cargada.

    Reproduce la carga que hace JefePlantaDashboard.tsx (fetchData) al abrirse:
    las 9 peticiones GET de su Promise.all, autenticado como jefe_planta. El
    navegador las lanza en paralelo; aquí se ejecutan en serie y se SUMAN, así
    que la cifra medida es una cota superior de la del navegador.

    IMPORTANTE — qué mide y qué NO mide este test: usa APIClient (llamada
    in-process, sin red real) contra SQLite en memoria (settings_test_local),
    así que mide el costo propio de Django + DRF sobre un volumen sembrado:
    permisos, consultas ORM, paginación y serialización JSON. NO incluye el
    salto de red real a través de Nginx, ni Gunicorn, ni la latencia ni el
    plan de ejecución de SQL Server 2022 en producción, ni el render de React.

    Es un PISO de referencia (si esto ya no está bajo 3 s in-process, el
    sistema real tampoco lo estará) — no el número que importa en planta. Su
    valor está en detectar regresiones. De las dos aserciones, la que de
    verdad protege el umbral es el techo de consultas: es determinista entre
    máquinas y detecta el N+1 que, con volumen real en SQL Server, multiplica
    los viajes a la base por cada fila serializada. La medición end-to-end
    bajo carga vive en scripts/loadtest/locustfile.py (fila "panel Jefe de
    Planta (RNF-03)").
    """

    UMBRAL_SEGUNDOS = 3.0
    NUM_ORDENES = 500
    LOTES_POR_ORDEN = 3

    ENDPOINTS_PANEL = [
        '/api/ordenes-produccion/',
        '/api/productos/',
        '/api/formula-colors/',
        '/api/sedes/',
        '/api/maquinas/',
        '/api/areas/',
        '/api/bodegas/',
        '/api/users/',
        '/api/produccion/pulso-diario/',
    ]

    # Techo de consultas de las 9 peticiones juntas (desglose en el mensaje
    # de fallo). Medido: 35, idéntico con 50 y con 500 órdenes. Son:
    #   ordenes-produccion  7 = 3 chequeos de rol (jefe_area/operario y el de
    #                           aislamiento por sede, OWASP A01) + COUNT
    #                           de la paginación + SELECT de la página con sus
    #                           select_related + prefetch de lotes + prefetch
    #                           de componentes_mezcla (con producto y bodega)
    #   productos           3 = 2 chequeos de rol + SELECT
    #   formula-colors      4 = rol + COUNT + SELECT (con versión vigente en
    #                           subconsulta) + prefetch de fases
    #   sedes               2 = COUNT + SELECT con num_areas anotado
    #   maquinas            4 = 2 chequeos de rol + SELECT con sus 5 FK en JOIN
    #                           + prefetch de operarios
    #   areas               2 = chequeo de rol (aislamiento por sede, OWASP A01;
    #                           Fase B, B5) + SELECT
    #   bodegas             2 = rol + SELECT
    #   users               6 = 2 chequeos de rol + COUNT + SELECT (sede/área
    #                           en JOIN) + prefetch de groups + prefetch de superior
    #   pulso-diario        5 = 2 chequeos de rol + 3 agregados SUM
    # Ninguna depende del número de filas: las relaciones por fila se resuelven
    # con JOIN o con un único prefetch "IN (...)". Antes de esta prueba el panel
    # hacía 302 consultas con esta misma siembra (producto_salida, mezcla,
    # peso_producido, bodegas/operarios de máquina y superiores de usuario se
    # consultaban fila a fila). Un N+1 nuevo suma decenas por página y rompe
    # este techo sin depender del reloj de la máquina.
    MAX_CONSULTAS = 35

    @classmethod
    def setUpTestData(cls):
        from datetime import datetime, time, timedelta

        from django.utils import timezone

        from gestion.models import ComponenteMezclaOP, LoteProduccion, OrdenProduccion
        from gestion.tests.factories import (
            AreaFactory,
            BodegaFactory,
            CustomUserFactory,
            FormulaColorFactory,
            MaquinaFactory,
            ProductoFactory,
            SedeFactory,
        )

        cls.sede = SedeFactory()
        areas = [AreaFactory(sede=cls.sede) for _ in range(5)]
        bodegas = [BodegaFactory(sede=cls.sede) for _ in range(6)]
        productos = [ProductoFactory(sede=cls.sede) for _ in range(60)]
        formulas = [FormulaColorFactory(sede=cls.sede) for _ in range(20)]
        # Todas las FK que leen los serializadores van pobladas: una FK nula no
        # consulta, y ocultaría un N+1 que en planta sí existe.
        maquinas = [
            MaquinaFactory(
                area=areas[i % 5], bodega_entrada=bodegas[i % 6],
                bodega_salida=bodegas[(i + 1) % 6], bodega_merma=bodegas[(i + 2) % 6],
                producto_merma=productos[i % 60],
            ) for i in range(15)
        ]
        operarios = [
            CustomUserFactory(sede=cls.sede, groups=['operario']) for _ in range(40)
        ]
        jefe_area = CustomUserFactory(sede=cls.sede, groups=['jefe_area'])
        for i, maquina in enumerate(maquinas):
            maquina.operarios.add(operarios[i % 40], operarios[(i + 1) % 40])
        for operario in operarios:
            operario.superior.add(jefe_area)
        cls.jefe_planta = CustomUserFactory(sede=cls.sede, groups=['jefe_planta'])

        estados = ['pendiente', 'en_proceso', 'finalizada']
        OrdenProduccion.objects.bulk_create([
            OrdenProduccion(
                codigo=f'OP-RNF03-{i:05d}', sede=cls.sede, area=areas[i % 5],
                producto_entrada=productos[i % 60],
                producto_salida=productos[(i + 1) % 60],
                formula_color=formulas[i % 20],
                bodega_entrada=bodegas[i % 6], bodega_salida=bodegas[(i + 1) % 6],
                maquina_asignada=maquinas[i % 15], operario_asignado=operarios[i % 40],
                peso_neto_requerido=Decimal('300.00'), estado=estados[i % 3],
            ) for i in range(cls.NUM_ORDENES)
        ], batch_size=250)
        # SQL Server no devuelve los pk desde bulk_create (SQLite sí).
        ordenes = list(
            OrdenProduccion.objects.filter(codigo__startswith='OP-RNF03-').order_by('codigo')
        )

        # Lotes de hoy y de días previos: pulso-diario agrega los del día.
        hoy = timezone.localdate()
        lotes = []
        for i, op in enumerate(ordenes):
            for j in range(cls.LOTES_POR_ORDEN):
                dia = hoy - timedelta(days=j)
                inicio = timezone.make_aware(datetime.combine(dia, time(8, 0)))
                lotes.append(LoteProduccion(
                    orden_produccion=op, codigo_lote=f'L-RNF03-{i:05d}-{j}',
                    peso_neto_producido=Decimal('95.000'), peso_merma=Decimal('5.000'),
                    operario=operarios[i % 40], maquina=maquinas[i % 15], turno='Dia',
                    hora_inicio=inicio, hora_final=inicio + timedelta(hours=8),
                ))
        LoteProduccion.objects.bulk_create(lotes, batch_size=500)

        # Mezcla de 2 componentes por orden (serializador anidado con producto y bodega).
        ComponenteMezclaOP.objects.bulk_create([
            ComponenteMezclaOP(
                orden=op, producto=productos[(i + k) % 60], bodega=bodegas[k % 6],
                porcentaje=Decimal('50.00'), cantidad_kg=Decimal('150.000'),
            ) for i, op in enumerate(ordenes) for k in range(2)
        ], batch_size=500)

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.client.force_authenticate(user=self.jefe_planta)

    def _abrir_panel(self):
        """Ejecuta las 9 peticiones del panel; devuelve (duración, consultas por endpoint)."""
        from time import perf_counter

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        desglose = {}
        duracion = 0.0
        for url in self.ENDPOINTS_PANEL:
            with CaptureQueriesContext(connection) as consultas:
                inicio = perf_counter()
                resp = self.client.get(url)
                duracion += perf_counter() - inicio
            self.assertEqual(resp.status_code, 200, f'{url} -> {resp.status_code}')
            desglose[url] = len(consultas)
        return duracion, desglose

    def test_panel_jefe_planta_dado_sede_cargada_cuando_se_abre_entonces_carga_bajo_3s_con_consultas_acotadas(self):
        duracion, desglose = self._abrir_panel()
        total = sum(desglose.values())

        self.assertLessEqual(total, self.MAX_CONSULTAS, (
            f"TEX-17 CA-3 (RNF-03): abrir el panel de Jefe de Planta ejecutó "
            f"{total} consultas (techo {self.MAX_CONSULTAS}) — probable N+1 que "
            f"degrada el umbral de {self.UMBRAL_SEGUNDOS}s con volumen real en "
            f"SQL Server. Desglose: {desglose}"
        ))
        self.assertLess(duracion, self.UMBRAL_SEGUNDOS, (
            f"TEX-17 CA-3 (RNF-03): el panel de Jefe de Planta tardó "
            f"{duracion:.3f}s en cargar sus 9 peticiones (in-process, sin red, "
            f"suma en serie) — supera el umbral de {self.UMBRAL_SEGUNDOS}s."
        ))


class OrdenPesoProducidoPrefetchTest(TestCase):
    """peso_producido con lotes prefetcheados: mismo valor, cero consultas extra (RNF-03)."""

    def setUp(self):
        from gestion.tests.factories import LoteProduccionFactory, OrdenProduccionFactory
        self.op = OrdenProduccionFactory()
        self.op_sin_lotes = OrdenProduccionFactory()
        LoteProduccionFactory(orden_produccion=self.op, peso_neto_producido=Decimal('95.500'))
        LoteProduccionFactory(orden_produccion=self.op, peso_neto_producido=Decimal('4.250'))

    def test_peso_producido_dado_lotes_prefetcheados_cuando_se_lee_entonces_suma_sin_consultar(self):
        from gestion.models import OrdenProduccion
        op = OrdenProduccion.objects.prefetch_related('lotes').get(pk=self.op.pk)
        with self.assertNumQueries(0):
            self.assertEqual(op.peso_producido, Decimal('99.750'))

    def test_peso_producido_dado_sin_prefetch_cuando_se_lee_entonces_agrega_en_base(self):
        from gestion.models import OrdenProduccion
        op = OrdenProduccion.objects.get(pk=self.op.pk)
        self.assertEqual(op.peso_producido, Decimal('99.750'))

    def test_peso_producido_dado_orden_sin_lotes_prefetcheada_cuando_se_lee_entonces_cero(self):
        from gestion.models import OrdenProduccion
        op = OrdenProduccion.objects.prefetch_related('lotes').get(pk=self.op_sin_lotes.pk)
        self.assertEqual(op.peso_producido, 0)


class ProduccionKPIServiceHistorialProductoTest(SimpleTestCase):
    """CU-EJ-09: historial diario de UN producto — gráfica de drill-down."""

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_historial_producto_dado_rango_con_huecos_cuando_consulta_entonces_rellena_dias_vacios(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {'fecha': date(2026, 8, 11), 'kg': Decimal('50.5')}
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._historial_producto(1, date(2026, 8, 10), date(2026, 8, 12))

        self.assertEqual(len(resultado), 3)
        self.assertEqual(resultado[0].fecha, '2026-08-10')
        self.assertEqual(resultado[0].kg, Decimal('0'))
        self.assertEqual(resultado[1].fecha, '2026-08-11')
        self.assertEqual(resultado[1].kg, Decimal('50.5'))
        self.assertEqual(resultado[2].kg, Decimal('0'))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_historial_producto_dado_producto_id_cuando_filtra_entonces_usa_ese_producto(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = []
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        service._historial_producto(42, date(2026, 8, 10), date(2026, 8, 10))

        _, filtro_kwargs = mock_qs.filter.call_args
        self.assertEqual(filtro_kwargs['orden_produccion__producto_salida_id'], 42)
