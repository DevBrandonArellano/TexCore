"""
Tests F1: Modelo EventoEtiqueta + snapshot ORIGINAL en registro de lote.
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-GestionEtiquetas (reetiquetado/reimpresión)

Técnicas ISTQB: EP (evento ORIGINAL vs REIMPRESION vs REETIQUETADO),
BVA (unique_together lote+version), regla de negocio (codigo_lote inmutable).
"""
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from gestion.models import (
    CustomUser, Sede, Producto, Bodega, OrdenProduccion, LoteProduccion, EventoEtiqueta,
)
from gestion.services.evento_etiqueta_service import EventoEtiquetaService
from gestion.services.registro_lote import RegistroLoteService


def _fixtures(tc):
    tc.sede = Sede.objects.create(nombre='Sede Etiquetas', location='Quito')
    tc.usuario = CustomUser.objects.create_user(username='empacador1', password='pass')
    tc.producto_hilo = Producto.objects.create(
        codigo='H-ET1', descripcion='Hilo Crudo', tipo='hilo',
        unidad_medida='kg', precio_base=Decimal('8.00'), sede=tc.sede,
    )
    tc.producto_tela = Producto.objects.create(
        codigo='T-ET1', descripcion='Tela Jersey', tipo='tela',
        unidad_medida='kg', precio_base=Decimal('15.00'), sede=tc.sede,
    )
    tc.bodega_entrada = Bodega.objects.create(nombre='Bodega Entrada ET', sede=tc.sede)
    tc.bodega_salida = Bodega.objects.create(nombre='Bodega Salida ET', sede=tc.sede)


def _crear_orden(tc, codigo='OP-ET-1'):
    return OrdenProduccion.objects.create(
        codigo=codigo,
        producto_entrada=tc.producto_hilo,
        producto_salida=tc.producto_tela,
        bodega_entrada=tc.bodega_entrada,
        bodega_salida=tc.bodega_salida,
        peso_neto_requerido=Decimal('100.00'),
        sede=tc.sede,
    )


def _crear_lote(tc, orden, codigo='LP-ET-1'):
    ahora = timezone.now()
    return LoteProduccion.objects.create(
        orden_produccion=orden,
        codigo_lote=codigo,
        peso_neto_producido=Decimal('95.000'),
        operario=tc.usuario,
        turno='Dia',
        hora_inicio=ahora - timedelta(hours=2),
        hora_final=ahora,
    )


class EventoEtiquetaModelTests(TestCase):
    def setUp(self):
        _fixtures(self)
        self.orden = _crear_orden(self)
        self.lote = _crear_lote(self, self.orden)

    def test_crea_evento_original_version_1(self):
        evento = EventoEtiqueta.objects.create(
            lote=self.lote,
            tipo_evento='ORIGINAL',
            secuencia=1,
            version=1,
            usuario=self.usuario,
            datos_snapshot={'peso_neto_producido': '95.000'},
            formato='ZPL',
        )
        self.assertEqual(evento.version, 1)
        self.assertFalse(evento.anulada)
        self.assertIsNone(evento.anula_a)
        self.assertEqual(str(evento), f'{self.lote.codigo_lote} v1 #1 (ORIGINAL)')

    def test_unique_together_lote_secuencia(self):
        EventoEtiqueta.objects.create(
            lote=self.lote, tipo_evento='ORIGINAL', secuencia=1, version=1, datos_snapshot={}
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EventoEtiqueta.objects.create(
                    lote=self.lote, tipo_evento='REIMPRESION', secuencia=1, version=1, datos_snapshot={}
                )

    def test_reimpresion_mantiene_version_de_datos(self):
        EventoEtiquetaService.registrar_original(self.lote, self.usuario)
        reimpresion1 = EventoEtiquetaService.registrar_reimpresion(
            self.lote, self.usuario, motivo='DANIADA', detalle_motivo='Etiqueta dañada en despacho'
        )
        reimpresion2 = EventoEtiquetaService.registrar_reimpresion(
            self.lote, self.usuario, motivo='PERDIDA'
        )
        self.assertEqual(reimpresion1.version, 1)
        self.assertEqual(reimpresion1.secuencia, 2)
        self.assertEqual(reimpresion2.version, 1)
        self.assertEqual(reimpresion2.secuencia, 3)
        self.assertEqual(self.lote.etiquetas.count(), 3)

    def test_reetiquetado_anula_version_previa(self):
        original = EventoEtiquetaService.registrar_original(self.lote, self.usuario)

        reetiquetado = EventoEtiquetaService.registrar_reetiquetado(
            self.lote, self.usuario, motivo='CORRECCION_PESO',
            detalle_motivo='Corrección de peso tras re-pesaje',
        )

        original.refresh_from_db()
        self.assertTrue(original.anulada)
        self.assertEqual(reetiquetado.anula_a, original)
        self.assertEqual(reetiquetado.version, 2)
        self.assertEqual(reetiquetado.secuencia, 2)
        self.assertEqual(self.lote.etiquetas.count(), 2)

    def test_codigo_lote_no_cambia_tras_reetiquetado(self):
        codigo_original = self.lote.codigo_lote
        EventoEtiquetaService.registrar_original(self.lote, self.usuario)
        EventoEtiquetaService.registrar_reetiquetado(
            self.lote, self.usuario, motivo='RECLASIFICACION'
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.codigo_lote, codigo_original)


class RegistroLoteEventoOriginalTests(TestCase):
    """El registro de un lote nuevo debe crear automáticamente el EventoEtiqueta ORIGINAL v1."""

    def setUp(self):
        _fixtures(self)
        self.orden = _crear_orden(self, codigo='OP-ET-2')

    def test_registrar_lote_crea_evento_original(self):
        from inventory.models import StockBodega
        StockBodega.objects.create(
            bodega=self.bodega_entrada, producto=self.producto_hilo, lote=None,
            cantidad=Decimal('200.00')
        )
        ahora = timezone.now()
        lote = RegistroLoteService.registrar_lote(
            orden=self.orden,
            lote_data={
                'peso_neto_producido': Decimal('95.000'),
                'turno': 'Dia',
                'hora_inicio': ahora - timedelta(hours=2),
                'hora_final': ahora,
            },
            user=self.usuario,
        )
        eventos = EventoEtiqueta.objects.filter(lote=lote)
        self.assertEqual(eventos.count(), 1)
        evento = eventos.first()
        self.assertEqual(evento.tipo_evento, 'ORIGINAL')
        self.assertEqual(evento.version, 1)
        self.assertEqual(evento.usuario, self.usuario)
        self.assertIn('peso_neto_producido', evento.datos_snapshot)
