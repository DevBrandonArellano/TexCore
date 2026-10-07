"""Caracterización de _get_object_sede_id para modelos auditados por señal (sin SedeResolvableMixin).

Fija el orden de prioridad del fallback por atributos antes y después de su refactor (C901).

Escrito con unittest (no pytest): la suite del backend corre con ``manage.py test``, que
no colecta funciones sueltas de pytest, y el CI no instala pytest.
"""
from types import SimpleNamespace as NS
from unittest.mock import patch

from django.test import SimpleTestCase

from gestion.models.core import _get_object_sede_id


class Sede:
    def __init__(self, pk):
        self.pk = pk


class Explota:
    @property
    def sede_id(self):
        raise RuntimeError("acceso roto")


CASOS = [
    (None, None),
    (Sede(7), 7),
    (NS(sede_id=3, area=NS(sede_id=9)), 3),
    (NS(sede_id=None, sede=NS(pk=4)), 4),
    (NS(fase=NS(formula=NS(sede_id=5))), 5),
    (NS(fase=NS(formula=None), bodega=NS(sede_id=9)), None),
    (NS(bodega=NS(sede_id=6), area=NS(sede_id=9)), 6),
    (NS(orden_produccion=NS(sede_id=8)), 8),
    (NS(pedido_venta=NS(sede_id=10)), 10),
    (NS(bodega_origen=NS(sede_id=11), bodega_destino=NS(sede_id=12)), 11),
    (NS(bodega_origen=None, bodega_destino=NS(sede_id=12)), 12),
    (NS(area=NS(sede_id=None), producto=NS(sede_id=13)), None),
    (NS(producto=NS(sede_id=13)), 13),
    (NS(lote=NS(orden_produccion=NS(sede_id=14))), 14),
    (NS(lote=NS(orden_produccion=None)), None),
    (NS(), None),
]


class GetObjectSedeIdFallbackTestCase(SimpleTestCase):

    def test_get_object_sede_id_dado_objeto_sin_protocolo_cuando_resuelve_entonces_respeta_prioridad(self):
        for objeto, esperado in CASOS:
            with self.subTest(objeto=objeto):
                self.assertEqual(_get_object_sede_id(objeto), esperado)

    def test_get_object_sede_id_dado_atributo_que_falla_cuando_resuelve_entonces_registra_y_retorna_none(self):
        with patch("gestion.models.core.logger") as logger:
            self.assertIsNone(_get_object_sede_id(Explota()))
        logger.warning.assert_called_once()
