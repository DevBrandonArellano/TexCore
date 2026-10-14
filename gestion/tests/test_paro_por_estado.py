"""
Paros automáticos por cambio de estado de la máquina (decisión del usuario, 14-oct-2026).

Pasar una máquina a `mantenimiento` o `inactiva` abre un paro con esa fecha y devolverla a
`operativa` lo cierra, para que el historial del Jefe de Área diga qué días estuvo detenida sin
depender de que alguien registre el paro a mano. Los paros manuales no se tocan nunca: son
históricos y alimentan el OEE.

Técnicas ISTQB aplicadas:
- Tabla de decisión: estado anterior × estado nuevo → abrir, cerrar, ambos o nada.
- Partición de equivalencia (EP): estado que detiene (`mantenimiento`, `inactiva`) / que reanuda.
- Transición de estados (STT): operativa → mantenimiento → inactiva → operativa.
"""

from django.test import TestCase
from django.utils import timezone

from gestion.models import ParoMaquina
from gestion.services.paro_por_estado import ParoPorEstadoService
from gestion.tests.factories import CustomUserFactory, MaquinaFactory, ParoMaquinaFactory


class ParoPorEstadoServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = CustomUserFactory()

    def setUp(self):
        self.maquina = MaquinaFactory(estado="operativa")

    def _sincronizar(self, anterior, nuevo):
        ParoPorEstadoService.sincronizar(self.maquina, anterior, nuevo, self.usuario)

    def _automaticos(self):
        return ParoMaquina.objects.filter(maquina=self.maquina, origen="estado").order_by("inicio")

    def test_paro_dado_paso_a_mantenimiento_cuando_sincroniza_entonces_abre_paro_planificado(self):
        self._sincronizar("operativa", "mantenimiento")

        paro = self._automaticos().get()
        self.assertEqual(paro.categoria, "MANTENIMIENTO_PLANIFICADO")
        self.assertTrue(paro.planificado)
        self.assertIsNone(paro.fin)
        self.assertEqual(paro.usuario, self.usuario)
        self.assertIn("mantenimiento", paro.descripcion.lower())

    def test_paro_dado_paso_a_inactiva_cuando_sincroniza_entonces_abre_paro_no_planificado(self):
        self._sincronizar("operativa", "inactiva")

        paro = self._automaticos().get()
        self.assertEqual(paro.categoria, "OTRO")
        self.assertFalse(paro.planificado)
        self.assertIsNone(paro.fin)

    def test_paro_dado_vuelta_a_operativa_cuando_sincroniza_entonces_cierra_el_abierto(self):
        self._sincronizar("operativa", "mantenimiento")
        antes = timezone.now()

        self._sincronizar("mantenimiento", "operativa")

        paro = self._automaticos().get()
        self.assertIsNotNone(paro.fin)
        self.assertGreaterEqual(paro.fin, antes)
        self.assertGreater(paro.duracion_minutos, -1)

    def test_paro_dado_mantenimiento_a_inactiva_cuando_sincroniza_entonces_cierra_uno_y_abre_otro(self):
        self._sincronizar("operativa", "mantenimiento")

        self._sincronizar("mantenimiento", "inactiva")

        paros = list(self._automaticos())
        self.assertEqual(len(paros), 2)
        self.assertIsNotNone(paros[0].fin)
        self.assertEqual(paros[0].categoria, "MANTENIMIENTO_PLANIFICADO")
        self.assertIsNone(paros[1].fin)
        self.assertEqual(paros[1].categoria, "OTRO")

    def test_paro_dado_estado_sin_cambio_cuando_sincroniza_entonces_no_registra_nada(self):
        self._sincronizar("operativa", "operativa")
        self._sincronizar("mantenimiento", "mantenimiento")

        self.assertEqual(self._automaticos().count(), 0)

    def test_paro_dado_mismo_estado_repetido_cuando_sincroniza_dos_veces_entonces_no_duplica(self):
        self._sincronizar("operativa", "mantenimiento")
        self._sincronizar("operativa", "mantenimiento")

        self.assertEqual(self._automaticos().filter(fin__isnull=True).count(), 1)

    def test_paro_manual_dado_paro_abierto_a_mano_cuando_vuelve_a_operativa_entonces_no_se_cierra(self):
        manual = ParoMaquinaFactory(maquina=self.maquina, fin=None, categoria="AVERIA")

        self._sincronizar("operativa", "mantenimiento")
        self._sincronizar("mantenimiento", "operativa")

        manual.refresh_from_db()
        self.assertIsNone(manual.fin)
        self.assertEqual(manual.origen, "manual")

    def test_paro_dado_vuelta_a_operativa_sin_paro_abierto_cuando_sincroniza_entonces_no_falla(self):
        self._sincronizar("inactiva", "operativa")

        self.assertEqual(self._automaticos().count(), 0)
