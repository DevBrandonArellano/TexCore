"""
Pruebas de la Fase 1 de recetas versionadas de tintorería
(docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md §10).

Cubre: catálogo ProcesoTintoreria (unicidad de codigo por sede), MaquinaProceso,
Maquina.volumen_bano_litros, FaseReceta.proceso + ciclo, OrdenProduccion.formula_color
PROTECT y los endpoints /procesos-tintoreria/ y /maquinas/{id}/procesos/. (La prueba de
la migración de datos enum → proceso se retiró al unificar las migraciones, 1-oct-2026.)

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): misma sede / otra sede; proceso por id / por nombre legacy.
- Análisis de valores límite (BVA): volumen del baño nulo vs. valor decimal.
- Tabla de decisión (TD): rol × acción sobre los endpoints (operario / tintorero / admin).
- Caja blanca, cobertura de decisiones (CB-D): borrado de fórmula con y sin órdenes.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import (
    FaseReceta, FormulaColor, Maquina, MaquinaProceso, OrdenProduccion, ProcesoTintoreria,
)
from gestion.tests.factories import (
    AreaFactory, CustomUserFactory, FaseRecetaFactory, FormulaColorFactory, MaquinaFactory, OrdenProduccionFactory,
    ProcesoTintoreriaFactory, SedeFactory,
)


class ProcesoTintoreriaModelTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()

    def test_proceso_dado_codigo_repetido_en_misma_sede_cuando_guarda_entonces_error(self):
        # EP: partición inválida — mismo (codigo, sede)
        ProcesoTintoreriaFactory(codigo='DESCRUDE', sede=self.sede)
        with self.assertRaises(ValidationError):
            ProcesoTintoreriaFactory(codigo='DESCRUDE', sede=self.sede)

    def test_proceso_dado_codigo_repetido_en_otra_sede_cuando_guarda_entonces_se_permite(self):
        # EP: partición válida — el codigo es único por sede, no global
        ProcesoTintoreriaFactory(codigo='DESCRUDE', sede=self.sede)
        ProcesoTintoreriaFactory(codigo='DESCRUDE', sede=self.otra_sede)
        self.assertEqual(ProcesoTintoreria.objects.filter(codigo='DESCRUDE').count(), 2)


class MaquinaProcesoModelTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.maquina = MaquinaFactory(area=AreaFactory(sede=self.sede))
        self.proceso = ProcesoTintoreriaFactory(sede=self.sede)

    def test_maquinaproceso_dado_par_repetido_cuando_guarda_entonces_error(self):
        MaquinaProceso.objects.create(maquina=self.maquina, proceso=self.proceso)
        duplicado = MaquinaProceso(maquina=self.maquina, proceso=self.proceso)
        with self.assertRaises(ValidationError):
            duplicado.full_clean()

    def test_maquinaproceso_dado_proceso_de_otra_sede_cuando_clean_entonces_error(self):
        # EP: el proceso debe pertenecer a la sede del área de la máquina
        proceso_ajeno = ProcesoTintoreriaFactory(sede=SedeFactory())
        with self.assertRaises(ValidationError):
            MaquinaProceso(maquina=self.maquina, proceso=proceso_ajeno).full_clean()

    def test_maquinaproceso_dado_misma_sede_cuando_clean_entonces_valido(self):
        MaquinaProceso(maquina=self.maquina, proceso=self.proceso).full_clean()


class MaquinaVolumenBanoTestCase(TestCase):
    def test_maquina_dado_sin_volumen_cuando_crea_entonces_volumen_nulo(self):
        # BVA: el volumen es opcional (máquinas no-tintorería)
        maquina = MaquinaFactory()
        self.assertIsNone(maquina.volumen_bano_litros)

    def test_maquina_dado_volumen_bano_cuando_guarda_entonces_persiste_sin_tocar_capacidad(self):
        maquina = MaquinaFactory(capacidad_maxima=Decimal('500.00'), volumen_bano_litros=Decimal('1800.00'))
        maquina.refresh_from_db()
        self.assertEqual(maquina.volumen_bano_litros, Decimal('1800.00'))
        self.assertEqual(maquina.capacidad_maxima, Decimal('500.00'))
        self.assertIsInstance(maquina, Maquina)


class FaseRecetaProcesoTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.formula = FormulaColorFactory(sede=self.sede)
        self.proceso = ProcesoTintoreriaFactory(
            codigo='DESCRUDE', nombre='Descrude', tipo='pre_tratamiento', sede=self.sede)

    def test_fase_dado_proceso_y_ciclo_cuando_crea_entonces_los_persiste(self):
        fase = FaseReceta.objects.create(formula=self.formula, proceso=self.proceso, orden=1, ciclo=3)
        fase.refresh_from_db()
        self.assertEqual(fase.proceso, self.proceso)
        self.assertEqual(fase.ciclo, 3)
        self.assertIn('Descrude', str(fase))

    def test_fase_dado_sin_ciclo_cuando_crea_entonces_ciclo_nulo(self):
        # BVA: ciclo es opcional
        fase = FaseReceta.objects.create(formula=self.formula, proceso=self.proceso, orden=1)
        self.assertIsNone(fase.ciclo)

    def test_proceso_dado_fases_que_lo_usan_cuando_elimina_entonces_protegido(self):
        # CB-D: un proceso en uso por recetas no se puede borrar
        from django.db.models import ProtectedError
        FaseReceta.objects.create(formula=self.formula, proceso=self.proceso, orden=1)
        with self.assertRaises(ProtectedError):
            self.proceso.delete()


class FormulaColorProtectTestCase(TestCase):
    """CB-D: OrdenProduccion.formula_color pasa de CASCADE a PROTECT (hallazgo A-1)."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.formula = FormulaColorFactory(sede=self.sede)

    def test_formula_dado_orden_asociada_cuando_admin_elimina_entonces_409_y_orden_intacta(self):
        orden = OrdenProduccionFactory(formula_color=self.formula, sede=self.sede)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(
            reverse('formulacolor-detail', args=[self.formula.id]),
            HTTP_X_JUSTIFICACION_AUDITORIA='Fórmula obsoleta',
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('órdenes de producción asociadas', resp.data['error']['message'])
        self.assertTrue(OrdenProduccion.objects.filter(pk=orden.pk).exists())
        self.assertTrue(FormulaColor.objects.filter(pk=self.formula.pk).exists())

    def test_formula_dado_sin_ordenes_cuando_admin_elimina_entonces_204(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(
            reverse('formulacolor-detail', args=[self.formula.id]),
            HTTP_X_JUSTIFICACION_AUDITORIA='Fórmula obsoleta',
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_orden_dado_carga_diferida_cuando_instancia_entonces_no_recursa(self):
        # CB-D: el colector de borrado de Django carga los relacionados con .only();
        # AuditableModelMixin.__init__ no debe forzar la carga de campos diferidos.
        orden = OrdenProduccionFactory(formula_color=self.formula, sede=self.sede)
        diferida = OrdenProduccion.objects.only('id', 'formula_color').get(pk=orden.pk)
        self.assertEqual(diferida.pk, orden.pk)


class ProcesoTintoreriaApiTestCase(TestCase):
    """TD rol × acción sobre GET/POST /procesos-tintoreria/."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()
        self.operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        self.tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.url = reverse('procesotintoreria-list')
        self.payload = {'codigo': 'DESCRUDE', 'nombre': 'Descrude', 'tipo': 'pre_tratamiento'}

    def test_procesos_dado_operario_cuando_crea_entonces_403(self):
        self.client.force_authenticate(user=self.operario)
        resp = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ProcesoTintoreria.objects.exists())

    def test_procesos_dado_operario_cuando_lista_entonces_403(self):
        self.client.force_authenticate(user=self.operario)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_procesos_dado_tintorero_cuando_crea_entonces_201_con_su_sede(self):
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProcesoTintoreria.objects.get(pk=resp.data['id']).sede, self.sede)

    def test_procesos_dado_admin_cuando_crea_entonces_201(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_procesos_dado_codigo_repetido_en_su_sede_cuando_crea_entonces_400(self):
        ProcesoTintoreriaFactory(codigo='DESCRUDE', sede=self.sede)
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_procesos_dado_tintorero_cuando_lista_entonces_solo_ve_su_sede(self):
        propio = ProcesoTintoreriaFactory(sede=self.sede)
        ProcesoTintoreriaFactory(sede=self.otra_sede)
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        filas = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual([p['id'] for p in filas], [propio.id])

    def test_procesos_dado_filtro_activo_cuando_lista_entonces_excluye_inactivos(self):
        # EP: ?activo=true (partición válida) vs. procesos dados de baja
        activo = ProcesoTintoreriaFactory(sede=self.sede, activo=True)
        ProcesoTintoreriaFactory(sede=self.sede, activo=False)
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.get(self.url, {'activo': 'true'})
        filas = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual([p['id'] for p in filas], [activo.id])


class MaquinaProcesosApiTestCase(TestCase):
    """TD rol × acción sobre GET /maquinas/{id}/procesos/."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.maquina = MaquinaFactory(area=AreaFactory(sede=self.sede), volumen_bano_litros=Decimal('1800'))
        self.asignado = ProcesoTintoreriaFactory(sede=self.sede, codigo='DESCRUDE')
        ProcesoTintoreriaFactory(sede=self.sede, codigo='NO-ASIGNADO')
        MaquinaProceso.objects.create(maquina=self.maquina, proceso=self.asignado)
        self.url = reverse('maquina-procesos', args=[self.maquina.id])

    def test_maquina_procesos_dado_operario_cuando_consulta_entonces_403(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=['operario']))
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_maquina_procesos_dado_tintorero_cuando_consulta_entonces_solo_asignados(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=['tintorero']))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([p['codigo'] for p in resp.data], ['DESCRUDE'])

    def test_maquina_dado_volumen_bano_cuando_consulta_detalle_entonces_lo_expone(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=['tintorero']))
        resp = self.client.get(reverse('maquina-detail', args=[self.maquina.id]))
        self.assertEqual(Decimal(resp.data['volumen_bano_litros']), Decimal('1800'))


