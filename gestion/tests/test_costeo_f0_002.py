"""
Tests Sprint 6 (F0-002): Costeo de Producción por Lote.
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-CosteoLoteProduccion

Costo total = MP + químicos + operario + máquina + otros.
Horas reales = hora_final - hora_inicio del lote (2h en las fixtures).

Técnicas ISTQB: EP (con/sin tarifas configuradas), BVA (tarifa con
vigente_hasta NULL = contrato abierto), STT (margen sobre precio de venta).
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import (
    Area,
    Bodega,
    CostoHoraMaquina,
    CostoLoteProduccion,
    CustomUser,
    DescargaQuimicoOP,
    LoteProduccion,
    Maquina,
    OrdenProduccion,
    Producto,
    Proveedor,
    Sede,
    TarifaOperario,
)
from gestion.services.costeo_service import CostoLoteService
from gestion.services.materia_prima_service import MateriaPrimaService


class CosteoLoteBaseTestCase(TestCase):

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Costeo', location='Quito')
        self.area = Area.objects.create(nombre='Tejeduría', sede=self.sede)
        self.operario = CustomUser.objects.create_user(username='operario_costeo', password='pass')
        self.proveedor = Proveedor.objects.create(nombre='Proveedor Costeo', sede=self.sede)

        self.hilo = Producto.objects.create(
            codigo='H-C01', descripcion='Hilo Costeo', tipo='hilo',
            unidad_medida='kg', precio_base=Decimal('8.00'), sede=self.sede,
        )
        self.quimico = Producto.objects.create(
            codigo='Q-C01', descripcion='Colorante Costeo', tipo='quimico',
            unidad_medida='kg', precio_base=Decimal('20.00'), sede=self.sede,
        )
        self.tela = Producto.objects.create(
            codigo='T-C01', descripcion='Tela Costeo', tipo='tela',
            unidad_medida='kg', precio_base=Decimal('25.00'), sede=self.sede,
        )
        self.bodega = Bodega.objects.create(nombre='Bodega Costeo', sede=self.sede)
        self.maquina = Maquina.objects.create(
            nombre='Jet Costeo', capacidad_maxima=Decimal('500.00'),
            eficiencia_ideal=Decimal('0.90'), area=self.area,
        )

        self.orden = OrdenProduccion.objects.create(
            codigo='OP-COSTEO-1',
            producto_entrada=self.hilo,
            producto_salida=self.tela,
            peso_neto_requerido=Decimal('100.00'),
            sede=self.sede,
            maquina_asignada=self.maquina,
            operario_asignado=self.operario,
        )
        ahora = timezone.now()
        self.lote = LoteProduccion.objects.create(
            orden_produccion=self.orden,
            codigo_lote='LP-COSTEO-1',
            peso_neto_producido=Decimal('95.000'),
            operario=self.operario,
            maquina=self.maquina,
            turno='diurno',
            hora_inicio=ahora - timedelta(hours=2),  # 2 horas de trabajo
            hora_final=ahora,
        )

    def _con_materia_prima(self, cantidad='50.000', costo='10.000'):
        """50 kg × $10 = $500 de MP consumida en el lote."""
        mp = MateriaPrimaService.registrar_entrada(
            proveedor=self.proveedor, producto=self.hilo,
            lote_proveedor='MP-COSTEO', cantidad_kg=Decimal('100.000'),
            costo_unitario=Decimal(costo), bodega_recepcion=self.bodega,
            fecha_recepcion=timezone.now().date(), usuario=self.operario,
        )
        MateriaPrimaService.consumir_materia_prima(
            lote_produccion=self.lote,
            consumos_data=[{'materia_prima_lote_id': mp.id, 'cantidad_kg': Decimal(cantidad)}],
            usuario=self.operario,
        )

    def _con_quimicos(self, cantidad='5.000'):
        """5 kg × $20 (precio_base) = $100 de químicos."""
        DescargaQuimicoOP.objects.create(
            orden_produccion=self.orden,
            producto=self.quimico,
            bodega=self.bodega,
            tipo_calculo='gr_l',
            cantidad_calculada_kg=Decimal(cantidad),
            estado='aplicada',
            descargado_por=self.operario,
        )

    def _con_tarifas(self):
        """Operario $10/h y máquina $5/h; 2 horas → $20 + $10."""
        TarifaOperario.objects.create(
            operario=self.operario, tipo_contrato='tiempo',
            tarifa_hora=Decimal('10.00'),
            vigente_desde=timezone.now().date() - timedelta(days=30),
            vigente_hasta=None,  # contrato abierto (BVA)
            sede=self.sede,
        )
        CostoHoraMaquina.objects.create(
            maquina=self.maquina, costo_hora=Decimal('5.00'),
            vigente_desde=timezone.now().date() - timedelta(days=30),
            vigente_hasta=None,
        )


class CosteoCalculoTestCase(CosteoLoteBaseTestCase):

    def test_costeo_dado_mp_quimicos_operario_y_maquina_cuando_calcula_entonces_suma_todos_los_componentes(self):
        """STT: MP $500 + químicos $100 + operario $20 + máquina $10 = $630."""
        self._con_materia_prima()
        self._con_quimicos()
        self._con_tarifas()

        costo = CostoLoteService.calcular_costo(self.lote, self.operario)

        self.assertEqual(costo.costo_materia_prima, Decimal('500.000'))
        self.assertEqual(costo.costo_quimicos, Decimal('100.000'))
        self.assertEqual(costo.costo_operario, Decimal('20.000'))
        self.assertEqual(costo.costo_maquina, Decimal('10.000'))
        self.assertEqual(costo.total_costo, Decimal('630.000'))

    def test_costeo_dado_sin_tarifas_cuando_calcula_entonces_operario_y_maquina_en_cero(self):
        """EP sin catálogo de tarifas: operario y máquina quedan en 0."""
        self._con_materia_prima()
        self._con_quimicos()

        costo = CostoLoteService.calcular_costo(self.lote, self.operario)

        self.assertEqual(costo.costo_operario, Decimal('0.000'))
        self.assertEqual(costo.costo_maquina, Decimal('0.000'))
        self.assertEqual(costo.total_costo, Decimal('600.000'))

    def test_costeo_dado_tarifa_sin_vigencia_final_cuando_calcula_entonces_la_aplica(self):
        """BVA: tarifa con vigente_hasta NULL (contrato abierto) SÍ aplica."""
        self._con_tarifas()  # ambas con vigente_hasta=None

        costo = CostoLoteService.calcular_costo(self.lote, self.operario)

        self.assertEqual(costo.costo_operario, Decimal('20.000'))
        self.assertEqual(costo.costo_maquina, Decimal('10.000'))

    def test_costeo_dado_tarifa_expirada_cuando_calcula_entonces_no_la_aplica(self):
        """EP expirada: tarifa que venció antes del lote no se usa."""
        TarifaOperario.objects.create(
            operario=self.operario, tipo_contrato='tiempo',
            tarifa_hora=Decimal('99.00'),
            vigente_desde=timezone.now().date() - timedelta(days=60),
            vigente_hasta=timezone.now().date() - timedelta(days=30),  # expirada
            sede=self.sede,
        )
        costo = CostoLoteService.calcular_costo(self.lote, self.operario)
        self.assertEqual(costo.costo_operario, Decimal('0.000'))

    def test_costeo_dado_precio_y_costo_cuando_calcula_margen_entonces_retorna_monto_y_porcentaje(self):
        """STT margen: precio $1000, costo $630 → margen $370 (37%)."""
        self._con_materia_prima()
        self._con_quimicos()
        self._con_tarifas()
        costo = CostoLoteService.calcular_costo(self.lote, self.operario)

        costo.calcular_margen(precio_venta=Decimal('1000.000'))

        costo.refresh_from_db()
        self.assertEqual(costo.margen_bruto, Decimal('370.000'))
        self.assertEqual(costo.margen_bruto_pct, Decimal('37.00'))

    def test_costeo_dado_costo_ya_calculado_cuando_recalcula_entonces_no_duplica(self):
        """STT: recalcular dos veces no duplica el registro ni el costo."""
        self._con_materia_prima()
        CostoLoteService.calcular_costo(self.lote, self.operario)
        costo2 = CostoLoteService.calcular_costo(self.lote, self.operario)

        self.assertEqual(CostoLoteProduccion.objects.count(), 1)
        self.assertEqual(costo2.costo_materia_prima, Decimal('500.000'))


class CosteoEndpointTestCase(CosteoLoteBaseTestCase):

    def test_obtener_costo_dado_lote_costeado_cuando_consulta_endpoint_entonces_retorna_desglose(self):
        """GET /api/lotes-produccion/{id}/obtener-costo/ retorna el desglose."""
        self._con_materia_prima()
        admin = CustomUser.objects.create_user(username='admin_costeo', password='pass')
        grupo, _ = Group.objects.get_or_create(name='admin_sistemas')
        admin.groups.add(grupo)

        api = APIClient()
        api.force_authenticate(user=admin)
        response = api.get(f'/api/lotes-produccion/{self.lote.id}/obtener-costo/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data['costo_materia_prima'])), Decimal('500.000'))
        self.assertEqual(response.data['lote_codigo'], 'LP-COSTEO-1')
