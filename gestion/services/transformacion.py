"""
TransformacionService — orquesta el registro de transformaciones máquina a máquina.

Diseño (SOLID / Clean Code):
- SRP: única responsabilidad — registrar un paso de transformación de forma
  consistente: asignar la secuencia, derivar el producto de entrada (continuidad
  de cadena), aislar por área/sede y persistir.
- Consistente con el patrón de servicios del proyecto (RegistroLoteService,
  MermaStockService): métodos estáticos + @transaction.atomic, sin estado.

Concurrencia (ISO 27001 A.12 / integridad):
- select_for_update() sobre la OP serializa la asignación de numero_secuencia,
  evitando que dos operarios obtengan la misma secuencia en paralelo.

RFC 5424: cada registro emite un log estructurado con extra={'sd': {...}}.
"""
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from gestion.models import (
    OrdenProduccion, TransformacionProducto, Maquina, Producto, CustomUser,
)

logger = logging.getLogger(__name__)


class TransformacionService:
    """Servicio de aplicación para registrar transformaciones de producto."""

    @staticmethod
    @transaction.atomic
    def registrar(orden, data: dict, user) -> TransformacionProducto:
        """
        Registra una transformación en la OP.

        El ``producto_entrada`` NO se confía al cliente cuando ya existe una
        transformación previa: se deriva del ``producto_salida`` de la última,
        garantizando la continuidad de la cadena por construcción.
        """
        # Bloqueo pesimista de la OP — serializa la asignación de secuencia.
        # En SQLite (tests) es no-op; en SQL Server (prod/CI) aplica el lock.
        orden = OrdenProduccion.objects.select_for_update().get(id=orden.id)

        maquina = TransformacionService._resolver_maquina(data.get('maquina'))

        # Aislamiento por área (multi-planta vía Sede): la máquina debe pertenecer
        # al área de la OP. Evita registrar en máquinas de otra área/sede.
        if orden.area_id and maquina.area_id != orden.area_id:
            raise ValidationError({
                'maquina': f'La máquina "{maquina.nombre}" no pertenece al área de la orden.'
            })

        ultima = orden.transformaciones.order_by('-numero_secuencia').first()
        numero_secuencia = (ultima.numero_secuencia + 1) if ultima else 1

        producto_entrada = TransformacionService._derivar_producto_entrada(
            orden, ultima, data.get('producto_entrada')
        )
        producto_salida = TransformacionService._resolver_producto(
            data.get('producto_salida'), 'producto_salida', sede_id=orden.sede_id
        )
        operario = TransformacionService._resolver_operario(data.get('operario'), user)

        transformacion = TransformacionProducto(
            orden_produccion=orden,
            etapa_id=data.get('etapa'),
            numero_secuencia=numero_secuencia,
            producto_entrada=producto_entrada,
            producto_salida=producto_salida,
            maquina=maquina,
            operario=operario,
            peso_entrada=Decimal(str(data['peso_entrada'])),
            peso_salida=Decimal(str(data['peso_salida'])),
            cantidad_entrada=data.get('cantidad_entrada'),
            cantidad_salida=data.get('cantidad_salida'),
            fecha_inicio=data.get('fecha_inicio'),
            fecha_fin=data.get('fecha_fin'),
            estado=data.get('estado', 'completada'),
            observaciones=data.get('observaciones', '') or '',
        )
        # AuditableModelMixin.save() ejecuta full_clean(): valida merma>=0,
        # coherencia de fechas y unicidad de secuencia, y emite el AuditLog.
        transformacion.save()

        logger.info(
            'Transformación de producto registrada',
            extra={'sd': {
                'rfc5424_severity': 6,
                'op': orden.codigo,
                'transformacion_id': transformacion.id,
                'numero_secuencia': transformacion.numero_secuencia,
                'producto_entrada': producto_entrada.codigo,
                'producto_salida': producto_salida.codigo,
                'maquina': maquina.nombre,
                'merma_kg': str(transformacion.merma),
                'sede_id': orden.sede_id,
            }},
        )
        return transformacion

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _derivar_producto_entrada(orden, ultima, producto_entrada_ref):
        """Continuidad de cadena: entrada = salida de la transformación previa."""
        if ultima is not None:
            return ultima.producto_salida
        # Primera transformación: usar la entrada de la OP, o la indicada en data.
        if producto_entrada_ref:
            return TransformacionService._resolver_producto(
                producto_entrada_ref, 'producto_entrada', sede_id=orden.sede_id
            )
        if orden.producto_entrada is None:
            raise ValidationError({
                'producto_entrada': (
                    'La orden no tiene producto de entrada definido; '
                    'debe indicarlo en la primera transformación.'
                )
            })
        return orden.producto_entrada

    @staticmethod
    def _resolver_maquina(ref):
        if ref is None:
            raise ValidationError({'maquina': 'La máquina es obligatoria.'})
        if isinstance(ref, Maquina):
            return ref
        try:
            return Maquina.objects.get(id=ref)
        except Maquina.DoesNotExist:
            raise ValidationError({'maquina': f'La máquina con id={ref} no existe.'})

    @staticmethod
    def _resolver_producto(ref, campo, sede_id=None):
        if ref is None:
            raise ValidationError({campo: f'{campo} es obligatorio.'})
        producto = ref if isinstance(ref, Producto) else None
        if producto is None:
            try:
                producto = Producto.objects.get(id=ref)
            except Producto.DoesNotExist:
                raise ValidationError({campo: f'El producto con id={ref} no existe.'})
        # Aislamiento multi-sede: un producto con sede definida debe pertenecer a
        # la sede de la orden. Los productos globales (sede=None) se permiten.
        if sede_id is not None and producto.sede_id is not None and producto.sede_id != sede_id:
            raise ValidationError({
                campo: f'El producto "{producto.codigo}" pertenece a otra sede.'
            })
        return producto

    @staticmethod
    def _resolver_operario(ref, user):
        if not ref:
            return user
        if isinstance(ref, CustomUser):
            return ref
        try:
            return CustomUser.objects.get(id=ref)
        except CustomUser.DoesNotExist:
            return user
