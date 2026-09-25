"""
Versionado inmutable de fórmulas de color
(docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md §5.5, §6 reglas 1-3).

- Una fórmula en `en_pruebas` se edita en sitio, sin versionar.
- Aprobarla crea la versión oficial N (snapshot JSON de la receta completa).
- Editar una fórmula ya aprobada exige motivo y crea la versión N+1 oficial; la
  anterior queda intacta y deja de ser oficial.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from gestion.models import FormulaColor, VersionFormula


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
    def aprobar(formula, motivo, usuario) -> VersionFormula:
        """Regla 2: aprobar una fórmula en pruebas crea su versión oficial."""
        formula = FormulaColor.objects.select_for_update().get(pk=formula.pk)
        if formula.estado == 'aprobada':
            raise ValidationError(
                'La fórmula ya está aprobada. Para cambiarla, edítela indicando el motivo: '
                'se creará una versión nueva.')
        return VersionadoFormulaService._crear_version_oficial(formula, motivo, usuario)

    @staticmethod
    @transaction.atomic
    def versionar(formula, motivo, usuario) -> VersionFormula:
        """Regla 3: congela el estado actual de una fórmula aprobada como versión N+1 oficial."""
        formula = FormulaColor.objects.select_for_update().get(pk=formula.pk)
        if formula.estado != 'aprobada':
            raise ValidationError('Solo se versiona una fórmula aprobada; una en pruebas se edita en sitio.')
        return VersionadoFormulaService._crear_version_oficial(formula, motivo, usuario)

    @staticmethod
    @transaction.atomic
    def asegurar_version_oficial(formula, motivo, usuario) -> VersionFormula:
        """Idempotente: devuelve la versión oficial de la fórmula y, si no tiene, la crea
        (aprueba la que está en pruebas o versiona la aprobada sin versiones, p. ej. las
        aprobadas antes del versionado). Para seeders y la migración de datos pendiente."""
        formula = FormulaColor.objects.select_for_update().get(pk=formula.pk)
        oficial = formula.versiones.filter(es_oficial=True).first()
        if oficial:
            return oficial
        return VersionadoFormulaService._crear_version_oficial(formula, motivo, usuario)

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

    @staticmethod
    def _crear_version_oficial(formula, motivo, usuario) -> VersionFormula:
        anterior = formula.versiones.filter(es_oficial=True).first()
        if anterior:
            # Primero se desmarca: la restricción de BD admite una sola oficial por fórmula
            anterior.es_oficial = False
            anterior.save()
        numero = (formula.versiones.aggregate(m=Max('numero'))['m'] or 0) + 1
        version = VersionFormula.objects.create(
            formula=formula,
            numero=numero,
            snapshot=VersionadoFormulaService.construir_snapshot(formula),
            motivo=motivo,
            creada_por=usuario,
            es_oficial=True,
        )
        formula.estado = 'aprobada'
        formula.version = numero
        formula._justificacion_auditoria = motivo
        formula.save()
        return version
