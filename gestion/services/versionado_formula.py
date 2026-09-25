"""
Versionado inmutable de fórmulas de color y derivación entre fórmulas
(docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md
§5.5, §5.7, §6 reglas 1-7, decisiones D7-D9).

- Guardar la receta (PUT/PATCH de FormulaColor) edita la receta viva; no crea
  versión por sí solo (D7: eso ya no está acoplado al estado de la fórmula).
- `crear_version` congela el estado actual de la receta viva como una versión
  nueva, no oficial: es un ensayo. Una fórmula en desarrollo acumula ensayos
  sin ninguna versión oficial — es su estado normal.
- `marcar_oficial` designa una versión ya existente (oficial o no) como la
  oficial vigente, desmarcando la anterior. Solo entonces puede lanzarse una
  orden con esa fórmula.
- `derivar` crea una FormulaColor nueva a partir del snapshot de una versión
  concreta de otra fórmula (oficial o ensayo, D9): la derivada arranca su
  propio ciclo de versionado.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from gestion.models import DetalleFormula, FaseReceta, FormulaColor, ProcesoTintoreria, VersionFormula


def _decimal_o_none(valor):
    return str(valor) if valor is not None else None


def _campos_cambiados(a, b, excluir=()):
    return {
        campo: {'a': a.get(campo), 'b': b.get(campo)}
        for campo in sorted((a.keys() | b.keys()) - set(excluir))
        if a.get(campo) != b.get(campo)
    }


def _diff_detalles(detalles_a, detalles_b):
    por_producto_a = {d['producto_id']: d for d in detalles_a}
    por_producto_b = {d['producto_id']: d for d in detalles_b}
    comunes = por_producto_a.keys() & por_producto_b.keys()
    modificados = []
    for producto_id in comunes:
        cambios = _campos_cambiados(por_producto_a[producto_id], por_producto_b[producto_id])
        if cambios:
            modificados.append({
                'producto_id': producto_id,
                'producto_codigo': por_producto_b[producto_id].get('producto_codigo'),
                'cambios': cambios,
            })
    return {
        'agregados': [d for p, d in por_producto_b.items() if p not in por_producto_a],
        'eliminados': [d for p, d in por_producto_a.items() if p not in por_producto_b],
        'modificados': sorted(modificados, key=lambda m: m['producto_id']),
    }


class VersionadoFormulaService:

    @staticmethod
    def construir_snapshot(formula) -> dict:
        """Receta completa de la fórmula según el esquema del spec (§5.5). Guarda código y
        descripción del producto además del id, para que la versión siga legible aunque
        el químico se renombre o se dé de baja."""
        fases = (
            formula.fases.select_related('proceso')
            .prefetch_related('detalles__producto')
            .order_by('orden')
        )
        return {
            'formula': {
                'codigo': formula.codigo,
                'nombre_color': formula.nombre_color,
                'tipo_sustrato': formula.tipo_sustrato,
                'observaciones': formula.observaciones,
            },
            'fases': [
                {
                    'orden': fase.orden,
                    'proceso_codigo': fase.proceso.codigo,
                    'proceso_nombre': fase.proceso.nombre,
                    'proceso_tipo': fase.proceso.tipo,
                    'ciclo': fase.ciclo,
                    'temperatura': fase.temperatura,
                    'tiempo': fase.tiempo,
                    'detalles': [
                        {
                            'producto_id': detalle.producto_id,
                            'producto_codigo': detalle.producto.codigo if detalle.producto else None,
                            'producto_descripcion': detalle.producto.descripcion if detalle.producto else None,
                            'tipo_calculo': detalle.tipo_calculo,
                            'concentracion_gr_l': _decimal_o_none(detalle.concentracion_gr_l),
                            'porcentaje': _decimal_o_none(detalle.porcentaje),
                            'orden_adicion': detalle.orden_adicion,
                        }
                        for detalle in fase.detalles.all()
                    ],
                }
                for fase in fases
            ],
        }

    @staticmethod
    @transaction.atomic
    def crear_version(formula, observaciones, usuario) -> VersionFormula:
        """Regla 1: guardar una fórmula (congelar su receta viva) crea siempre una versión
        nueva, nunca oficial por sí sola (D7). Una fórmula en desarrollo acumula así
        varios ensayos sin ninguna marcada oficial; para lanzar una orden con ella hay
        que llamar después a `marcar_oficial` sobre la versión elegida."""
        formula = FormulaColor.objects.select_for_update().get(pk=formula.pk)
        numero = (formula.versiones.aggregate(m=Max('numero'))['m'] or 0) + 1
        # `motivo` se conserva por compatibilidad con el historial/auditoría existente
        # (VersionFormula.motivo es obligatorio desde antes de D7); `observaciones` es
        # el campo nuevo que ve la UI para distinguir un ensayo de otro.
        version = VersionFormula.objects.create(
            formula=formula,
            numero=numero,
            snapshot=VersionadoFormulaService.construir_snapshot(formula),
            motivo=observaciones,
            observaciones=observaciones,
            creada_por=usuario,
            es_oficial=False,
        )
        return version

    @staticmethod
    @transaction.atomic
    def marcar_oficial(formula, numero, usuario) -> VersionFormula:
        """Regla 3-4: designa una versión existente (ensayo u oficial anterior) como la
        oficial vigente. Se puede seguir ensayando después: las versiones nuevas nacen
        no oficiales y esta no cambia hasta que se marque otra explícitamente. También
        cubre la regla 5 (volver a una versión anterior marcándola oficial de nuevo)."""
        formula = FormulaColor.objects.select_for_update().get(pk=formula.pk)
        version = formula.versiones.select_for_update().get(numero=numero)
        anterior = formula.versiones.filter(es_oficial=True).exclude(pk=version.pk).first()
        if anterior:
            # Primero se desmarca: la restricción de BD admite una sola oficial por fórmula
            anterior.es_oficial = False
            anterior.save()
        version.es_oficial = True
        version.save()
        formula.estado = 'aprobada'
        formula.version = version.numero
        formula._justificacion_auditoria = f'Versión {version.numero} marcada oficial.'
        formula.save()
        return version

    @staticmethod
    @transaction.atomic
    def asegurar_version_oficial(formula, motivo, usuario) -> VersionFormula:
        """Idempotente: devuelve la versión oficial de la fórmula y, si no tiene, crea
        una versión con la receta viva y la marca oficial. Para seeders y datos de
        demostración: no forma parte del flujo normal de la UI (crear_version +
        marcar_oficial son dos pasos deliberados y separados)."""
        formula = FormulaColor.objects.select_for_update().get(pk=formula.pk)
        oficial = formula.versiones.filter(es_oficial=True).first()
        if oficial:
            return oficial
        version = VersionadoFormulaService.crear_version(formula, motivo, usuario)
        return VersionadoFormulaService.marcar_oficial(formula, version.numero, usuario)

    @staticmethod
    @transaction.atomic
    def derivar(formula_origen, version_origen, datos, usuario) -> FormulaColor:
        """Reglas 6-7 (D8-D9): crea una FormulaColor nueva a partir del snapshot de una
        versión concreta de otra fórmula (oficial o ensayo, a elección del tintorero).
        La derivada arranca sin versiones propias; el primer `crear_version` que se le
        haga será su v1."""
        nueva = FormulaColor.objects.create(
            codigo=datos['codigo'],
            nombre_color=datos['nombre_color'],
            tipo_sustrato=datos.get('tipo_sustrato') or formula_origen.tipo_sustrato,
            estado='en_pruebas',
            sede=formula_origen.sede,
            creado_por=usuario,
            formula_origen=formula_origen,
            version_origen=version_origen,
            motivo_derivacion=datos.get('motivo_derivacion', ''),
            es_laboratorio=datos.get('es_laboratorio', False),
        )
        VersionadoFormulaService._reconstruir_fases_desde_snapshot(nueva, version_origen.snapshot)
        return nueva

    @staticmethod
    def _reconstruir_fases_desde_snapshot(formula_destino, snapshot):
        """Reconstruye FaseReceta/DetalleFormula a partir de un snapshot JSON (el inverso
        de `construir_snapshot`). Usado por `derivar`: la receta de origen puede ser un
        ensayo antiguo cuyas fases ya no coinciden con las de la fórmula origen en vivo,
        así que se reconstruye desde el snapshot, no desde el ORM del origen."""
        for fase_data in snapshot.get('fases', []):
            try:
                proceso = ProcesoTintoreria.objects.get(
                    codigo=fase_data['proceso_codigo'], sede=formula_destino.sede)
            except ProcesoTintoreria.DoesNotExist:
                raise ValidationError(
                    f"El proceso \"{fase_data['proceso_codigo']}\" del snapshot de origen "
                    "no existe en el catálogo de esta sede.")
            fase = FaseReceta.objects.create(
                formula=formula_destino,
                proceso=proceso,
                ciclo=fase_data.get('ciclo'),
                orden=fase_data['orden'],
                temperatura=fase_data.get('temperatura'),
                tiempo=fase_data.get('tiempo'),
            )
            for detalle_data in fase_data.get('detalles', []):
                DetalleFormula.objects.create(
                    fase=fase,
                    producto_id=detalle_data.get('producto_id'),
                    tipo_calculo=detalle_data['tipo_calculo'],
                    concentracion_gr_l=detalle_data.get('concentracion_gr_l'),
                    porcentaje=detalle_data.get('porcentaje'),
                    orden_adicion=detalle_data.get('orden_adicion', 1),
                )

    @staticmethod
    def diff(snapshot_a, snapshot_b) -> dict:
        """Diferencias de A hacia B. Las fases se emparejan por `orden` y los insumos de
        cada fase por `producto_id` (único por fase). Solo se listan los campos cambiados."""
        fases_a = {f['orden']: f for f in snapshot_a.get('fases', [])}
        fases_b = {f['orden']: f for f in snapshot_b.get('fases', [])}
        modificadas = []
        for orden in sorted(fases_a.keys() & fases_b.keys()):
            fa, fb = fases_a[orden], fases_b[orden]
            cambios = _campos_cambiados(fa, fb, excluir=('detalles',))
            detalles = _diff_detalles(fa.get('detalles', []), fb.get('detalles', []))
            if cambios or any(detalles.values()):
                modificadas.append({
                    'orden': orden, 'proceso_codigo': fb.get('proceso_codigo'),
                    'cambios': cambios, 'detalles': detalles,
                })
        return {
            'formula': _campos_cambiados(snapshot_a.get('formula', {}), snapshot_b.get('formula', {})),
            'fases': {
                'agregadas': [fases_b[o] for o in sorted(fases_b.keys() - fases_a.keys())],
                'eliminadas': [fases_a[o] for o in sorted(fases_a.keys() - fases_b.keys())],
                'modificadas': modificadas,
            },
        }

