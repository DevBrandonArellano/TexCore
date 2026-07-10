"""
Pruebas complementarias de gestion/serializers.py — validadores y métodos
create/update que test_serializers.py no ejercita.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol autorizado / no autorizado, tipo_calculo
  gr_l / pct, estado transicionable / bloqueado.
- Análisis de valores límite (BVA): porcentaje = 0 / 100 / 101, precio_unitario
  igual al costo base.
- Caja blanca: rama de derivación sede desde área, rama de admin_sistemas sin
  sede, ramas create/update con y sin grupos/password.
"""
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from gestion.serializers import (
    ClienteSerializer, ComponenteMezclaOPSerializer, CustomUserSerializer,
    DetalleFormulaSerializer, DetallePedidoSerializer, FormulaColorWriteSerializer,
    OrdenProduccionEstadoSerializer,
)
from gestion.tests.factories import (
    AreaFactory, ClienteFactory, ComponenteMezclaOPFactory, CustomUserFactory,
    FaseRecetaFactory, OrdenProduccionFactory, ProductoFactory, SedeFactory,
)

rf = APIRequestFactory()


class CustomUserSerializerValidateTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        Group.objects.get_or_create(name='vendedor')
        Group.objects.get_or_create(name='admin_sistemas')

    def test_validate_dado_area_sin_sede_cuando_valida_entonces_infiere_sede_del_area(self):
        # Caja blanca: `if area and not sede: data['sede'] = area.sede`
        vendedor_group = Group.objects.get(name='vendedor')
        s = CustomUserSerializer(data={
            'username': 'nuevo1', 'password': 'x', 'area': self.area.id,
            'groups': [vendedor_group.id],
        })
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['sede'], self.sede)

    def test_validate_dado_area_y_sede_inconsistentes_cuando_valida_entonces_error(self):
        otra_sede = SedeFactory()
        vendedor_group = Group.objects.get(name='vendedor')
        s = CustomUserSerializer(data={
            'username': 'nuevo2', 'password': 'x', 'area': self.area.id, 'sede': otra_sede.id,
            'groups': [vendedor_group.id],
        })
        self.assertFalse(s.is_valid())
        self.assertIn('area', s.errors)

    def test_validate_dado_rol_no_admin_sin_sede_cuando_valida_entonces_error(self):
        # EP: rol distinto de admin_sistemas requiere sede obligatoriamente
        vendedor_group = Group.objects.get(name='vendedor')
        s = CustomUserSerializer(data={
            'username': 'nuevo3', 'password': 'x', 'groups': [vendedor_group.id],
        })
        self.assertFalse(s.is_valid())
        self.assertIn('sede', s.errors)

    def test_validate_dado_admin_sistemas_sin_sede_cuando_valida_entonces_ok(self):
        # EP: admin_sistemas está exento del requisito de sede
        admin_group = Group.objects.get(name='admin_sistemas')
        s = CustomUserSerializer(data={
            'username': 'nuevo4', 'password': 'x', 'groups': [admin_group.id],
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_validate_dado_sin_grupos_cuando_valida_entonces_ok_sin_validar_sede(self):
        # Caja blanca: `if not groups: return data` (paso intermedio de creación)
        s = CustomUserSerializer(data={'username': 'nuevo5', 'password': 'x'})
        self.assertTrue(s.is_valid(), s.errors)


class CustomUserSerializerCreateUpdateTestCase(TestCase):
    def setUp(self):
        self.ejecutivo_group, _ = Group.objects.get_or_create(name='ejecutivo')
        self.vendedor_group, _ = Group.objects.get_or_create(name='vendedor')
        self.sede = SedeFactory()

    def test_create_dado_grupo_ejecutivo_cuando_crea_entonces_asigna_todas_las_bodegas(self):
        from gestion.tests.factories import BodegaFactory
        BodegaFactory()
        BodegaFactory()

        s = CustomUserSerializer(data={
            'username': 'ejecutivo1', 'password': 'Pass123!', 'sede': self.sede.id,
            'groups': [self.ejecutivo_group.id],
        })
        self.assertTrue(s.is_valid(), s.errors)
        user = s.save()

        self.assertTrue(user.check_password('Pass123!'))
        self.assertEqual(user.bodegas_asignadas.count(), 2)

    def test_update_dado_password_nueva_cuando_actualiza_entonces_la_hashea(self):
        user = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        s = CustomUserSerializer(
            user, data={'password': 'NuevaClave456!'}, partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password('NuevaClave456!'))

    def test_update_dado_sin_groups_en_payload_cuando_actualiza_entonces_mantiene_los_actuales(self):
        # Caja blanca: `if groups is None and self.instance: groups = self.instance.groups.all()`
        user = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        s = CustomUserSerializer(user, data={'first_name': 'NuevoNombre'}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertTrue(user.groups.filter(name='vendedor').exists())


class DetalleFormulaSerializerTestCase(TestCase):
    def setUp(self):
        self.fase = FaseRecetaFactory()
        # producto: DetalleFormula.producto tiene limit_choices_to={'tipo': 'quimico'},
        # que DRF aplica como filtro de queryset en el PrimaryKeyRelatedField.
        self.producto = ProductoFactory(tipo='quimico')

    def test_validate_dado_tipo_gr_l_sin_concentracion_cuando_valida_entonces_error(self):
        s = DetalleFormulaSerializer(data={
            'fase': self.fase.id, 'producto': self.producto.id, 'tipo_calculo': 'gr_l',
            'orden_adicion': 1,
        })
        self.assertFalse(s.is_valid())
        self.assertIn('concentracion_gr_l', s.errors)

    def test_validate_dado_tipo_pct_sin_porcentaje_cuando_valida_entonces_error(self):
        s = DetalleFormulaSerializer(data={
            'fase': self.fase.id, 'producto': self.producto.id, 'tipo_calculo': 'pct',
            'orden_adicion': 1,
        })
        self.assertFalse(s.is_valid())
        self.assertIn('porcentaje', s.errors)

    def test_validate_dado_tipo_gr_l_con_concentracion_cuando_valida_entonces_ok(self):
        s = DetalleFormulaSerializer(data={
            'fase': self.fase.id, 'producto': self.producto.id, 'tipo_calculo': 'gr_l',
            'concentracion_gr_l': '10.00', 'orden_adicion': 1,
        })
        self.assertTrue(s.is_valid(), s.errors)


class FormulaColorWriteSerializerValidateFasesTestCase(TestCase):
    def setUp(self):
        self.producto = ProductoFactory()

    def test_validate_fases_dado_insumo_duplicado_cuando_valida_entonces_error(self):
        fases_data = [{
            'nombre': 'tintura', 'orden': 1,
            'detalles': [
                {'producto': self.producto, 'tipo_calculo': 'gr_l', 'concentracion_gr_l': Decimal('5')},
                {'producto': self.producto, 'tipo_calculo': 'gr_l', 'concentracion_gr_l': Decimal('3')},
            ],
        }]
        s = FormulaColorWriteSerializer()
        with self.assertRaises(Exception):
            s.validate_fases(fases_data)

    def test_validate_fases_dado_tipo_pct_sin_porcentaje_cuando_valida_entonces_error(self):
        fases_data = [{
            'nombre': 'tintura', 'orden': 1,
            'detalles': [{'producto': self.producto, 'tipo_calculo': 'pct'}],
        }]
        s = FormulaColorWriteSerializer()
        with self.assertRaises(Exception):
            s.validate_fases(fases_data)

    def test_validate_fases_dado_datos_validos_cuando_valida_entonces_ok(self):
        fases_data = [{
            'nombre': 'tintura', 'orden': 1,
            'detalles': [{'producto': self.producto, 'tipo_calculo': 'gr_l', 'concentracion_gr_l': Decimal('5')}],
        }]
        s = FormulaColorWriteSerializer()
        result = s.validate_fases(fases_data)
        self.assertEqual(result, fases_data)


class DetallePedidoSerializerTestCase(TestCase):
    def setUp(self):
        self.producto = ProductoFactory(precio_base=Decimal('10.000'))

    def test_validate_dado_precio_menor_al_base_cuando_valida_entonces_error(self):
        s = DetallePedidoSerializer()
        with self.assertRaises(Exception):
            s.validate({'producto': self.producto, 'precio_unitario': Decimal('9.000')})

    def test_validate_dado_precio_igual_al_base_cuando_valida_entonces_ok(self):
        # BVA: precio_unitario == precio_base (frontera permitida)
        s = DetallePedidoSerializer()
        data = {'producto': self.producto, 'precio_unitario': Decimal('10.000')}
        result = s.validate(data)
        self.assertEqual(result, data)

    def test_validate_dado_precio_mayor_al_base_cuando_valida_entonces_ok(self):
        s = DetallePedidoSerializer()
        data = {'producto': self.producto, 'precio_unitario': Decimal('12.000')}
        result = s.validate(data)
        self.assertEqual(result, data)


class OrdenProduccionEstadoSerializerTestCase(TestCase):
    def test_validate_estado_dado_orden_finalizada_cuando_regresa_a_pendiente_entonces_error(self):
        orden = OrdenProduccionFactory(estado='finalizada')
        s = OrdenProduccionEstadoSerializer(orden, data={'estado': 'pendiente'})
        self.assertFalse(s.is_valid())
        self.assertIn('estado', s.errors)

    def test_validate_estado_dado_orden_en_proceso_cuando_avanza_a_finalizada_entonces_ok(self):
        orden = OrdenProduccionFactory(estado='en_proceso')
        s = OrdenProduccionEstadoSerializer(orden, data={'estado': 'finalizada'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_validate_estado_dado_orden_finalizada_cuando_se_mantiene_finalizada_entonces_ok(self):
        # Caja blanca: `value != 'finalizada'` es False cuando no cambia -> permitido
        orden = OrdenProduccionFactory(estado='finalizada')
        s = OrdenProduccionEstadoSerializer(orden, data={'estado': 'finalizada'})
        self.assertTrue(s.is_valid(), s.errors)


class ComponenteMezclaOPSerializerTestCase(TestCase):
    def setUp(self):
        self.orden = OrdenProduccionFactory(peso_neto_requerido=Decimal('200.00'))

    def test_validate_porcentaje_dado_cero_cuando_valida_entonces_error(self):
        s = ComponenteMezclaOPSerializer()
        with self.assertRaises(Exception):
            s.validate_porcentaje(Decimal('0'))

    def test_validate_porcentaje_dado_mayor_a_cien_cuando_valida_entonces_error(self):
        s = ComponenteMezclaOPSerializer()
        with self.assertRaises(Exception):
            s.validate_porcentaje(Decimal('101'))

    def test_validate_porcentaje_dado_cien_cuando_valida_entonces_ok(self):
        # BVA: porcentaje == 100 (frontera superior permitida)
        s = ComponenteMezclaOPSerializer()
        result = s.validate_porcentaje(Decimal('100'))
        self.assertEqual(result, Decimal('100'))

    def test_validate_dado_orden_y_porcentaje_cuando_valida_entonces_calcula_cantidad_kg(self):
        componente = ComponenteMezclaOPFactory(orden=self.orden)
        s = ComponenteMezclaOPSerializer(componente)
        result = s.validate({'orden': self.orden, 'porcentaje': Decimal('50')})
        self.assertEqual(result['cantidad_kg'], Decimal('100.000'))


class ClienteSerializerValidateTieneBeneficioTestCase(TestCase):
    def setUp(self):
        self.cliente = ClienteFactory(tiene_beneficio=False)

    def _serializer_con_usuario(self, user, value):
        request = rf.get('/')
        request.user = user
        s = ClienteSerializer(self.cliente, context={'request': request})
        return s, value

    def test_validate_tiene_beneficio_dado_usuario_no_autorizado_cuando_cambia_entonces_error(self):
        operario = CustomUserFactory(groups=['operario'])
        s, value = self._serializer_con_usuario(operario, True)
        with self.assertRaises(Exception):
            s.validate_tiene_beneficio(value)

    def test_validate_tiene_beneficio_dado_vendedor_cuando_cambia_entonces_ok(self):
        vendedor = CustomUserFactory(groups=['vendedor'])
        s, value = self._serializer_con_usuario(vendedor, True)
        result = s.validate_tiene_beneficio(value)
        self.assertTrue(result)

    def test_validate_tiene_beneficio_dado_sin_cambio_cuando_valida_entonces_ok_sin_chequear_permiso(self):
        # Caja blanca: `if self.instance and self.instance.tiene_beneficio != value` es False
        # cuando el valor no cambia -> no se exige autorización.
        operario = CustomUserFactory(groups=['operario'])
        s, value = self._serializer_con_usuario(operario, False)  # ya es False
        result = s.validate_tiene_beneficio(value)
        self.assertFalse(result)
