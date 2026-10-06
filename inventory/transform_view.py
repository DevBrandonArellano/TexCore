import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import Bodega, LoteProduccion, Producto
from gestion.permissions import filtrar_lotes_por_sede

from .models import MovimientoInventario, StockBodega
from .permissions import IsInventoryWriterOrAdmin, validar_traslado

logger = logging.getLogger('inventory.transform')

_CAMPOS_OBLIGATORIOS = (
    'bodega_origen_id', 'bodega_destino_id', 'producto_origen_id', 'producto_destino_id', 'cantidad',
)
_SIN_LOTE = (None, '', '0', 0)


class _StockInsuficiente(Exception):
    def __init__(self, disponible):
        super().__init__(disponible)
        self.disponible = disponible


def _leer_entrada(data):
    """Normaliza y valida la forma del pedido; los errores van como {"error": ...} (400)."""
    entrada = {campo: data.get(campo) for campo in _CAMPOS_OBLIGATORIOS}
    justificacion = data.get('_justificacion_auditoria')
    entrada['justificacion'] = justificacion.strip() if isinstance(justificacion, str) else justificacion

    # Tratar 0 / "0" / vacío como "sin lote" (el front puede enviar SelectItem value="0").
    lote_raw = data.get('lote_origen_id')
    entrada['lote_origen_id'] = None
    if lote_raw not in _SIN_LOTE:
        try:
            entrada['lote_origen_id'] = int(lote_raw) or None
        except (TypeError, ValueError):
            raise ValidationError({"error": "lote_origen_id inválido."}) from None

    codigo = data.get('nuevo_lote_codigo')
    entrada['nuevo_lote_codigo'] = (codigo.strip() or None) if isinstance(codigo, str) else codigo

    if not all(entrada[campo] for campo in _CAMPOS_OBLIGATORIOS):
        raise ValidationError({"error": "Faltan campos obligatorios."})
    if not entrada['justificacion']:
        raise ValidationError({"error": "Se requiere una justificación (_justificacion_auditoria)."})
    return entrada


def _validar_alcance(user, datos):
    """OWASP A01: origen operable, destino de la misma sede, productos globales o
    de esa sede, y lotes (origen y nuevo código existente) de la sede del usuario."""
    origen = Bodega.objects.filter(pk=datos['bodega_origen_id']).first()
    destino = Bodega.objects.filter(pk=datos['bodega_destino_id']).first()
    if origen is None:
        raise ValidationError({'bodega_origen_id': 'No encontrado.'})
    if destino is None:
        raise ValidationError({'bodega_destino_id': 'No encontrado.'})
    validar_traslado(user, origen, destino, 'bodega_destino_id')
    for campo in ('producto_origen_id', 'producto_destino_id'):
        producto = Producto.objects.filter(pk=datos[campo]).first()
        if producto is None or producto.sede_id not in (None, origen.sede_id):
            raise ValidationError({campo: 'No encontrado.'})
    lotes = filtrar_lotes_por_sede(LoteProduccion.objects.all(), user)
    if datos['lote_origen_id'] and not lotes.filter(pk=datos['lote_origen_id']).exists():
        raise ValidationError({'lote_origen_id': 'No encontrado.'})
    codigo = datos['nuevo_lote_codigo']
    if codigo and LoteProduccion.objects.filter(codigo_lote=codigo).exists() \
            and not lotes.filter(codigo_lote=codigo).exists():
        raise ValidationError({'nuevo_lote_codigo': 'El código de lote ya está en uso.'})


def _parse_cantidad(valor):
    # Antes un valor no numérico caía en el except genérico y respondía 500.
    try:
        cantidad = Decimal(str(valor))
    except InvalidOperation:
        raise ValidationError({"error": "La cantidad no es un número válido."}) from None
    if not cantidad.is_finite() or cantidad <= 0:
        raise ValidationError({"error": "La cantidad debe ser positiva."})
    return cantidad