class FormulaFasesProcesoApiTestCase(TestCase):
    """EP: la fase se indica por `proceso` (id); el `nombre` del antiguo enum ya no se acepta
    (compatibilidad de Fase 1 retirada al migrar el frontend en la Fase 2)."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.client.force_authenticate(user=self.tintorero)
        self.url = reverse('formulacolor-list')

    def _payload(self, fase):
        return {'codigo': 'F-001', 'nombre_color': 'Azul', 'fases': [dict({'orden': 1, 'detalles': []}, **fase)]}

    def test_formula_dado_solo_nombre_legacy_cuando_crea_entonces_400_y_no_crea(self):
        resp = self.client.post(self.url, self._payload({'nombre': 'tintura'}), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(FormulaColor.objects.filter(codigo='F-001').exists())

    def test_formula_dado_proceso_y_ciclo_cuando_crea_entonces_201(self):
        proceso = ProcesoTintoreriaFactory(codigo='DESCRUDE', sede=self.sede)
        resp = self.client.post(self.url, self._payload({'proceso': proceso.id, 'ciclo': 3}), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        fase = FaseReceta.objects.get(formula_id=resp.data['id'])
        self.assertEqual((fase.proceso, fase.ciclo), (proceso, 3))

    def test_formula_dado_proceso_de_otra_sede_cuando_crea_entonces_400(self):
        ajeno = ProcesoTintoreriaFactory(sede=SedeFactory())
        resp = self.client.post(self.url, self._payload({'proceso': ajeno.id}), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_formula_dado_fase_sin_proceso_ni_nombre_cuando_crea_entonces_400(self):
        resp = self.client.post(self.url, self._payload({}), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_formula_dado_fase_con_proceso_cuando_consulta_entonces_expone_proceso_sin_campos_legacy(self):
        formula = FormulaColorFactory(sede=self.sede)
        FaseRecetaFactory(formula=formula, nombre='lavado', ciclo=2)
        resp = self.client.get(reverse('formulacolor-detail', args=[formula.id]))
        fase = resp.data['fases'][0]
        self.assertEqual((fase['proceso_codigo'], fase['proceso_nombre']), ('LAVADO', 'Lavado / Jabonado'))
        self.assertEqual(fase['ciclo'], 2)
        self.assertNotIn('nombre', fase)
        self.assertNotIn('nombre_display', fase)

    def test_formula_dado_fase_con_proceso_cuando_duplica_entonces_copia_proceso_y_ciclo(self):
        formula = FormulaColorFactory(sede=self.sede)
        original = FaseRecetaFactory(formula=formula, nombre='lavado', ciclo=2)
        resp = self.client.post(reverse('formulacolor-duplicar', args=[formula.id]),
                                {'codigo': 'VAR-001', 'nombre_color': 'Variante'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        copia = FaseReceta.objects.get(formula_id=resp.data['id'])
        self.assertEqual((copia.proceso, copia.ciclo), (original.proceso, 2))

    def test_formula_dado_fase_con_proceso_cuando_exporta_dosificador_entonces_usa_nombre_proceso(self):
        formula = FormulaColorFactory(sede=self.sede)
        FaseRecetaFactory(formula=formula, nombre='lavado', ciclo=2)
        resp = self.client.get(reverse('formulacolor-exportar-dosificador', args=[formula.id]))
        self.assertEqual(resp.data['phases'][0]['phase_name'], 'Lavado / Jabonado')
        self.assertEqual(resp.data['phases'][0]['cycle'], 2)
