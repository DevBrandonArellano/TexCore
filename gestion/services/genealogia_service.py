import logging
from collections import deque
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from gestion.models import GenealogiaLote, LoteProduccion, MateriaPrimaLote
from inventory.models import DetalleHistorialDespacho, MovimientoInventario

logger = logging.getLogger(__name__)


def _serializar_lote(lote: LoteProduccion) -> dict:
    """Serializa la entidad LoteProduccion a un formato diccionario liviano para grafos."""
    return {
        'id': lote.id,
        'codigo_lote': lote.codigo_lote,
        'producto_id': lote.producto_id,
        'producto_codigo': lote.producto.codigo if lote.producto else 'N/A',
        'producto_descripcion': lote.producto.descripcion if lote.producto else 'N/A',
        'producto_tipo': lote.producto.tipo if lote.producto else 'N/A',
        'peso_neto_producido': str(lote.peso_neto_producido),
        'clasificacion_calidad': lote.clasificacion_calidad,
        'orden_produccion_id': lote.orden_produccion_id,
        'orden_produccion_codigo': lote.orden_produccion.codigo if lote.orden_produccion else None,
    }


class GenealogiaService:
    """
    Servicio de Trazabilidad Total basado en Grafos Acíclicos Dirigidos (DAG).
    Permite:
    1. Trace-Back (Trazabilidad Hacia Atrás): Desde un producto terminado o lote
       en reclamo, rastrea hacia atrás todas las mezclas, etapas previas y proveedores
       de materias primas originales.
    2. Trace-Forward Recall (Trazabilidad Hacia Adelante): Desde un lote defectuoso
       de materia prima o lote intermedio, proyecta el árbol de impacto de todos los
       lotes derivados y localiza los clientes a quienes se les despachó producto.
    """

    @classmethod
    def resolver_lote(cls, lote_ref) -> LoteProduccion:
        """Resuelve un objeto LoteProduccion a partir de instancia, ID o código de lote."""
        if isinstance(lote_ref, LoteProduccion):
            return lote_ref
        if isinstance(lote_ref, int):
            try:
                return LoteProduccion.objects.select_related('producto', 'orden_produccion').get(pk=lote_ref)
            except LoteProduccion.DoesNotExist:
                raise ValidationError(f"No existe un lote de producción con ID {lote_ref}.")
        if isinstance(lote_ref, str):
            try:
                return LoteProduccion.objects.select_related('producto', 'orden_produccion').get(codigo_lote=lote_ref)
            except LoteProduccion.DoesNotExist:
                raise ValidationError(f"No existe un lote de producción con código '{lote_ref}'.")
        raise ValidationError(f"Referencia de lote no válida: {type(lote_ref)}")

    @classmethod
    def obtener_trazabilidad_hacia_atras(cls, lote_ref, profundidad_maxima: int = 10) -> dict:
        """
        Recorre el DAG hacia atrás (Trace-Back) desde el lote indicado.
        Retorna la raíz, los ancestros, las aristas del grafo y los proveedores
        de materias primas que originaron la cadena.
        """
        lote_raiz = cls.resolver_lote(lote_ref)
        visited = {lote_raiz.id}
        queue = deque([(lote_raiz, 0)])

        ancestros = []
        aristas = []
        materias_primas_origen = []
        mps_vistas = set()

        while queue:
            curr_lote, profundidad = queue.popleft()

            # 1. Comprobar si el lote actual tiene enlace directo con MateriaPrimaLote
            if curr_lote.materia_prima_lote_id and curr_lote.materia_prima_lote_id not in mps_vistas:
                mp = curr_lote.materia_prima_lote
                mps_vistas.add(mp.id)
                materias_primas_origen.append({
                    'id': mp.id,
                    'lote_proveedor': mp.lote_proveedor,
                    'proveedor_id': mp.proveedor_id,
                    'proveedor_nombre': mp.proveedor.nombre if mp.proveedor else 'N/A',
                    'producto_codigo': mp.producto.codigo if mp.producto else 'N/A',
                    'fecha_recepcion': str(mp.fecha_recepcion),
                    'numero_documento_entrada': mp.numero_documento_entrada,
                    'asociado_a_lote_codigo': curr_lote.codigo_lote,
                })

            # 2. Comprobar consumos de materia prima mediante tabla through histórica si existe
            for consumo_mp in getattr(curr_lote, 'consumos_materias_primas', []).all() if hasattr(curr_lote, 'consumos_materias_primas') else []:
                mp = consumo_mp.materia_prima
                if mp.id not in mps_vistas:
                    mps_vistas.add(mp.id)
                    materias_primas_origen.append({
                        'id': mp.id,
                        'lote_proveedor': mp.lote_proveedor,
                        'proveedor_id': mp.proveedor_id,
                        'proveedor_nombre': mp.proveedor.nombre if mp.proveedor else 'N/A',
                        'producto_codigo': mp.producto.codigo if mp.producto else 'N/A',
                        'fecha_recepcion': str(mp.fecha_recepcion),
                        'numero_documento_entrada': mp.numero_documento_entrada,
                        'asociado_a_lote_codigo': curr_lote.codigo_lote,
                    })

            if profundidad >= profundidad_maxima:
                continue

            # 3. Buscar aristas donde curr_lote es el lote_hijo (padres inmediatos)
            padres_aristas = GenealogiaLote.objects.filter(
                lote_hijo=curr_lote
            ).select_related(
                'lote_padre',
                'lote_padre__producto',
                'operacion',
                'operacion__corrida',
                'operacion__maquina',
                'operacion__operario',
            )

            for arista in padres_aristas:
                padre = arista.lote_padre
                op = arista.operacion
                aristas.append({
                    'padre_id': padre.id,
                    'padre_codigo': padre.codigo_lote,
                    'hijo_id': curr_lote.id,
                    'hijo_codigo': curr_lote.codigo_lote,
                    'cantidad_usada': str(arista.cantidad_padre_usada),
                    'operacion_id': op.id if op else None,
                    'numero_secuencia': op.numero_secuencia if op else None,
                    'corrida_codigo': op.corrida.codigo if op and op.corrida else None,
                    'maquina': op.maquina.nombre if op and op.maquina else None,
                    'operario': (op.operario.get_full_name() or op.operario.username) if op and op.operario else None,
                    'fecha': arista.created_at.isoformat() if arista.created_at else None,
                })

                if padre.id not in visited:
                    visited.add(padre.id)
                    ancestros.append(_serializar_lote(padre))
                    queue.append((padre, profundidad + 1))

        return {
            'nodo_raiz': _serializar_lote(lote_raiz),
            'ancestros': ancestros,
            'aristas': aristas,
            'materias_primas_origen': materias_primas_origen,
            'total_ancestros': len(ancestros),
            'total_materias_primas': len(materias_primas_origen),
        }

    @classmethod
    def obtener_trazabilidad_hacia_adelante(cls, lote_ref, profundidad_maxima: int = 10) -> dict:
        """
        Recorre el DAG hacia adelante (Trace-Forward Recall) desde el lote indicado.
        Si se pasa un MateriaPrimaLote, inicia desde los lotes derivados.
        Retorna la raíz, los descendientes generados, las aristas y todos los
        despachos a clientes finales potencialmente afectados.
        """
        lotes_inicio = []
        info_mp_raiz = None

        if isinstance(lote_ref, MateriaPrimaLote):
            info_mp_raiz = {
                'id': lote_ref.id,
                'lote_proveedor': lote_ref.lote_proveedor,
                'proveedor': lote_ref.proveedor.nombre if lote_ref.proveedor else 'N/A',
            }
            derivados = list(LoteProduccion.objects.filter(
                Q(materia_prima_lote=lote_ref) | Q(consumos_materias_primas__materia_prima=lote_ref)
            ).distinct())
            lotes_inicio.extend(derivados)
        else:
            lote_obj = cls.resolver_lote(lote_ref)
            lotes_inicio.append(lote_obj)

        if not lotes_inicio:
            return {
                'nodo_raiz': info_mp_raiz or {'error': 'Sin lotes de inicio'},
                'descendientes': [],
                'aristas': [],
                'despachos_clientes': [],
                'total_descendientes': 0,
                'total_clientes_afectados': 0,
            }

        visited = set(l.id for l in lotes_inicio)
        queue = deque([(l, 0) for l in lotes_inicio])

        descendientes = []
        aristas = []
        despachos_clientes = []
        despachos_vistos = set()

        while queue:
            curr_lote, profundidad = queue.popleft()

            # 1. Buscar si este lote fue despachado a clientes
            detalles_despacho = DetalleHistorialDespacho.objects.filter(
                lote=curr_lote
            ).select_related('historial')

            for d in detalles_despacho:
                historial = d.historial
                for pedido in historial.pedidos.select_related('cliente').all():
                    clave_despacho = (historial.id, pedido.id, curr_lote.id)
                    if clave_despacho not in despachos_vistos:
                        despachos_vistos.add(clave_despacho)
                        despachos_clientes.append({
                            'lote_id': curr_lote.id,
                            'lote_codigo': curr_lote.codigo_lote,
                            'despacho_id': historial.id,
                            'fecha_despacho': historial.fecha_despacho.isoformat() if historial.fecha_despacho else None,
                            'pedido_id': pedido.id,
                            'pedido_codigo': getattr(pedido, 'codigo', str(pedido.id)),
                            'cliente_id': pedido.cliente_id,
                            'cliente_nombre': pedido.cliente.nombre_razon_social if pedido.cliente else 'N/A',
                            'cliente_ruc': pedido.cliente.ruc_cedula if pedido.cliente else 'N/A',
                            'peso_despachado': str(d.peso),
                        })

            # También consultar salidas Kardex por VENTA
            movs_venta = MovimientoInventario.objects.filter(
                lote=curr_lote,
                tipo_movimiento='VENTA',
            )
            for mv in movs_venta:
                clave_mv = (mv.id, curr_lote.id)
                if clave_mv not in despachos_vistos:
                    despachos_vistos.add(clave_mv)
                    despachos_clientes.append({
                        'lote_id': curr_lote.id,
                        'lote_codigo': curr_lote.codigo_lote,
                        'movimiento_kardex_id': mv.id,
                        'fecha_despacho': mv.fecha.isoformat() if mv.fecha else None,
                        'documento_ref': mv.documento_ref,
                        'cantidad_vendida': str(mv.cantidad),
                    })

            if profundidad >= profundidad_maxima:
                continue

            # 2. Buscar aristas donde curr_lote es el lote_padre (hijos inmediatos)
            hijos_aristas = GenealogiaLote.objects.filter(
                lote_padre=curr_lote
            ).select_related(
                'lote_hijo',
                'lote_hijo__producto',
                'operacion',
                'operacion__corrida',
                'operacion__maquina',
            )

            for arista in hijos_aristas:
                hijo = arista.lote_hijo
                op = arista.operacion
                aristas.append({
                    'padre_id': curr_lote.id,
                    'padre_codigo': curr_lote.codigo_lote,
                    'hijo_id': hijo.id,
                    'hijo_codigo': hijo.codigo_lote,
                    'cantidad_usada': str(arista.cantidad_padre_usada),
                    'operacion_id': op.id if op else None,
                    'corrida_codigo': op.corrida.codigo if op and op.corrida else None,
                    'maquina': op.maquina.nombre if op and op.maquina else None,
                    'fecha': arista.created_at.isoformat() if arista.created_at else None,
                })

                if hijo.id not in visited:
                    visited.add(hijo.id)
                    descendientes.append(_serializar_lote(hijo))
                    queue.append((hijo, profundidad + 1))

        nodo_raiz_repr = info_mp_raiz or _serializar_lote(lotes_inicio[0])
        clientes_unicos = set(d['cliente_id'] for d in despachos_clientes if 'cliente_id' in d)

        return {
            'nodo_raiz': nodo_raiz_repr,
            'descendientes': descendientes,
            'aristas': aristas,
            'despachos_clientes': despachos_clientes,
            'total_descendientes': len(descendientes),
            'total_clientes_afectados': len(clientes_unicos),
        }
