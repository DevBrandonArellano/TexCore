"""
Comando `run_mrp` (TEX-27, ADR-012): ejecuta el MRP de una sede o de todas las activas.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): --sede / sin opción; sede existente / inexistente;
  ejecución completada / fallida.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from gestion.tests.factories import SedeFactory
from inventory.models import MRPEjecucion


class RunMRPCommandTestCase(TestCase):
    def _correr(self, *args):
        salida = StringIO()
        call_command("run_mrp", *args, stdout=salida)
        return salida.getvalue()

    def test_run_mrp_dado_opcion_sede_cuando_corre_entonces_calcula_solo_esa_sede(self):
        sede = SedeFactory(nombre="Planta Norte")
        SedeFactory()
        salida = self._correr("--sede", str(sede.id))
        self.assertEqual(list(MRPEjecucion.objects.values_list("sede_id", flat=True)), [sede.id])
        self.assertIn("Planta Norte", salida)

    def test_run_mrp_dado_sin_opciones_cuando_corre_entonces_calcula_todas_las_activas(self):
        activas = {SedeFactory().id, SedeFactory().id}
        SedeFactory(status="inactivo")
        self._correr()
        self.assertEqual(set(MRPEjecucion.objects.values_list("sede_id", flat=True)), activas)

    def test_run_mrp_dado_sede_inexistente_cuando_corre_entonces_error(self):
        with self.assertRaises(CommandError):
            self._correr("--sede", "999999")

    def test_run_mrp_dado_ejecucion_fallida_cuando_corre_entonces_termina_con_error(self):
        sede = SedeFactory()
        fallida = MRPEjecucion(sede=sede, estado=MRPEjecucion.ESTADO_FALLIDA, mensaje_error="Error interno")
        with (
            patch("inventory.management.commands.run_mrp.MRPEngine.ejecutar", return_value=fallida),
            self.assertRaises(CommandError),
        ):
            self._correr("--sede", str(sede.id))
