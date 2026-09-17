import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .catalogo import Bodega, Producto
from .core import Area, AuditableModelMixin, CustomUser, Sede, SedeResolvableMixin
from .maquina import LineaProduccion, Maquina, ProcessStep
from .produccion import LoteProduccion, OrdenProduccion
from .ventas import PedidoVenta

logger = logging.getLogger(__name__)


class CorridaProduccion(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Contenedor de ejecución en planta (Nivel 3 MES - ISA-95).
    Agrupa operaciones por turno, máquina, línea y modalidad productiva
    (Continua, Contra Stock o Bajo Pedido).
    """
    MODALIDAD_CHOICES = [
        ('CONTINUA', 'Producción Continua'),
        ('STOCK', 'Producción Contra Stock'),
        ('PEDIDO', 'Producción Bajo Pedido'),
    ]
    ESTADO_CHOICES = [
        ('en_proceso', 'En Proceso'),
        ('pausada', 'Pausada'),
        ('finalizada', 'Finalizada'),
        ('anulada', 'Anulada'),
    ]

    campos_auditables = [
        'codigo',
        'modalidad',
        'estado',
        'turno',
        'fecha_jornada',
        'maquina_principal',
        'supervisor',
        'plan_produccion',
        'detalle_plan',
    ]

    codigo = models.CharField(max_length=100, db_index=True)
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        related_name='corridas_produccion',
        verbose_name='Sede',
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name='corridas_produccion',
        verbose_name='Área Productiva',
    )
    linea = models.ForeignKey(
        LineaProduccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_produccion',
        verbose_name='Línea de Producción',
    )
    maquina_principal = models.ForeignKey(
        Maquina,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_produccion',
        verbose_name='Máquina Principal',
    )
    modalidad = models.CharField(
        max_length=20,
        choices=MODALIDAD_CHOICES,
        default='CONTINUA',
        db_index=True,
        verbose_name='Modalidad Productiva',
    )
    orden_produccion = models.ForeignKey(
        OrdenProduccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_mes',
        verbose_name='Orden de Producción Asociada',
    )
    plan_produccion = models.ForeignKey(
        'gestion.PlanProduccion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_mes',
        verbose_name='Plan de Producción Asociado',
    )
    detalle_plan = models.ForeignKey(
        'gestion.DetallePlanProduccion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_mes',
        verbose_name='Detalle de Plan Asociado',
    )
    pedido_venta = models.ForeignKey(
        PedidoVenta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_mes',
        verbose_name='Pedido Comercial Asociado',
    )
    turno = models.CharField(max_length=50, verbose_name='Turno Productivo')
    fecha_jornada = models.DateField(db_index=True, verbose_name='Fecha de Jornada')
    hora_inicio = models.DateTimeField(verbose_name='Hora de Inicio')
    hora_fin = models.DateTimeField(null=True, blank=True, verbose_name='Hora de Fin')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='en_proceso',
        db_index=True,
        verbose_name='Estado de la Corrida',
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corridas_supervisadas',
        verbose_name='Supervisor Responsable',
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Corrida de Producción'
        verbose_name_plural = 'Corridas de Producción'
        ordering = ['-fecha_jornada', '-hora_inicio']
        constraints = [
            models.UniqueConstraint(
                fields=['sede', 'codigo'],
                name='gestion_corridaproduccion_unique_sede_codigo',
            )
        ]
        indexes = [
            models.Index(fields=['sede', 'estado'], name='idx_corrida_sede_estado'),
            models.Index(fields=['fecha_jornada', 'turno'], name='idx_corrida_jornada_turno'),
            models.Index(fields=['modalidad', 'estado'], name='idx_corrida_mod_estado'),
        ]

    def __str__(self):
        sede_nombre = self.sede.nombre if self.sede_id else "Sin Sede"
        return f"Corrida {self.codigo} ({self.get_modalidad_display()}) - {sede_nombre}"

    def get_audit_sede_id(self):
        return self.sede_id

    def clean(self):
        if self.hora_fin and self.hora_inicio and self.hora_fin < self.hora_inicio:
            raise ValidationError({
                'hora_fin': 'La hora de fin no puede ser anterior a la hora de inicio.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class OperacionProduccion(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Paso unitario de transformación en máquina dentro de una corrida (Nivel 3 MES).
    Garantiza el registro preciso de tiempos, recursos consumidos, salidas netas
    y mermas generadas.
    """
    ESTADO_CHOICES = [
        ('en_curso', 'En Curso'),
        ('completada', 'Completada'),
        ('rechazada', 'Rechazada'),
        ('revertida', 'Revertida'),
    ]

    campos_auditables = [
        'numero_secuencia',
        'maquina',
        'proceso',
        'operario',
        'estado',
        'hora_inicio',
        'hora_fin',
    ]

    corrida = models.ForeignKey(
        CorridaProduccion,
        on_delete=models.CASCADE,
        related_name='operaciones',
        verbose_name='Corrida de Producción',
    )
    numero_secuencia = models.PositiveIntegerField(
        default=1,
        verbose_name='Número de Secuencia',
    )
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name='operaciones_mes',
        verbose_name='Máquina Empleada',
    )
    proceso = models.ForeignKey(
        ProcessStep,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_mes',
        verbose_name='Paso de Proceso',
    )
    operario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='operaciones_mes_operadas',
        verbose_name='Operario Responsable',
    )
    hora_inicio = models.DateTimeField(verbose_name='Hora de Inicio')
    hora_fin = models.DateTimeField(null=True, blank=True, verbose_name='Hora de Fin')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='en_curso',
        db_index=True,
        verbose_name='Estado de la Operación',
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    motivo_reversion = models.TextField(
        blank=True,
        null=True,
        help_text='Justificación obligatoria en caso de anulación o reversión de inventarios.',
        verbose_name='Motivo de Reversión',
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Operación de Producción'
        verbose_name_plural = 'Operaciones de Producción'
        ordering = ['corrida', 'numero_secuencia']
        constraints = [
            models.UniqueConstraint(
                fields=['corrida', 'numero_secuencia'],
                name='gestion_operacionproduccion_unique_corrida_secuencia',
            )
        ]
        indexes = [
            models.Index(fields=['corrida', 'estado'], name='idx_operacion_corrida_estado'),
            models.Index(fields=['maquina', 'hora_inicio'], name='idx_operacion_maq_inicio'),
        ]

    def __str__(self):
        maquina_nombre = self.maquina.nombre if self.maquina_id else "N/A"
        return f"Op #{self.numero_secuencia} en {self.corrida.codigo} ({maquina_nombre})"

    def get_audit_sede_id(self):
        return self.corrida.sede_id if self.corrida_id else None

    def clean(self):
        if self.hora_fin and self.hora_inicio and self.hora_fin < self.hora_inicio:
            raise ValidationError({
                'hora_fin': 'La hora de fin no puede ser anterior a la hora de inicio.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ConsumoMaterial(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Entrada real consumida por una operación de producción en máquina.
    Descuenta de StockBodega y genera MovimientoInventario de tipo CONSUMO.
    """
    campos_auditables = ['cantidad_consumida', 'costo_unitario']

    operacion = models.ForeignKey(
        OperacionProduccion,
        on_delete=models.CASCADE,
        related_name='consumos',
        verbose_name='Operación de Producción',
    )
    lote_origen = models.ForeignKey(
        LoteProduccion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='consumos_mes',
        verbose_name='Lote de Origen',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='consumos_mes',
        verbose_name='Producto Consumido',
    )
    bodega_origen = models.ForeignKey(
        Bodega,
        on_delete=models.PROTECT,
        related_name='consumos_mes',
        verbose_name='Bodega de Origen',
    )
    cantidad_consumida = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name='Cantidad Consumida',
    )
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.000'),
        verbose_name='Costo Unitario',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Consumo de Material'
        verbose_name_plural = 'Consumos de Materiales'
        ordering = ['operacion', 'id']
        indexes = [
            models.Index(fields=['operacion', 'producto'], name='idx_consumo_op_prod'),
            models.Index(fields=['lote_origen'], name='idx_consumo_lote_origen'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad_consumida__gt=0),
                name='gestion_consumomaterial_cantidad_gt_zero',
            )
        ]

    def __str__(self):
        return f"Consumo {self.cantidad_consumida} {self.producto.unidad_medida} de {self.producto.codigo}"

    def get_audit_sede_id(self):
        if self.bodega_origen_id:
            return self.bodega_origen.sede_id
        return self.operacion.corrida.sede_id if self.operacion_id else None

    def clean(self):
        if self.cantidad_consumida is not None and self.cantidad_consumida <= 0:
            raise ValidationError({
                'cantidad_consumida': 'La cantidad consumida debe ser estrictamente mayor a 0.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ProduccionSalida(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Salida neta generada por una operación de producción en máquina.
    Ingresa a StockBodega y genera MovimientoInventario de tipo PRODUCCION.
    """
    CALIDAD_CHOICES = [
        ('primera', 'Primera Calidad'),
        ('segunda', 'Segunda Calidad'),
        ('saldo', 'Saldo / Retazo'),
    ]

    campos_auditables = [
        'cantidad_neta',
        'clasificacion_calidad',
        'peso_bruto',
        'tara',
        'unidades_empaque',
        'cantidad_metros',
    ]

    operacion = models.ForeignKey(
        OperacionProduccion,
        on_delete=models.CASCADE,
        related_name='salidas',
        verbose_name='Operación de Producción',
    )
    lote_generado = models.ForeignKey(
        LoteProduccion,
        on_delete=models.PROTECT,
        related_name='salidas_mes',
        verbose_name='Lote Generado',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='salidas_mes',
        verbose_name='Producto Resultante',
    )
    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.PROTECT,
        related_name='salidas_mes',
        verbose_name='Bodega de Destino',
    )
    cantidad_neta = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name='Cantidad Neta Producida',
    )
    clasificacion_calidad = models.CharField(
        max_length=20,
        choices=CALIDAD_CHOICES,
        default='primera',
        verbose_name='Clasificación de Calidad',
    )
    peso_bruto = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.000'),
        verbose_name='Peso Bruto',
    )
    tara = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.000'),
        verbose_name='Tara',
    )
    unidades_empaque = models.PositiveIntegerField(
        default=1,
        verbose_name='Unidades por Empaque',
    )
    cantidad_metros = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Metros Producidos',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Salida de Producción'
        verbose_name_plural = 'Salidas de Producción'
        ordering = ['operacion', 'id']
        indexes = [
            models.Index(fields=['operacion', 'producto'], name='idx_salida_op_prod'),
            models.Index(fields=['lote_generado'], name='idx_salida_lote_gen'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad_neta__gt=0),
                name='gestion_produccionsalida_cantidad_gt_zero',
            )
        ]

    def __str__(self):
        lote_cod = self.lote_generado.codigo_lote if self.lote_generado_id else "N/A"
        return f"Salida {self.cantidad_neta} {self.producto.unidad_medida} de {self.producto.codigo} (Lote: {lote_cod})"

    def get_audit_sede_id(self):
        if self.bodega_destino_id:
            return self.bodega_destino.sede_id
        return self.operacion.corrida.sede_id if self.operacion_id else None

    def clean(self):
        if self.cantidad_neta is not None and self.cantidad_neta <= 0:
            raise ValidationError({
                'cantidad_neta': 'La cantidad neta producida debe ser estrictamente mayor a 0.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class MermaDesperdicio(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Pérdidas, mermas de proceso o subproductos vendibles generados en una operación.
    Permite balance exacto de masa y opcionalmente valorización de subproductos.
    """
    TIPO_MERMA_CHOICES = [
        ('maquina', 'Falla Técnica / Máquina'),
        ('material', 'Defecto de Material / Hilo'),
        ('setup', 'Arranque / Setup'),
        ('corte', 'Desperdicio de Corte / Empalme'),
        ('humedad', 'Pérdida por Humedad / Volatilización'),
        ('otro', 'Otro Desperdicio'),
    ]

    campos_auditables = [
        'peso_merma',
        'tipo_merma',
        'es_subproducto_vendible',
    ]

    operacion = models.ForeignKey(
        OperacionProduccion,
        on_delete=models.CASCADE,
        related_name='mermas',
        verbose_name='Operación de Producción',
    )
    peso_merma = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name='Peso de Merma (kg)',
    )
    tipo_merma = models.CharField(
        max_length=30,
        choices=TIPO_MERMA_CHOICES,
        default='maquina',
        verbose_name='Tipo de Merma',
    )
    es_subproducto_vendible = models.BooleanField(
        default=False,
        verbose_name='¿Es Subproducto Vendible?',
        help_text='Indica si esta merma ingresa a inventario como subproducto recuperable/vendible.',
    )
    producto_subproducto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mermas_como_subproducto',
        verbose_name='Producto Subproducto',
    )
    bodega_subproducto = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mermas_como_subproducto',
        verbose_name='Bodega Destino del Subproducto',
    )
    lote_subproducto = models.ForeignKey(
        LoteProduccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mermas_subproducto_lote',
        verbose_name='Lote Asignado al Subproducto',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Merma y Desperdicio'
        verbose_name_plural = 'Mermas y Desperdicios'
        ordering = ['operacion', 'id']
        indexes = [
            models.Index(fields=['operacion', 'tipo_merma'], name='idx_merma_op_tipo'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_merma__gte=0),
                name='gestion_mermadesperdicio_peso_gte_zero',
            )
        ]

    def __str__(self):
        return f"Merma {self.peso_merma} kg ({self.get_tipo_merma_display()})"

    def get_audit_sede_id(self):
        if self.operacion_id and self.operacion.corrida_id:
            return self.operacion.corrida.sede_id
        return None

    def clean(self):
        if self.peso_merma is not None and self.peso_merma < 0:
            raise ValidationError({
                'peso_merma': 'El peso de merma no puede ser negativo.'
            })
        if self.es_subproducto_vendible:
            if not self.producto_subproducto:
                raise ValidationError({
                    'producto_subproducto': 'Debe especificar el producto subproducto para una merma vendible.'
                })
            if not self.bodega_subproducto:
                raise ValidationError({
                    'bodega_subproducto': 'Debe especificar la bodega destino para una merma vendible.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class GenealogiaLote(models.Model):
    """
    Grafo Acíclico Dirigido (DAG) de trazabilidad entre lotes.
    Modela relaciones N-a-N (Mezclas, Divisiones y Transformaciones)
    con conservación estricta de cantidad padre usada.
    """
    lote_padre = models.ForeignKey(
        LoteProduccion,
        on_delete=models.PROTECT,
        related_name='aristas_hijos',
        verbose_name='Lote Padre (Insumo)',
    )
    lote_hijo = models.ForeignKey(
        LoteProduccion,
        on_delete=models.PROTECT,
        related_name='aristas_padres',
        verbose_name='Lote Hijo (Producido)',
    )
    operacion = models.ForeignKey(
        OperacionProduccion,
        on_delete=models.CASCADE,
        related_name='genealogias',
        verbose_name='Operación que ejecutó la transformación',
    )
    cantidad_padre_usada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name='Cantidad del Padre Usada (kg)',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Genealogía de Lote'
        verbose_name_plural = 'Genealogías de Lotes'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['lote_padre', 'lote_hijo', 'operacion'],
                name='gestion_genealogialote_unique_padre_hijo_op',
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_padre_usada__gt=0),
                name='gestion_genealogialote_cantidad_gt_zero',
            ),
        ]
        indexes = [
            models.Index(fields=['lote_padre', 'lote_hijo'], name='idx_genealogia_padre_hijo'),
            models.Index(fields=['lote_hijo', 'lote_padre'], name='idx_genealogia_hijo_padre'),
        ]

    def __str__(self):
        return f"Genealogía {self.lote_padre.codigo_lote} -> {self.lote_hijo.codigo_lote} ({self.cantidad_padre_usada} kg)"

    def clean(self):
        if self.lote_padre_id and self.lote_hijo_id and self.lote_padre_id == self.lote_hijo_id:
            raise ValidationError({
                'lote_hijo': 'Un lote no puede ser padre de sí mismo (evita ciclos reflexivos en el DAG).'
            })
        if self.cantidad_padre_usada is not None and self.cantidad_padre_usada <= 0:
            raise ValidationError({
                'cantidad_padre_usada': 'La cantidad del lote padre usada debe ser estrictamente mayor a 0.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