def _stock_origen_bloqueado(entrada):
    """Fila de stock de origen, bloqueada. Si llega "sin lote", o el lote elegido no tiene
    fila con saldo, toma la de mayor saldo del producto en la bodega."""
    base = StockBodega.objects.select_for_update().filter(
        bodega_id=entrada['bodega_origen_id'], producto_id=entrada['producto_origen_id'])
    lote_id = entrada['lote_origen_id']
    candidatas = base.filter(lote_id=lote_id) if lote_id else base
    stock = candidatas.filter(cantidad__gt=0).order_by('-cantidad', 'id').first()
    if not stock and lote_id:
        stock = base.filter(cantidad__gt=0).order_by('-cantidad', 'id').first()
    if not stock:
        raise StockBodega.DoesNotExist
    return stock


def _registrar_movimiento(justificacion, **campos):
    movimiento = MovimientoInventario(**campos)
    movimiento._justificacion_auditoria = justificacion
    movimiento.save()


def _mover_stock(user, entrada, cantidad):
    """Consume el origen e ingresa el destino, con sus movimientos de kárdex.
    Devuelve (stock_origen, lote_origen, lote_destino)."""
    justificacion = entrada['justificacion']

    # 1. Consumir stock de origen (materia prima / producto base)
    stock_origen = _stock_origen_bloqueado(entrada)
    lote_origen = stock_origen.lote
    if stock_origen.cantidad < cantidad:
        raise _StockInsuficiente(stock_origen.cantidad)
    stock_origen.cantidad -= cantidad
    stock_origen._justificacion_auditoria = justificacion
    stock_origen.save()
    _registrar_movimiento(
        justificacion,
        tipo_movimiento='CONSUMO',  # O un tipo nuevo 'TRANSFORMACION_SALIDA'
        producto_id=entrada['producto_origen_id'],
        # Sin bodega_destino: el kárdex la leería como una entrada.
        bodega_origen_id=entrada['bodega_origen_id'],
        lote=lote_origen,
        cantidad=cantidad,
        usuario=user,
        documento_ref=f"TRANSF->{entrada['producto_destino_id']}",
        saldo_resultante=stock_origen.cantidad,  # Guardamos el saldo POST-consumo
    )

    # 2. Determinar lote de destino: por defecto mantiene el lote
    lote_destino = lote_origen
    if entrada['nuevo_lote_codigo']:
        # maquina es ForeignKey(Maquina); no se puede asignar un string.
        lote_destino, _ = LoteProduccion.objects.get_or_create(
            codigo_lote=entrada['nuevo_lote_codigo'],
            defaults={
                'peso_neto_producido': cantidad,
                'operario': user,
                'turno': 'N/A',
                'hora_inicio': timezone.now(),
                'hora_final': timezone.now(),
            }
        )

    # 3. Ingresar stock de destino (producto transformado)
    stock_destino, _ = StockBodega.objects.select_for_update().get_or_create(
        bodega_id=entrada['bodega_destino_id'],
        producto_id=entrada['producto_destino_id'],
        lote=lote_destino,
        defaults={'cantidad': 0}
    )
    stock_destino.cantidad += cantidad
    stock_destino._justificacion_auditoria = justificacion
    stock_destino.save()
    _registrar_movimiento(
        justificacion,
        tipo_movimiento='PRODUCCION',  # O un tipo nuevo 'TRANSFORMACION_ENTRADA'
        producto_id=entrada['producto_destino_id'],
        # Sin bodega_origen: el kárdex la leería como una salida.
        bodega_destino_id=entrada['bodega_destino_id'],
        lote=lote_destino,
        cantidad=cantidad,
        usuario=user,
        documento_ref=f"TRANSF<-{entrada['producto_origen_id']}",
        saldo_resultante=stock_destino.cantidad,  # Guardamos el saldo POST-producción
    )
    return stock_origen, lote_origen, lote_destino


