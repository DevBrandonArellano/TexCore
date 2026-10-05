"""
Pruebas del snapshot de AuditableModelMixin sobre campos ForeignKey.

Contexto (RNF-03 · TEX-22 CA-3): __init__ toma el snapshot de
campos_auditables leyendo getattr(self, 'bodega_origen'), lo que carga el
objeto relacionado. Eso corre dentro de la construcción del modelo, ANTES de
que Django llene la caché de select_related, así que cada fila leída de la
base disparaba una consulta por FK auditable no nula (5005 consultas para un
kárdex de 5000 movimientos). El snapshot solo guarda el pk, que ya está en la
columna <fk>_id sin tocar la base.

Técnicas ISTQB:
- Caja blanca: rama ForeignKey de _get_auditable_data (consultas = 0).
- Particiones de equivalencia (EP): FK auditable cambiada / no cambiada — la
  auditoría debe seguir detectando el cambio de bodega tras la optimización.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from gestion.tests.factories import BodegaFactory, ProductoFactory, SedeFactory
from inventory.models import MovimientoInventario


class AuditableMixinSnapshotFKTestCase(TestCase):
    def setUp(self):
        sede = SedeFactory()
        self.bodega_a = BodegaFactory(sede=sede)
        self.bodega_b = BodegaFactory(sede=sede)
        self.mov = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=ProductoFactory(sede=sede),
            bodega_destino=self.bodega_a, cantidad=Decimal('10.000'),
        )

    def test_snapshot_auditable_dado_fk_no_nula_cuando_se_carga_desde_la_base_entonces_no_consulta_la_fk(self):
        # Una sola consulta: el SELECT del movimiento. Antes: 2 (la bodega_destino).
        with self.assertNumQueries(1):
            MovimientoInventario.objects.get(pk=self.mov.pk)

    def test_snapshot_auditable_dado_fk_cargada_cuando_se_toma_entonces_guarda_el_pk(self):
        mov = MovimientoInventario.objects.get(pk=self.mov.pk)
        self.assertEqual(mov._initial_state['bodega_destino'], self.bodega_a.pk)
        self.assertIsNone(mov._initial_state['bodega_origen'])

    def test_clean_auditable_dado_bodega_cambiada_sin_justificacion_cuando_valida_entonces_rechaza(self):
        mov = MovimientoInventario.objects.get(pk=self.mov.pk)
        mov.bodega_destino = self.bodega_b
        with self.assertRaises(ValidationError):
            mov.clean()
