"""
GenealogiaService (gestion/services/genealogia_service.py): trazabilidad hacia atrás y hacia adelante.

Defecto encontrado el 9-nov-2026 al revisar la cobertura del servicio: la materia prima que un
lote consume por la vía oficial (ConsumoMateriaPrima, F0-001) nunca aparecía en la trazabilidad
hacia atrás. El servicio buscaba la relación `consumos_materias_primas` y el campo `materia_prima`,
pero el modelo los llama `consumos_materia_prima` y `materia_prima_lote`; el `hasattr` daba
siempre False y lo ocultaba. Hacia adelante desde un lote de materia prima, la misma relación
lanzaba FieldError.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): referencia por instancia / id / código / tipo inválido;
  materia prima por vínculo directo / por consumo; despacho por historial / por kárdex.
- Análisis de valores límite (BVA): profundidad máxima 0 (solo la raíz).
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestion.models import GenealogiaLote, LoteProduccion
from gestion.services.genealogia_service import GenealogiaService
from gestion.services.materia_prima_service import MateriaPrimaService
from gestion.tests.factories import (
    BodegaFactory,
    CustomUserFactory,
    OperacionProduccionFactory,
    ProductoFactory,
    ProveedorFactory,
    SedeFactory,
)
from inventory.models import MovimientoInventario


class _BaseGenealogia(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.usuario = CustomUserFactory(sede=self.sede)
        self.bodega = BodegaFactory(sede=self.sede)
        self.hilo = ProductoFactory(tipo="hilo", sede=self.sede)
        self.tela = ProductoFactory(tipo="tela", sede=self.sede)

    def _lote(self, codigo, producto=None, **extra):
        ahora = timezone.now()
        return LoteProduccion.objects.create(
            codigo_lote=codigo,
            producto=producto or self.tela,
            peso_neto_producido=Decimal("50.000"),
            turno="Mañana",
            hora_inicio=ahora,
            hora_final=ahora,
            **extra,
        )

    def _materia_prima(self, lote_proveedor):
        return MateriaPrimaService.registrar_entrada(
            proveedor=ProveedorFactory(sede=self.sede, nombre=f"Proveedor {lote_proveedor}"),
            producto=self.hilo,
            lote_proveedor=lote_proveedor,
            cantidad_kg=Decimal("100.000"),
            costo_unitario=Decimal("5.000"),
            bodega_recepcion=self.bodega,
            fecha_recepcion=date(2026, 10, 1),
            usuario=self.usuario,
        )

    def _consumir(self, lote, mp, cantidad="20.000"):
        MateriaPrimaService.consumir_materia_prima(
            lote_produccion=lote,
            consumos_data=[{"materia_prima_lote_id": mp.id, "cantidad_kg": Decimal(cantidad)}],
            usuario=self.usuario,
        )


class TrazabilidadHaciaAtrasMateriaPrimaTest(_BaseGenealogia):
    def test_atras_dado_lote_que_consumio_materia_prima_cuando_traza_entonces_la_lista_como_origen(self):
        lote = self._lote("LOT-CONSUME-MP")
        mp = self._materia_prima("PROV-HILO-01")
        self._consumir(lote, mp)

        grafo = GenealogiaService.obtener_trazabilidad_hacia_atras(lote)

        self.assertEqual([m["id"] for m in grafo["materias_primas_origen"]], [mp.id])
        origen = grafo["materias_primas_origen"][0]
        self.assertEqual(
            (origen["lote_proveedor"], origen["asociado_a_lote_codigo"]), ("PROV-HILO-01", "LOT-CONSUME-MP")
        )

    def test_atras_dado_mp_por_vinculo_directo_y_por_consumo_cuando_traza_entonces_cada_una_una_vez(self):
        mp_directa = self._materia_prima("PROV-DIRECTA")
        mp_consumida = self._materia_prima("PROV-CONSUMIDA")
        lote = self._lote("LOT-DOS-MP", materia_prima_lote=mp_directa)
        self._consumir(lote, mp_consumida)
        self._consumir(lote, mp_directa, cantidad="5.000")

        grafo = GenealogiaService.obtener_trazabilidad_hacia_atras(lote)

        self.assertEqual(
            sorted(m["id"] for m in grafo["materias_primas_origen"]), sorted([mp_directa.id, mp_consumida.id])
        )
        self.assertEqual(grafo["total_materias_primas"], 2)

    def test_atras_dado_profundidad_cero_cuando_traza_entonces_no_recorre_los_padres(self):
        padre = self._lote("LOT-PADRE", producto=self.hilo)
        hijo = self._lote("LOT-HIJO")
        GenealogiaLote.objects.create(
            lote_padre=padre,
            lote_hijo=hijo,
            cantidad_padre_usada=Decimal("10.000"),
            operacion=OperacionProduccionFactory(),
        )

        self.assertEqual(
            GenealogiaService.obtener_trazabilidad_hacia_atras(hijo, profundidad_maxima=0)["ancestros"], []
        )
        self.assertEqual(
            [a["codigo_lote"] for a in GenealogiaService.obtener_trazabilidad_hacia_atras(hijo)["ancestros"]],
            ["LOT-PADRE"],
        )


class TrazabilidadHaciaAdelanteDesdeMateriaPrimaTest(_BaseGenealogia):
    def test_adelante_dado_lote_de_mp_consumido_cuando_traza_entonces_llega_a_su_venta(self):
        mp = self._materia_prima("PROV-RECALL")
        lote = self._lote("LOT-DERIVADO")
        self._consumir(lote, mp)
        venta = MovimientoInventario.objects.create(
            tipo_movimiento="VENTA",
            producto=self.tela,
            lote=lote,
            bodega_origen=self.bodega,
            cantidad=Decimal("20.000"),
            documento_ref="Despacho #77",
        )

        recall = GenealogiaService.obtener_trazabilidad_hacia_adelante(mp)

        self.assertEqual(recall["nodo_raiz"]["lote_proveedor"], "PROV-RECALL")
        self.assertEqual([d.get("movimiento_kardex_id") for d in recall["despachos_clientes"]], [venta.id])

    def test_adelante_dado_mp_sin_lotes_derivados_cuando_traza_entonces_resultado_vacio_con_la_raiz(self):
        mp = self._materia_prima("PROV-SIN-USO")

        recall = GenealogiaService.obtener_trazabilidad_hacia_adelante(mp)

        self.assertEqual(recall["nodo_raiz"]["id"], mp.id)
        self.assertEqual((recall["descendientes"], recall["total_clientes_afectados"]), ([], 0))

    def test_adelante_dado_profundidad_cero_cuando_traza_entonces_no_recorre_los_hijos(self):
        padre = self._lote("LOT-P-ADEL", producto=self.hilo)
        hijo = self._lote("LOT-H-ADEL")
        GenealogiaLote.objects.create(
            lote_padre=padre,
            lote_hijo=hijo,
            cantidad_padre_usada=Decimal("10.000"),
            operacion=OperacionProduccionFactory(),
        )

        self.assertEqual(GenealogiaService.obtener_trazabilidad_hacia_adelante(padre, 0)["descendientes"], [])
        self.assertEqual(GenealogiaService.obtener_trazabilidad_hacia_adelante(padre)["total_descendientes"], 1)


class ResolverLoteTest(_BaseGenealogia):
    def test_resolver_dado_id_o_codigo_existente_cuando_resuelve_entonces_el_mismo_lote(self):
        lote = self._lote("LOT-RESOLVER")
        self.assertEqual(GenealogiaService.resolver_lote(lote.id), lote)
        self.assertEqual(GenealogiaService.resolver_lote("LOT-RESOLVER"), lote)

    def test_resolver_dado_referencia_inexistente_o_invalida_cuando_resuelve_entonces_validation_error(self):
        for referencia, mensaje in ((999999, "ID 999999"), ("NO-EXISTE", "'NO-EXISTE'"), (1.5, "no válida")):
            with self.subTest(referencia=referencia), self.assertRaisesMessage(ValidationError, mensaje):
                GenealogiaService.resolver_lote(referencia)