def _registrar_trazabilidad_mes(user, entrada, cantidad, stock_origen, lote_origen, lote_destino):
    """4. Trazabilidad MES (Nivel 3) y grafo DAG GenealogiaLote.

    Best-effort: corre en su propio savepoint y un fallo solo se registra, sin revertir
    la transformación."""
    try:
        with transaction.atomic():
            from gestion.models import (
                Area,
                ConsumoMaterial,
                CorridaProduccion,
                GenealogiaLote,
                OperacionProduccion,
                ProduccionSalida,
            )
            sede = StockBodega.objects.select_related('bodega__sede').get(id=stock_origen.id).bodega.sede
            if not sede:
                return
            area = sede.areas.first()
            if not area:
                area, _ = Area.objects.get_or_create(sede=sede, defaults={'nombre': 'Área General'})
            autenticado = user if user.is_authenticated else None

            corrida, _ = CorridaProduccion.objects.get_or_create(
                codigo=f"CORR-TRANSF-{sede.id}-{timezone.now().date().strftime('%Y%m%d')}",
                defaults={
                    'sede': sede,
                    'area': area,
                    'modalidad': 'CONTINUA',
                    'turno': 'General',
                    'fecha_jornada': timezone.now().date(),
                    'hora_inicio': timezone.now(),
                    'supervisor': autenticado,
                    'estado': 'en_proceso',
                }
            )
            operacion = OperacionProduccion.objects.create(
                corrida=corrida,
                numero_secuencia=corrida.operaciones.count() + 1,
                operario=autenticado,
                hora_inicio=timezone.now(),
                hora_fin=timezone.now(),
                estado='completada',
                observaciones=(entrada['justificacion'] or
                               f"Transformación {entrada['producto_origen_id']} -> {entrada['producto_destino_id']}"),
            )
            ConsumoMaterial.objects.create(
                operacion=operacion,
                lote_origen=lote_origen,
                producto_id=entrada['producto_origen_id'],
                bodega_origen_id=entrada['bodega_origen_id'],
                cantidad_consumida=cantidad,
            )
            ProduccionSalida.objects.create(
                operacion=operacion,
                lote_generado=lote_destino,
                producto_id=entrada['producto_destino_id'],
                bodega_destino_id=entrada['bodega_destino_id'],
                cantidad_neta=cantidad,
                clasificacion_calidad='primera',
            )
            if lote_origen and lote_destino and lote_origen.id != lote_destino.id:
                GenealogiaLote.objects.get_or_create(
                    lote_padre=lote_origen,
                    lote_hijo=lote_destino,
                    operacion=operacion,
                    defaults={'cantidad_padre_usada': cantidad},
                )
    except Exception as err:
        logger.warning("Trazabilidad MES en transformación: %s", err, exc_info=True)


class TransformacionAPIView(APIView):
    """
    API para registrar la TRANSFORMACIÓN de un producto en otro (ej. Proceso productivo simple).
    Mueve stock de Origen (Producto A) a Destino (Producto B).
    """
    permission_classes = [IsInventoryWriterOrAdmin]

    def post(self, request, *args, **kwargs):
        try:
            entrada = _leer_entrada(request.data)
            _validar_alcance(request.user, entrada)
            cantidad = _parse_cantidad(entrada['cantidad'])
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                stock_origen, lote_origen, lote_destino = _mover_stock(request.user, entrada, cantidad)
                _registrar_trazabilidad_mes(request.user, entrada, cantidad, stock_origen, lote_origen, lote_destino)
        except _StockInsuficiente as e:
            return Response({"error": f"Stock insuficiente en origen. Disponible: {e.disponible}"},
                            status=status.HTTP_400_BAD_REQUEST)
        except StockBodega.DoesNotExist:
            # 400: regla de negocio (no hay fila de stock), no confundir con 404 de ruta
            return Response(
                {
                    "error": (
                        "No hay stock registrado para ese producto en la bodega de origen "
                        "con el lote indicado (incluido «sin lote»). Cree o ajuste el stock antes."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error inesperado en transformación de stock")
            return Response({"error": "Error inesperado al registrar la transformación."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Transformación registrada correctamente."}, status=status.HTTP_201_CREATED)
