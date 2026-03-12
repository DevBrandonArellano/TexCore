from django.test import TestCase, override_settings
from django.contrib.auth.models import Group
from gestion.models import Sede, Area, CustomUser, Maquina, LoteProduccion, OrdenProduccion, Producto
from django.utils import timezone
from rest_framework.test import APIClient
from decimal import Decimal
import datetime

@override_settings(ROOT_URLCONF='gestion.urls')
class JefeAreaLogicTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Groups
        self.group_jefe, _ = Group.objects.get_or_create(name='jefe_area')
        self.group_operario, _ = Group.objects.get_or_create(name='operario')
        
        # Infrastructure
        self.sede = Sede.objects.create(nombre='Sede Norte')
        self.area_tintoreria = Area.objects.create(nombre='Tintoreria', sede=self.sede)
        self.area_empaquetado = Area.objects.create(nombre='Empaquetado', sede=self.sede)
        
        # Users
        self.jefe_tintoreria = CustomUser.objects.create_user(username='jefe_t', password='password', area=self.area_tintoreria)
        self.jefe_tintoreria.groups.add(self.group_jefe)
        
        self.operario1 = CustomUser.objects.create_user(username='op1', password='password', area=self.area_tintoreria)
        self.operario1.groups.add(self.group_operario)
        
        # Machines
        self.maquina1 = Maquina.objects.create(
            nombre='M1', capacidad_maxima=1000, eficiencia_ideal=0.9, area=self.area_tintoreria
        )
        self.maquina2 = Maquina.objects.create(
            nombre='M2', capacidad_maxima=500, eficiencia_ideal=0.8, area=self.area_empaquetado
        )
        
        # Product & Production
        self.producto = Producto.objects.create(codigo='P1', descripcion='Tela RT', tipo='tela', unidad_medida='kg')
        self.op = OrdenProduccion.objects.create(
            codigo='OP1', producto=self.producto, peso_neto_requerido=500, area=self.area_tintoreria
        )
        
        # Production data for today
        now = timezone.now()
        LoteProduccion.objects.create(
            codigo_lote='L1',
            peso_neto_producido=100,
            operario=self.operario1,
            maquina=self.maquina1,
            hora_inicio=now - datetime.timedelta(hours=2),
            hora_final=now - datetime.timedelta(hours=1),
            orden_produccion=self.op,
            turno='Turno 1'
        )
        LoteProduccion.objects.create(
            codigo_lote='L2',
            peso_neto_producido=150,
            operario=self.operario1,
            maquina=self.maquina1,
            hora_inicio=now - datetime.timedelta(minutes=30),
            hora_final=now,
            orden_produccion=self.op,
            turno='Turno 1'
        )

    def test_jefe_area_queryset_filtering(self):
        self.client.force_authenticate(user=self.jefe_tintoreria)
        
        # Test machines list
        response = self.client.get('/maquinas/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nombre'], 'M1')
        
        # Test users list
        response = self.client.get('/users/')
        # Jefe + Operario = 2
        self.assertEqual(len(response.data), 2)
        
    def test_efficiency_report(self):
        self.client.force_authenticate(user=self.jefe_tintoreria)
        
        response = self.client.get(f'/areas/{self.area_tintoreria.id}/reporte-eficiencia/')
        self.assertEqual(response.status_code, 200)
        
        data = response.data
        self.assertEqual(float(data['produccion_total_area']), 250.0)
        # 250 / 1000 = 25%
        self.assertEqual(float(data['maquinas'][0]['eficiencia']), 25.0)
        
        # Operario stats
        op_data = data['operarios'][0]
        self.assertEqual(op_data['total_lotes'], 2)
        self.assertEqual(float(op_data['produccion_total_kg']), 250.0)
        self.assertGreater(op_data['horas_trabajadas_aprox'], 0)

    def test_operator_performance_endpoint(self):
        self.client.force_authenticate(user=self.jefe_tintoreria)
        
        response = self.client.get(f'/users/{self.operario1.id}/desempeno/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data['produccion_hoy_kg']), 250.0)
