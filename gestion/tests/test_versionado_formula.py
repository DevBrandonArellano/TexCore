"""
Pruebas de las Fases 2 y 4 de recetas versionadas de tintorería
(docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md
§5.5, §6 reglas 1-5 y 13, §7, decisiones D7-D9).

Técnicas ISTQB aplicadas:
- Transición de estados (STT): en_pruebas -> version creada -> version marcada oficial;
  OP pendiente -> en_proceso.
- Tabla de decisión (TD): como máximo una oficial por fórmula; rol x acción.
- Caja blanca, cobertura de decisiones (CB-D): inmutabilidad de la versión (update/delete rechazados).
- Partición de equivalencia (EP): producto renombrado o dado de baja, la versión sigue legible;
  fórmula con varios ensayos y ninguna oficial es estado válido.
- Análisis de valores límite (BVA): observaciones/motivo de 9 / 10 caracteres.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import FormulaColor, OrdenProduccion, VersionFormula
from gestion.services.versionado_formula import VersionadoFormulaService
from gestion.tests.factories import (
    CustomUserFactory, DetalleFormulaFactory, FaseRecetaFactory, FormulaColorFactory, OrdenProduccionFactory,
    ProductoFactory, SedeFactory,
)


class VersionFormulaModelTestCase(TestCase):
    def setUp(self):
        self.formula = FormulaColorFactory(sede=SedeFactory(), estado='en_pruebas')

    def _version(self, numero, es_oficial=False, motivo='Aprobación de laboratorio', observaciones=''):
        return VersionFormula.objects.create(
            formula=self.formula, numero=numero, snapshot={'formula': {}, 'fases': []},
            motivo=motivo, observaciones=observaciones, es_oficial=es_oficial)

    def test_version_dado_numero_repetido_en_misma_formula_cuando_guarda_entonces_error(self):
        self._version(1)
        with self.assertRaises(ValidationError):
            self._version(1)

    def test_version_dado_segunda_oficial_en_misma_formula_cuando_guarda_en_bd_entonces_integrity_error(self):
        # TD: la restricción de BD (UniqueConstraint condicional) impide dos oficiales
        self._version(1, es_oficial=True)
        segunda = VersionFormula(formula=self.formula, numero=2, snapshot={}, motivo='Otra versión oficial',
                                 es_oficial=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            # save_base salta full_clean: prueba la restricción de BD, no la del modelo
            segunda.save_base()

    def test_version_dado_motivo_de_9_caracteres_cuando_guarda_entonces_error(self):
        # BVA: el motivo exige mínimo 10 caracteres
        with self.assertRaises(ValidationError):
            self._version(1, motivo='123456789')

    def test_version_dado_motivo_de_10_caracteres_cuando_guarda_entonces_valida(self):
        self.assertEqual(self._version(1, motivo='1234567890').motivo, '1234567890')

    def test_version_dado_existente_cuando_modifica_snapshot_entonces_error(self):
        # CB-D: el contenido de una versión es inmutable
        version = self._version(1)
        version.snapshot = {'formula': {'codigo': 'OTRA'}, 'fases': []}
        with self.assertRaises(ValidationError):
            version.save()

    def test_version_dado_existente_cuando_modifica_observaciones_entonces_error(self):
        # CB-D: observaciones también es inmutable (D7 — es parte de la foto del ensayo)
        version = self._version(1, observaciones='Ensayo inicial de color')
        version.observaciones = 'Cambié de opinión'
        with self.assertRaises(ValidationError):
            version.save()

    def test_version_dado_existente_cuando_desmarca_oficial_entonces_se_permite(self):
        # es_oficial es el único campo mutable: marcar otra versión oficial la desmarca
        version = self._version(1, es_oficial=True)
        version.es_oficial = False
        version.save()
        version.refresh_from_db()
        self.assertFalse(version.es_oficial)

    def test_version_dado_existente_cuando_elimina_entonces_error(self):
        version = self._version(1)
        with self.assertRaises(ValidationError):
            version.delete()


class VersionadoFormulaServiceTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.usuario = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.formula = FormulaColorFactory(sede=self.sede, estado='en_pruebas', codigo='PES-T0191')
        self.fase = FaseRecetaFactory(formula=self.formula, nombre='pre_tratamiento', orden=1, ciclo=3,
                                      temperatura=70, tiempo=20)
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede, codigo='Q00610', descripcion='FORYL FKN')
        DetalleFormulaFactory(fase=self.fase, producto=self.quimico, tipo_calculo='gr_l',
                              concentracion_gr_l=Decimal('0.700'), orden_adicion=1)

    def test_snapshot_dado_receta_cuando_construye_entonces_sigue_el_esquema_del_spec(self):
        snap = VersionadoFormulaService.construir_snapshot(self.formula)
        self.assertEqual(snap['formula']['codigo'], 'PES-T0191')
        fase = snap['fases'][0]
        self.assertEqual((fase['orden'], fase['proceso_codigo'], fase['proceso_tipo'], fase['ciclo']),
                         (1, 'PRE_TRATAMIENTO', 'pre_tratamiento', 3))
        self.assertEqual((fase['temperatura'], fase['tiempo']), (70, 20))
        detalle = fase['detalles'][0]
        self.assertEqual(detalle['producto_id'], self.quimico.id)
        self.assertEqual((detalle['producto_codigo'], detalle['producto_descripcion']), ('Q00610', 'FORYL FKN'))
        self.assertEqual((detalle['tipo_calculo'], detalle['concentracion_gr_l'], detalle['porcentaje']),
                         ('gr_l', '0.700', None))

    # --- crear_version (regla 1, D7): siempre no oficial, sin importar el estado ---
    def test_formula_dado_en_pruebas_cuando_crea_version_entonces_v1_no_oficial_y_sigue_en_pruebas(self):
        version = VersionadoFormulaService.crear_version(self.formula, 'Primer ensayo de laboratorio', self.usuario)
        self.formula.refresh_from_db()
        self.assertEqual((version.numero, version.es_oficial, version.creada_por), (1, False, self.usuario))
        self.assertEqual((self.formula.estado, self.formula.versiones.count()), ('en_pruebas', 1))

    def test_formula_dado_observaciones_cortas_cuando_crea_version_entonces_error_y_no_crea_nada(self):
        # BVA: observaciones/motivo exige mínimo 10 caracteres (validador del modelo)
        with self.assertRaises(ValidationError):
            VersionadoFormulaService.crear_version(self.formula, 'corto', self.usuario)
        self.formula.refresh_from_db()
        self.assertEqual(self.formula.estado, 'en_pruebas')
        self.assertFalse(self.formula.versiones.exists())

    def test_formula_dado_en_desarrollo_cuando_crea_varios_ensayos_entonces_ninguno_es_oficial(self):
        # EP: una fórmula con 3 ensayos y ninguna oficial es un estado válido (D7)
        VersionadoFormulaService.crear_version(self.formula, 'Ensayo 1: sale muy rojizo', self.usuario)
        VersionadoFormulaService.crear_version(self.formula, 'Ensayo 2: falta igualación', self.usuario)
        v3 = VersionadoFormulaService.crear_version(self.formula, 'Ensayo 3: mejor resultado', self.usuario)
        self.formula.refresh_from_db()
        self.assertEqual(self.formula.versiones.count(), 3)
        self.assertFalse(self.formula.versiones.filter(es_oficial=True).exists())
        self.assertEqual(v3.numero, 3)

    # --- marcar_oficial (reglas 3-5) ---
    def test_formula_dado_version_creada_cuando_marca_oficial_entonces_queda_aprobada(self):
        version = VersionadoFormulaService.crear_version(self.formula, 'Ensayo aprobado en laboratorio', self.usuario)
        oficial = VersionadoFormulaService.marcar_oficial(self.formula, version.numero, self.usuario)
        self.formula.refresh_from_db()
        oficial.refresh_from_db()
        self.assertTrue(oficial.es_oficial)
        self.assertEqual((self.formula.estado, self.formula.version), ('aprobada', 1))

    def test_formula_dado_oficial_vigente_cuando_crea_otro_ensayo_entonces_se_permite_y_no_la_afecta(self):
        # Regla 4: se puede seguir ensayando con una oficial vigente
        v1 = VersionadoFormulaService.crear_version(self.formula, 'Ensayo original', self.usuario)
        VersionadoFormulaService.marcar_oficial(self.formula, v1.numero, self.usuario)
        self.fase.temperatura = 80
        self.fase.save()
        v2 = VersionadoFormulaService.crear_version(self.formula, 'Nuevo ensayo con la oficial vigente', self.usuario)
        v1.refresh_from_db()
        self.formula.refresh_from_db()
        self.assertFalse(v2.es_oficial)
        self.assertTrue(v1.es_oficial)
        self.assertEqual(self.formula.version, 1)

    def test_formula_dado_dos_ensayos_cuando_marca_el_segundo_oficial_entonces_reemplaza_al_primero(self):
        v1 = VersionadoFormulaService.crear_version(self.formula, 'Primer ensayo', self.usuario)
        VersionadoFormulaService.marcar_oficial(self.formula, v1.numero, self.usuario)
        snapshot_v1 = v1.snapshot
        self.fase.temperatura = 80
        self.fase.save()
        v2 = VersionadoFormulaService.crear_version(self.formula, 'Segundo ensayo, mejor resultado', self.usuario)
        VersionadoFormulaService.marcar_oficial(self.formula, v2.numero, self.usuario)
        v1.refresh_from_db()
        v2.refresh_from_db()
        self.formula.refresh_from_db()
        self.assertEqual((v2.es_oficial, v1.es_oficial), (True, False))
        self.assertEqual(v1.snapshot, snapshot_v1)
        self.assertEqual(v1.snapshot['fases'][0]['temperatura'], 70)
        self.assertEqual(v2.snapshot['fases'][0]['temperatura'], 80)
        self.assertEqual(self.formula.version, 2)

    def test_formula_dado_version_anterior_cuando_se_vuelve_a_marcar_oficial_entonces_se_permite(self):
        # Regla 5: se puede volver a una versión anterior marcándola oficial de nuevo
        v1 = VersionadoFormulaService.crear_version(self.formula, 'Primer ensayo', self.usuario)
        VersionadoFormulaService.marcar_oficial(self.formula, v1.numero, self.usuario)
        v2 = VersionadoFormulaService.crear_version(self.formula, 'Segundo ensayo', self.usuario)
        VersionadoFormulaService.marcar_oficial(self.formula, v2.numero, self.usuario)
        vuelta = VersionadoFormulaService.marcar_oficial(self.formula, v1.numero, self.usuario)
        v2.refresh_from_db()
        self.assertEqual(vuelta.numero, 1)
        self.assertTrue(vuelta.es_oficial)
        self.assertFalse(v2.es_oficial)

    # --- asegurar_version_oficial (seeders y datos de demostración) ---
    def test_asegurar_dado_en_pruebas_cuando_asegura_entonces_aprueba_con_v1(self):
        version = VersionadoFormulaService.asegurar_version_oficial(self.formula, 'Versión inicial migrada', None)
        self.formula.refresh_from_db()
        self.assertEqual((version.numero, version.es_oficial, self.formula.estado), (1, True, 'aprobada'))

    def test_asegurar_dado_aprobada_sin_versiones_cuando_asegura_entonces_crea_v1_oficial(self):
        # Fórmulas aprobadas antes del versionado (estado cambiado a mano, sin VersionFormula)
        FormulaColor.objects.filter(pk=self.formula.pk).update(estado='aprobada')
        version = VersionadoFormulaService.asegurar_version_oficial(self.formula, 'Versión inicial migrada', None)
        self.assertEqual((version.numero, version.es_oficial), (1, True))
        self.assertEqual(version.snapshot['formula']['codigo'], 'PES-T0191')

    def test_asegurar_dado_ya_con_version_oficial_cuando_asegura_entonces_no_crea_otra(self):
        v1 = VersionadoFormulaService.asegurar_version_oficial(self.formula, 'Versión inicial migrada', self.usuario)
        version = VersionadoFormulaService.asegurar_version_oficial(self.formula, 'Otro intento', None)
        self.assertEqual(version, v1)
        self.assertEqual(self.formula.versiones.count(), 1)

    def test_version_dado_producto_renombrado_y_de_baja_cuando_consulta_entonces_sigue_legible(self):
        # EP: el snapshot guarda código y descripción, no depende del producto vivo
        version = VersionadoFormulaService.asegurar_version_oficial(
            self.formula, 'Aprobada tras prueba de laboratorio', self.usuario)
        self.quimico.descripcion = 'NOMBRE NUEVO'
        self.quimico.save()
        version.refresh_from_db()
        detalle = version.snapshot['fases'][0]['detalles'][0]
        self.assertEqual((detalle['producto_codigo'], detalle['producto_descripcion']), ('Q00610', 'FORYL FKN'))
        # Baja del producto (Producto no tiene flag de baja: se elimina)
        type(self.quimico).objects.filter(pk=self.quimico.pk).delete()
        version.refresh_from_db()
        self.assertEqual(version.snapshot['fases'][0]['detalles'][0]['producto_descripcion'], 'FORYL FKN')


class DerivacionFormulaServiceTestCase(TestCase):
    """Reglas 6-7 (§5.7, D8-D9): derivar crea una fórmula nueva a partir del snapshot
    de una versión concreta (oficial o ensayo) de otra."""

    def setUp(self):
        self.sede = SedeFactory()
        self.usuario = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.origen = FormulaColorFactory(sede=self.sede, estado='en_pruebas', codigo='ORIG-001',
                                          tipo_sustrato='poliester')
        self.fase = FaseRecetaFactory(formula=self.origen, nombre='tintura', orden=1, temperatura=90)
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        DetalleFormulaFactory(fase=self.fase, producto=self.quimico, tipo_calculo='gr_l',
                              concentracion_gr_l=Decimal('5.000'))
        self.version = VersionadoFormulaService.crear_version(self.origen, 'Ensayo base para derivar', self.usuario)

    def test_derivar_dado_version_de_origen_cuando_deriva_entonces_copia_receta_y_guarda_lineage(self):
        derivada = VersionadoFormulaService.derivar(
            self.origen, self.version,
            {'codigo': 'DERIV-001', 'nombre_color': 'Derivada Acrílico', 'tipo_sustrato': 'nylon',
             'motivo_derivacion': 'Cambio de sustrato a nylon', 'es_laboratorio': False},
            self.usuario,
        )
        self.assertEqual((derivada.formula_origen, derivada.version_origen), (self.origen, self.version))
        self.assertEqual((derivada.tipo_sustrato, derivada.estado), ('nylon', 'en_pruebas'))
        self.assertFalse(derivada.versiones.exists())
        self.assertEqual(derivada.fases.count(), 1)
        detalle = derivada.fases.get().detalles.get()
        self.assertEqual(detalle.producto_id, self.quimico.id)
        self.assertEqual(detalle.concentracion_gr_l, Decimal('5.000'))

    def test_derivar_dado_es_laboratorio_cuando_deriva_entonces_se_marca_como_tal(self):
        derivada = VersionadoFormulaService.derivar(
            self.origen, self.version,
            {'codigo': 'LAB-001', 'nombre_color': 'Prueba Lab', 'es_laboratorio': True},
            self.usuario,
        )
        self.assertTrue(derivada.es_laboratorio)

    def test_derivar_dado_receta_original_editada_despues_cuando_deriva_entonces_no_afecta_al_origen(self):
        derivada = VersionadoFormulaService.derivar(
            self.origen, self.version,
            {'codigo': 'DERIV-002', 'nombre_color': 'Otra Derivada'},
            self.usuario,
        )
        derivada.fases.get().delete()
        self.origen.refresh_from_db()
        self.assertEqual(self.origen.fases.count(), 1)


class VersionadoFormulaApiTestCase(TestCase):
    """Endpoints de §7 y reglas 1, 3-5 y 13 a través de la API."""
    OBSERVACIONES = 'Aprobada tras prueba de laboratorio'

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        self.formula = FormulaColorFactory(sede=self.sede, estado='en_pruebas')
        self.fase = FaseRecetaFactory(formula=self.formula, nombre='tintura', orden=1, temperatura=90)
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        DetalleFormulaFactory(fase=self.fase, producto=self.quimico, concentracion_gr_l=Decimal('10.000'))
        self.client.force_authenticate(user=self.tintorero)

    def _url(self, nombre, *args):
        return reverse(f'formulacolor-{nombre}', args=[self.formula.id, *args])

    def _payload(self, temperatura=90, **extra):
        return dict({
            'codigo': self.formula.codigo, 'nombre_color': self.formula.nombre_color,
            'estado': self.formula.estado,
            'fases': [{'proceso': self.fase.proceso_id, 'orden': 1, 'temperatura': temperatura, 'detalles': [
                {'producto': self.quimico.id, 'tipo_calculo': 'gr_l', 'concentracion_gr_l': '10.000',
                 'orden_adicion': 1}]}],
        }, **extra)

    def _crear_version(self, observaciones=None):
        resp = self.client.post(self._url('versiones'), {'observaciones': observaciones or self.OBSERVACIONES},
                                format='json')
        self.formula.refresh_from_db()
        return resp

    def _marcar_oficial(self, numero):
        resp = self.client.post(self._url('marcar-oficial', numero), {}, format='json')
        self.formula.refresh_from_db()
        return resp

    def _aprobar(self):
        """Ensayo + marcar oficial en un solo paso, para los tests que solo necesitan
        una fórmula ya aprobada sin importarles la mecánica de las dos acciones."""
        resp = self._crear_version()
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        return self._marcar_oficial(resp.data['numero'])

    # --- crear_version (regla 1, D7) y permisos (regla 13) ---
    def test_crear_version_dado_tintorero_cuando_crea_entonces_201_v1_no_oficial(self):
        resp = self._crear_version()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual((resp.data['numero'], resp.data['es_oficial']), (1, False))
        self.assertEqual(self.formula.estado, 'en_pruebas')

    def test_crear_version_dado_operario_cuando_crea_entonces_403(self):
        self.client.force_authenticate(user=self.operario)
        self.assertEqual(self._crear_version().status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(self.formula.versiones.exists())

    def test_crear_version_dado_observaciones_cortas_cuando_crea_entonces_400(self):
        resp = self._crear_version(observaciones='corto')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crear_version_dado_ya_con_oficial_cuando_crea_otra_entonces_201_y_no_la_reemplaza(self):
        # Regla 4: se puede seguir ensayando con una oficial vigente
        self._aprobar()
        resp = self._crear_version('Segundo ensayo con la oficial vigente')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual((resp.data['numero'], resp.data['es_oficial']), (2, False))
        self.assertEqual(self.formula.estado, 'aprobada')
        self.assertEqual(self.formula.versiones.get(es_oficial=True).numero, 1)

    # --- marcar_oficial (reglas 3-5) ---
    def test_marcar_oficial_dado_version_existente_cuando_marca_entonces_200_y_formula_aprobada(self):
        v1 = self._crear_version()
        resp = self._marcar_oficial(v1.data['numero'])
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data['es_oficial'])
        self.assertEqual(self.formula.estado, 'aprobada')

    def test_marcar_oficial_dado_operario_cuando_marca_entonces_403(self):
        v1 = self._crear_version()
        self.client.force_authenticate(user=self.operario)
        self.assertEqual(self._marcar_oficial(v1.data['numero']).status_code, status.HTTP_403_FORBIDDEN)

    def test_marcar_oficial_dado_numero_inexistente_cuando_marca_entonces_404(self):
        self.assertEqual(self._marcar_oficial(99).status_code, status.HTTP_404_NOT_FOUND)

    def test_marcar_oficial_dado_dos_versiones_cuando_marca_la_segunda_entonces_desmarca_la_primera(self):
        v1 = self._crear_version('Primer ensayo')
        self._marcar_oficial(v1.data['numero'])
        v2 = self._crear_version('Segundo ensayo, mejor resultado')
        self._marcar_oficial(v2.data['numero'])
        resp = self.client.get(self._url('version-detalle', v1.data['numero']))
        self.assertFalse(resp.data['es_oficial'])

    # --- Regla 1 (D7): editar la receta viva no crea versión, sin importar el estado ---
    def test_formula_dado_en_pruebas_cuando_edita_entonces_200_sin_versionar(self):
        resp = self.client.put(self._url('detail'), self._payload(temperatura=95), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertFalse(self.formula.versiones.exists())

    def test_formula_dado_put_sin_sede_cuando_edita_entonces_conserva_su_sede(self):
        # Regresión: el PUT del tintorero no envía `sede`; antes la dejaba en NULL y la
        # fórmula desaparecía del filtro multi-tenant de su propia sede.
        resp = self.client.put(self._url('detail'), self._payload(temperatura=95), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.formula.refresh_from_db()
        self.assertEqual(self.formula.sede, self.sede)

    def test_formula_dado_aprobada_cuando_edita_entonces_200_sin_version_nueva_y_oficial_intacta(self):
        # D7: editar la receta viva ya no exige motivo ni versiona automáticamente,
        # ni siquiera con una versión oficial vigente. La oficial (JSON aparte) no se toca.
        self._aprobar()
        resp = self.client.put(self._url('detail'), self._payload(temperatura=95), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self.formula.versiones.count(), 1)
        oficial = self.formula.versiones.get(es_oficial=True)
        self.assertEqual(oficial.snapshot['fases'][0]['temperatura'], 90)

    def test_formula_dado_operario_cuando_edita_entonces_403(self):
        self.client.force_authenticate(user=self.operario)
        resp = self.client.put(self._url('detail'), self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Cierre de atajos: solo se marca oficial por la acción dedicada ---
    def test_formula_dado_en_pruebas_cuando_put_con_estado_aprobada_entonces_400(self):
        # Con justificación de auditoría: el único motivo de rechazo es la regla de estado
        payload = self._payload(estado='aprobada', _justificacion_auditoria='Intento de aprobar por PUT')
        resp = self.client.put(self._url('detail'), payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', resp.data['error']['fields'])
        self.formula.refresh_from_db()
        self.assertEqual(self.formula.estado, 'en_pruebas')

    def test_formula_dado_payload_aprobada_cuando_crea_entonces_400(self):
        payload = self._payload(estado='aprobada', codigo='NUEVA-1', nombre_color='Nuevo color')
        resp = self.client.post(reverse('formulacolor-list'), payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_formula_dado_version_en_payload_cuando_edita_entonces_se_ignora(self):
        resp = self.client.put(self._url('detail'), self._payload(version=99), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.formula.refresh_from_db()
        self.assertEqual(self.formula.version, 1)

    # --- Historial, detalle, diff e inmutabilidad ---
    def test_versiones_dado_dos_versiones_cuando_lista_entonces_orden_descendente_sin_snapshot(self):
        self._aprobar()
        self._crear_version('Subir temperatura de tintura')
        resp = self.client.get(self._url('versiones'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([v['numero'] for v in resp.data], [2, 1])
        self.assertNotIn('snapshot', resp.data[0])
        self.assertEqual(resp.data[0]['creada_por_nombre'], self.tintorero.username)

    def test_version_dado_numero_existente_cuando_consulta_entonces_snapshot(self):
        self._aprobar()
        resp = self.client.get(self._url('version-detalle', 1))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['snapshot']['fases'][0]['temperatura'], 90)

    def test_version_dado_numero_inexistente_cuando_consulta_entonces_404(self):
        self.assertEqual(self.client.get(self._url('version-detalle', 7)).status_code, status.HTTP_404_NOT_FOUND)

    def test_version_dado_existente_cuando_put_o_delete_entonces_405(self):
        # CB-D: la API no expone update ni delete de versiones
        self._aprobar()
        url = self._url('version-detalle', 1)
        self.assertEqual(self.client.put(url, {}, format='json').status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.formula.versiones.count(), 1)

    def test_diff_dado_dos_versiones_cuando_compara_entonces_reporta_campo_cambiado(self):
        self._aprobar()
        self.fase.temperatura = 95
        self.fase.save()
        self._crear_version('Subir temperatura')
        resp = self.client.get(self._url('version-diff', 1, 2))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        modificada = resp.data['cambios']['fases']['modificadas'][0]
        self.assertEqual(modificada['cambios']['temperatura'], {'a': 90, 'b': 95})
        self.assertEqual(resp.data['cambios']['fases']['agregadas'], [])

    def test_diff_dado_version_inexistente_cuando_compara_entonces_404(self):
        self._aprobar()
        self.assertEqual(self.client.get(self._url('version-diff', 1, 9)).status_code, status.HTTP_404_NOT_FOUND)

    # --- duplicar = crear variante (sin lineage) ---
    def test_duplicar_dado_codigo_y_nombre_cuando_duplica_entonces_variante_en_pruebas_v1(self):
        self._aprobar()
        resp = self.client.post(self._url('duplicar'), {'codigo': 'VAR-01', 'nombre_color': 'Azul variante'},
                                format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        variante = FormulaColor.objects.get(pk=resp.data['id'])
        self.assertEqual((variante.codigo, variante.estado, variante.version, variante.sede),
                         ('VAR-01', 'en_pruebas', 1, self.sede))
        self.assertEqual(variante.fases.count(), 1)
        self.assertFalse(variante.versiones.exists())

    def test_duplicar_dado_sin_codigo_cuando_duplica_entonces_400(self):
        resp = self.client.post(self._url('duplicar'), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicar_dado_codigo_existente_en_sede_cuando_duplica_entonces_400(self):
        resp = self.client.post(self._url('duplicar'),
                                {'codigo': self.formula.codigo, 'nombre_color': 'Otro nombre'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # --- derivar / derivadas (D8-D9) ---
    def test_derivar_dado_version_existente_cuando_deriva_entonces_201_con_lineage(self):
        v1 = self._crear_version('Ensayo base')
        resp = self.client.post(self._url('derivar'), {
            'codigo': 'DERIV-API-1', 'nombre_color': 'Derivada API', 'version_origen': v1.data['numero'],
            'motivo_derivacion': 'Cambio de sustrato',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data['formula_origen'], self.formula.id)
        self.assertEqual(resp.data['version_origen_numero'], 1)

    def test_derivar_dado_version_inexistente_cuando_deriva_entonces_404(self):
        resp = self.client.post(self._url('derivar'), {
            'codigo': 'DERIV-API-2', 'nombre_color': 'Derivada API 2', 'version_origen': 99,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_derivadas_dado_una_derivada_cuando_lista_entonces_la_incluye(self):
        v1 = self._crear_version('Ensayo base')
        self.client.post(self._url('derivar'), {
            'codigo': 'DERIV-API-3', 'nombre_color': 'Derivada API 3', 'version_origen': v1.data['numero'],
        }, format='json')
        resp = self.client.get(self._url('derivadas'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([f['codigo'] for f in resp.data], ['DERIV-API-3'])

    # --- Listado: es_laboratorio se filtra por defecto (D8) ---
    def test_listado_dado_formula_de_laboratorio_cuando_lista_sin_filtro_entonces_no_aparece(self):
        laboratorio = FormulaColorFactory(sede=self.sede, es_laboratorio=True)
        resp = self.client.get(reverse('formulacolor-list'))
        ids = [f['id'] for f in resp.data.get('results', resp.data)]
        self.assertIn(self.formula.id, ids)
        self.assertNotIn(laboratorio.id, ids)

    def test_listado_dado_incluir_laboratorio_cuando_lista_entonces_la_incluye(self):
        laboratorio = FormulaColorFactory(sede=self.sede, es_laboratorio=True)
        resp_sin = self.client.get(reverse('formulacolor-list'))
        ids_sin = [f['id'] for f in (resp_sin.data.get('results', resp_sin.data))]
        self.assertNotIn(laboratorio.id, ids_sin)
        resp_con = self.client.get(reverse('formulacolor-list'), {'incluir_laboratorio': 'true'})
        ids_con = [f['id'] for f in (resp_con.data.get('results', resp_con.data))]
        self.assertIn(laboratorio.id, ids_con)


class CongeladoVersionOrdenTestCase(TestCase):
    """Reglas 8-9 (§6): al lanzar una OP se congela la versión oficial de su fórmula y ya no cambia.
    STT: pendiente -> en_proceso / finalizada; CB-D: guardas del lanzamiento y de la inmutabilidad."""
    MOTIVO = 'Aprobada tras prueba de laboratorio'

    def setUp(self):
        self.sede = SedeFactory()
        self.usuario = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.formula = FormulaColorFactory(sede=self.sede, estado='en_pruebas')
        self.fase = FaseRecetaFactory(formula=self.formula, nombre='tintura', orden=1, temperatura=90)

    def _orden(self, formula=None, **extra):
        return OrdenProduccionFactory(sede=self.sede, formula_color=formula or self.formula, **extra)

    def _aprobar(self):
        return VersionadoFormulaService.asegurar_version_oficial(self.formula, self.MOTIVO, self.usuario)

    def _lanzar(self, orden, estado='en_proceso', **kwargs):
        orden.estado = estado
        orden.save(**kwargs)
        orden.refresh_from_db()
        return orden

    def test_orden_dado_formula_con_version_oficial_cuando_lanza_entonces_congela_esa_version(self):
        v1 = self._aprobar()
        orden = self._lanzar(self._orden())
        self.assertEqual((orden.estado, orden.version_formula), ('en_proceso', v1))

    def test_orden_dado_formula_sin_version_oficial_cuando_lanza_entonces_error_y_sigue_pendiente(self):
        orden = self._orden()
        orden.estado = 'en_proceso'
        with self.assertRaises(ValidationError):
            orden.save()
        orden.refresh_from_db()
        self.assertEqual((orden.estado, orden.version_formula), ('pendiente', None))

    def test_orden_dado_formula_con_solo_ensayos_sin_oficial_cuando_lanza_entonces_error(self):
        # EP: tener ensayos no basta; se exige una versión marcada oficial (regla 8)
        VersionadoFormulaService.crear_version(self.formula, 'Ensayo sin marcar oficial', self.usuario)
        orden = self._orden()
        orden.estado = 'en_proceso'
        with self.assertRaises(ValidationError):
            orden.save()

    def test_orden_dado_update_fields_solo_estado_cuando_lanza_entonces_persiste_la_version(self):
        # Camino de registro_lote / ejecucion_produccion: save(update_fields=['estado'])
        v1 = self._aprobar()
        orden = self._lanzar(self._orden(), update_fields=['estado'])
        self.assertEqual(orden.version_formula, v1)

    def test_orden_dado_pendiente_cuando_pasa_directo_a_finalizada_entonces_congela(self):
        v1 = self._aprobar()
        orden = self._lanzar(self._orden(), estado='finalizada')
        self.assertEqual(orden.version_formula, v1)

    def test_orden_dado_creada_ya_en_proceso_cuando_guarda_entonces_congela(self):
        v1 = self._aprobar()
        orden = self._orden(estado='en_proceso')
        self.assertEqual(orden.version_formula, v1)

    def test_orden_dado_sin_formula_cuando_lanza_entonces_no_exige_version(self):
        orden = self._lanzar(OrdenProduccionFactory(sede=self.sede))
        self.assertEqual((orden.estado, orden.version_formula), ('en_proceso', None))

    def test_orden_dado_pendiente_cuando_guarda_sin_lanzar_entonces_no_congela(self):
        self._aprobar()
        orden = self._orden()
        orden.observaciones = 'Solo cambia una observación'
        orden.save()
        orden.refresh_from_db()
        self.assertIsNone(orden.version_formula)

    def test_orden_dado_pendiente_cuando_cambia_de_formula_entonces_se_permite(self):
        # D6: una orden en pendiente aún puede cambiar de receta
        orden = self._orden()
        otra = FormulaColorFactory(sede=self.sede)
        orden.formula_color = otra
        orden.save()
        orden.refresh_from_db()
        self.assertEqual(orden.formula_color, otra)

    def test_orden_dado_lanzada_cuando_se_marca_otra_version_oficial_entonces_conserva_la_suya(self):
        v1 = self._aprobar()
        orden = self._lanzar(self._orden())
        self.fase.temperatura = 95
        self.fase.save()
        v2 = VersionadoFormulaService.crear_version(self.formula, 'Ajuste de temperatura de tintura', self.usuario)
        VersionadoFormulaService.marcar_oficial(self.formula, v2.numero, self.usuario)
        orden = self._lanzar(orden, estado='finalizada')
        self.assertEqual(orden.version_formula, v1)
        self.assertEqual(orden.version_formula.snapshot['fases'][0]['temperatura'], 90)
        self.assertNotEqual(orden.version_formula, v2)

    def test_orden_dado_lanzada_cuando_cambia_de_formula_entonces_error(self):
        self._aprobar()
        orden = self._lanzar(self._orden())
        orden.formula_color = FormulaColorFactory(sede=self.sede)
        with self.assertRaises(ValidationError):
            orden.save()

    def test_orden_dado_lanzada_cuando_cambia_de_version_entonces_error(self):
        self._aprobar()
        orden = self._lanzar(self._orden())
        orden.version_formula = VersionadoFormulaService.crear_version(
            self.formula, 'Nueva versión de la receta', self.usuario)
        with self.assertRaises(ValidationError):
            orden.save()

    def test_orden_dado_legacy_en_proceso_sin_version_cuando_finaliza_entonces_se_permite(self):
        # Las OPs ya en proceso antes del versionado no se bloquean (no hay migración de datos)
        orden = self._orden()
        OrdenProduccion.objects.filter(pk=orden.pk).update(estado='en_proceso')
        orden = self._lanzar(OrdenProduccion.objects.get(pk=orden.pk), estado='finalizada')
        self.assertEqual((orden.estado, orden.version_formula), ('finalizada', None))

    def test_factory_dado_formula_aprobada_cuando_se_crea_entonces_tiene_version_oficial(self):
        formula = FormulaColorFactory(sede=self.sede, estado='aprobada')
        self.assertTrue(formula.versiones.filter(es_oficial=True, numero=1).exists())


class CongeladoVersionOrdenApiTestCase(TestCase):
    """Reglas 8-9 vía API: version_formula es de solo lectura y el rechazo del lanzamiento es 400."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.jefe = CustomUserFactory(sede=self.sede, groups=['jefe_planta'])
        self.client.force_authenticate(user=self.jefe)

    def _url(self, orden):
        return reverse('ordenproduccion-detail', args=[orden.id])

    def test_orden_dado_formula_sin_version_cuando_patch_a_en_proceso_entonces_400(self):
        formula = FormulaColorFactory(sede=self.sede, estado='en_pruebas')
        orden = OrdenProduccionFactory(sede=self.sede, formula_color=formula)
        resp = self.client.patch(self._url(orden), {'estado': 'en_proceso'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'pendiente')

    def test_orden_dado_formula_aprobada_cuando_patch_a_en_proceso_entonces_expone_version(self):
        formula = FormulaColorFactory(sede=self.sede, estado='aprobada')
        orden = OrdenProduccionFactory(sede=self.sede, formula_color=formula)
        resp = self.client.patch(self._url(orden), {'estado': 'en_proceso'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['version_formula'], formula.versiones.get(es_oficial=True).id)

    def test_orden_dado_version_en_payload_cuando_patch_entonces_se_ignora(self):
        formula = FormulaColorFactory(sede=self.sede, estado='aprobada')
        orden = OrdenProduccionFactory(sede=self.sede, formula_color=formula)
        resp = self.client.patch(self._url(orden), {'version_formula': formula.versiones.get().id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        orden.refresh_from_db()
        self.assertIsNone(orden.version_formula)
