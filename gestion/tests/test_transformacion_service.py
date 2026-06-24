"""
Tests del servicio TransformacionService — orquestación del registro.

Técnicas ISTQB:
- Caja blanca: cobertura de ramas (primera vs N-ésima transformación,
  cadena válida vs rota, máquina del área vs de otra área).
- EP: clases válidas/inválidas de la entrada del servicio.

El servicio deriva producto_entrada para garantizar continuidad de la cadena
(SRP: el modelo solo persiste; el servicio orquesta y valida la secuencia).
"""
from decimal import Decimal
from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from gestion.tests.factories import (
    OrdenProduccionFactory, MaquinaFactory, ProductoFactory,
    CustomUserFactory, AreaFactory, SedeFactory,
)


def _data(maquina, producto_salida, **overrides):
    base = {
        'maquina': maquina.id,
        'producto_salida': producto_salida.id,
        'peso_entrada': Decimal('100.000'),
        'peso_salida': Decimal('95.000'),
        'fecha_inicio': datetime(2026, 1, 1, 8, 0),
        'fecha_fin': datetime(2026, 1, 1, 12, 0),
    }
    base.update(overrides)
    return base


class TransformacionServiceRegistrarTest(TestCase):
    def setUp(self):
        self.user = CustomUserFactory()
        self.orden = OrdenProduccionFactory()
        self.maquina = MaquinaFactory(area=self.orden.area)

    # Auditoría (ISO 27001 A.12.4): crear una transformación genera un AuditLog
    def test_servicio_dado_registro_cuando_registrar_entonces_crea_auditlog(self):
        from django.contrib.contenttypes.models import ContentType
        from gestion.models import AuditLog, TransformacionProducto
        from gestion.services.transformacion import TransformacionService
        salida = ProductoFactory(codigo='AUD-OUT', sede=self.orden.sede)
        t = TransformacionService.registrar(self.orden, _data(self.maquina, salida), self.user)
        ct = ContentType.objects.get_for_model(TransformacionProducto)
        self.assertTrue(
            AuditLog.objects.filter(content_type=ct, object_id=t.id, accion='CREATE').exists()
        )

    # RFC 5424: el servicio emite un log estructurado con SD-ELEMENT
    def test_servicio_dado_registro_cuando_registrar_entonces_emite_log_rfc5424(self):
        from gestion.services.transformacion import TransformacionService
        salida = ProductoFactory(codigo='LOG-OUT', sede=self.orden.sede)
        with self.assertLogs('gestion.services.transformacion', level='INFO') as cm:
            TransformacionService.registrar(self.orden, _data(self.maquina, salida), self.user)
        self.assertTrue(any('Transformación de producto registrada' in m for m in cm.output))

    # Caja blanca: rama "primera transformación" → secuencia 1 + usa producto_entrada de la OP
    def test_servicio_dado_primera_transf_cuando_registrar_entonces_secuencia_1_y_usa_entrada_op(self):
        from gestion.services.transformacion import TransformacionService
        salida = ProductoFactory(codigo='TELA-001-REC', sede=self.orden.sede)
        t = TransformacionService.registrar(self.orden, _data(self.maquina, salida), self.user)
        self.assertEqual(t.numero_secuencia, 1)
        self.assertEqual(t.producto_entrada, self.orden.producto_entrada)
        self.assertEqual(t.producto_salida, salida)
        self.assertEqual(t.merma, Decimal('5.000'))
        self.assertEqual(t.operario, self.user)

    # Caja blanca: rama "N-ésima transformación" → secuencia incremental + encadena producto
    def test_servicio_dado_segunda_transf_cuando_registrar_entonces_secuencia_2_y_encadena(self):
        from gestion.services.transformacion import TransformacionService
        salida1 = ProductoFactory(codigo='TELA-001-REC', sede=self.orden.sede)
        salida2 = ProductoFactory(codigo='TELA-MEZCLA', sede=self.orden.sede)
        TransformacionService.registrar(self.orden, _data(self.maquina, salida1), self.user)
        t2 = TransformacionService.registrar(self.orden, _data(self.maquina, salida2,
                                                               peso_entrada=Decimal('95.000'),
                                                               peso_salida=Decimal('90.000')), self.user)
        self.assertEqual(t2.numero_secuencia, 2)
        # La entrada de la 2da transformación es la salida de la 1ra (continuidad de cadena)
        self.assertEqual(t2.producto_entrada, salida1)

    # Caja blanca: rama "máquina de otra área" → ValidationError (aislamiento)
    def test_servicio_dado_maquina_de_otra_area_cuando_registrar_entonces_falla(self):
        from gestion.services.transformacion import TransformacionService
        otra_maquina = MaquinaFactory(area=AreaFactory())  # área distinta
        salida = ProductoFactory()
        with self.assertRaises(ValidationError):
            TransformacionService.registrar(self.orden, _data(otra_maquina, salida), self.user)

    # EP inválida: peso_salida > peso_entrada → ValidationError (merma negativa)
    def test_servicio_dado_peso_salida_mayor_cuando_registrar_entonces_falla(self):
        from gestion.services.transformacion import TransformacionService
        salida = ProductoFactory(sede=self.orden.sede)
        with self.assertRaises(ValidationError):
            TransformacionService.registrar(
                self.orden,
                _data(self.maquina, salida, peso_entrada=Decimal('90.000'), peso_salida=Decimal('91.000')),
                self.user,
            )

    # Caja blanca: rama "primera sin producto_entrada en OP ni en data" → ValidationError
    def test_servicio_dado_op_sin_entrada_y_sin_dato_cuando_registrar_primera_entonces_falla(self):
        from gestion.services.transformacion import TransformacionService
        orden_sin_entrada = OrdenProduccionFactory(producto_entrada=None)
        maquina = MaquinaFactory(area=orden_sin_entrada.area)
        salida = ProductoFactory()
        with self.assertRaises(ValidationError):
            TransformacionService.registrar(orden_sin_entrada, _data(maquina, salida), self.user)

    # Seguridad multi-sede: producto_salida de OTRA sede → rechazado (aislamiento)
    def test_servicio_dado_producto_salida_de_otra_sede_cuando_registrar_entonces_falla(self):
        from gestion.services.transformacion import TransformacionService
        producto_intruso = ProductoFactory(codigo='AJENO-001', sede=SedeFactory())
        with self.assertRaises(ValidationError):
            TransformacionService.registrar(
                self.orden, _data(self.maquina, producto_intruso), self.user
            )

    # EP inválida: producto_salida inexistente → ValidationError
    def test_servicio_dado_producto_salida_inexistente_cuando_registrar_entonces_falla(self):
        from gestion.services.transformacion import TransformacionService
        data = {
            'maquina': self.maquina.id,
            'producto_salida': 999999,
            'peso_entrada': Decimal('100.000'),
            'peso_salida': Decimal('95.000'),
            'fecha_inicio': '2026-01-01T08:00:00Z',
            'fecha_fin': '2026-01-01T12:00:00Z',
        }
        with self.assertRaises(ValidationError):
            TransformacionService.registrar(self.orden, data, self.user)

    # EP inválida: máquina inexistente → ValidationError
    def test_servicio_dado_maquina_inexistente_cuando_registrar_entonces_falla(self):
        from gestion.services.transformacion import TransformacionService
        salida = ProductoFactory()
        data = {
            'maquina': 999999,
            'producto_salida': salida.id,
            'peso_entrada': Decimal('100.000'),
            'peso_salida': Decimal('95.000'),
            'fecha_inicio': '2026-01-01T08:00:00Z',
            'fecha_fin': '2026-01-01T12:00:00Z',
        }
        with self.assertRaises(ValidationError):
            TransformacionService.registrar(self.orden, data, self.user)

    # EP válida: primera sin entrada en OP pero con producto_entrada explícito en data → OK
    def test_servicio_dado_op_sin_entrada_con_dato_explicito_cuando_registrar_entonces_ok(self):
        from gestion.services.transformacion import TransformacionService
        orden_sin_entrada = OrdenProduccionFactory(producto_entrada=None)
        maquina = MaquinaFactory(area=orden_sin_entrada.area)
        entrada = ProductoFactory(codigo='MP-LANA', sede=orden_sin_entrada.sede)
        salida = ProductoFactory(codigo='LANA-REC', sede=orden_sin_entrada.sede)
        t = TransformacionService.registrar(
            orden_sin_entrada,
            _data(maquina, salida, producto_entrada=entrada.id),
            self.user,
        )
        self.assertEqual(t.producto_entrada, entrada)
