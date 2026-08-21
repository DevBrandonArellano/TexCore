from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal

from .core import Sede, Area, CustomUser, AuditableModelMixin
from .catalogo import Producto, Bodega
from .maquina import Maquina, ProcessStep
from .formula import FormulaColor, FaseReceta


class OrdenProduccion(AuditableModelMixin, models.Model):
    campos_auditables = [
        'codigo',
        'producto_entrada',
        'producto_salida',
        'peso_neto_requerido',
        'estado',
        'maquina_asignada',
        'operario_asignado',
        'prioridad',
        'bodega_entrada',
        'bodega_salida']
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('en_proceso', 'En Proceso'), ('finalizada', 'Finalizada')]
    PRIORIDAD_CHOICES = [('baja', 'Baja'), ('normal', 'Normal'), ('alta', 'Alta'), ('urgente', 'Urgente')]

    codigo = models.CharField(max_length=100)
    producto_entrada = models.ForeignKey(
        'Producto', on_delete=models.PROTECT, db_index=True,
        related_name='ordenes_como_entrada',
        null=True, blank=True,
        verbose_name='Producto de Entrada'
    )
    producto_salida = models.ForeignKey(
        'Producto', on_delete=models.PROTECT, db_index=True,
        related_name='ordenes_como_salida',
        null=True, blank=True,
        verbose_name='Producto de Salida'
    )
    formula_color = models.ForeignKey(FormulaColor, on_delete=models.CASCADE, null=True, blank=True)
    bodega_entrada = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        related_name='ordenes_entrada',
        null=True, blank=True,
        verbose_name='Bodega de Entrada (MP)'
    )
    bodega_salida = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        related_name='ordenes_salida',
        null=True, blank=True,
        verbose_name='Bodega de Salida (PT)'
    )
    area = models.ForeignKey('Area', on_delete=models.PROTECT, related_name='ordenes_produccion', null=True, blank=True)
    peso_neto_requerido = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='normal', db_index=True)
    inventario_descontado = models.BooleanField(default=False)

    # Planificación y Asignación
    fecha_inicio_planificada = models.DateField(null=True, blank=True)
    fecha_fin_planificada = models.DateField(null=True, blank=True)
    maquina_asignada = models.ForeignKey(
        'Maquina',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_asignadas')
    operario_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_asignadas')
    observaciones = models.CharField(max_length=500, blank=True, null=True)

    # Gestión de químicos - bodega de uso diario en tintorería
    bodega_quimicos = models.ForeignKey(Bodega, on_delete=models.SET_NULL, null=True,
                                        blank=True, related_name='ordenes_quimicos')

    fecha_creacion = models.DateField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True, db_index=True)

    def __str__(self):
        return f"OP-{self.codigo} para {self.producto_entrada.descripcion if self.producto_entrada else 'N/A'}"

    def generate_next_lote_codigo(self):
        """
        Genera el siguiente código de lote secuencial para esta orden.
        Ejemplo: OP-101-L1, OP-101-L2, etc.
        """
        count = self.lotes.count() + 1
        return f"{self.codigo}-L{count}"

    @property
    def peso_producido(self):
        from django.db.models import Sum
        return self.lotes.aggregate(Sum('peso_neto_producido'))['peso_neto_producido__sum'] or 0

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_neto_requerido__gt=0),
                name='gestion_ordenproduccion_peso_neto_positivo',
            )
        ]
        unique_together = ('codigo', 'sede')


class DescargaQuimicoOP(models.Model):
    # Artefacto RUP: Entidad de Dominio - Registro de descarga química
    # Caso de Uso: CU-DescargaQuimicaAutomatica
    # Patrón: Entity + Audit Trail (inmutable post-creación)
    ESTADO_CHOICES = [
        ('aplicada', 'Aplicada'),
        ('revertida', 'Revertida'),
    ]
    TIPO_CALCULO_CHOICES = [
        ('gr_l', 'Concentración (gr/L)'),
        ('pct', 'Agotamiento (%)'),
    ]

    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='descargas_quimicos')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    fase = models.ForeignKey(FaseReceta, on_delete=models.SET_NULL, null=True, blank=True)
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT)
    tipo_calculo = models.CharField(max_length=10, choices=TIPO_CALCULO_CHOICES, default='gr_l')
    cantidad_calculada_kg = models.DecimalField(max_digits=12, decimal_places=6)
    cantidad_real_kg = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='aplicada')
    fecha_descarga = models.DateTimeField(auto_now_add=True)
    descargado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    justificacion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Descarga Química OP'
        verbose_name_plural = 'Descargas Químicas OP'
        ordering = ['-fecha_descarga']
        indexes = [
            models.Index(fields=['orden_produccion', 'estado']),
            models.Index(fields=['bodega', 'fecha_descarga']),
        ]

    def __str__(self):
        return (
            f"Descarga {self.producto.descripcion} "
            f"({self.cantidad_calculada_kg}kg) - OP {self.orden_produccion.codigo}"
        )


class AreaProcessStep(models.Model):
    """
    Define los subprocesos de un área con su orden y tipo de flujo.
    Permite configurar qué ProcessSteps ejecuta cada área y en qué orden/paralelismo.
    """
    FLUJO_CHOICES = [
        ('secuencial', 'Secuencial'),
        ('paralelo', 'Paralelo'),
    ]

    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='subprocesos')
    proceso = models.ForeignKey(ProcessStep, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(help_text="Orden de ejecución (menor número = primero)")
    tipo_flujo = models.CharField(max_length=20, choices=FLUJO_CHOICES, default='secuencial')
    es_bloqueante = models.BooleanField(default=True,
                                        help_text="Si es True, los siguientes procesos esperan a que se complete")

    class Meta:
        unique_together = ('area', 'proceso')
        ordering = ['orden']

    def __str__(self):
        return f"{self.area.nombre} → {self.proceso.name} (Orden: {self.orden})"


class OrdenProduccionSubproceso(models.Model):
    """
    Rastrea el progreso de cada subproceso en una orden de producción.
    Permite al jefe de área monitorear y controlar cada fase.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('pausado', 'Pausado'),
        ('rechazado', 'Rechazado'),
    ]

    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='subprocesos')
    area_proceso = models.ForeignKey(AreaProcessStep, on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)

    # Tiempos
    fecha_inicio_planificada = models.DateTimeField(null=True, blank=True)
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)

    # Responsable
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subprocesos_responsable'
    )

    # Observaciones y validación
    observaciones = models.TextField(blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True, help_text="Si fue rechazado, incluir el motivo")

    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('orden_produccion', 'area_proceso')
        ordering = ['area_proceso__orden']
        indexes = [
            models.Index(fields=['orden_produccion', 'estado']),
            models.Index(fields=['usuario_responsable', 'estado']),
        ]

    def __str__(self):
        return f"OP-{self.orden_produccion.codigo} → {self.area_proceso.proceso.name} ({self.get_estado_display()})"

    @property
    def duracion_minutos(self):
        """Retorna la duración en minutos si el subproceso está completado."""
        if self.fecha_inicio_real and self.fecha_fin_real:
            delta = self.fecha_fin_real - self.fecha_inicio_real
            return int(delta.total_seconds() / 60)
        return None


class LoteProduccion(models.Model):
    CALIDAD_CHOICES = [
        ('primera', 'Primera Calidad'),
        ('segunda', 'Segunda Calidad'),
        ('saldo', 'Saldo / Retazo'),
    ]
    TIPO_MERMA_CHOICES = [
        ('maquina', 'Falla Técnica / Máquina'),
        ('material', 'Calidad de Hilo / Material'),
        ('setup', 'Arranque / Setup'),
        ('corte', 'Corte / Empalme'),
        ('otro', 'Otro'),
    ]

    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE,
                                         related_name='lotes', null=True, blank=True)
    codigo_lote = models.CharField(max_length=100)
    peso_neto_producido = models.DecimalField(max_digits=12, decimal_places=3)
    operario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    maquina = models.ForeignKey(Maquina, on_delete=models.SET_NULL, null=True, related_name='lotes_producidos')
    turno = models.CharField(max_length=50)
    hora_inicio = models.DateTimeField()
    hora_final = models.DateTimeField()

    # Mermas y Calidad
    peso_merma = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    tipo_merma = models.CharField(max_length=50, choices=TIPO_MERMA_CHOICES, blank=True, null=True)
    clasificacion_calidad = models.CharField(max_length=50, choices=CALIDAD_CHOICES, default='primera')

    # Nuevos campos para Empaquetado
    peso_bruto = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    tara = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    unidades_empaque = models.IntegerField(default=1)  # Ej: 12 rollos por caja, o 1 cono por funda
    presentacion = models.CharField(max_length=100, blank=True, null=True)  # Ej: Caja, Funda, Cono
    cantidad_metros = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Metros reenrollados para telas")

    # F0-001: trazabilidad de materia prima — qué lotes de MP del proveedor
    # alimentaron este lote producido (through inmutable con cantidad y usuario)
    materias_primas = models.ManyToManyField(
        'MateriaPrimaLote',
        through='ConsumoMateriaPrima',
        related_name='lotes_produccion',
        blank=True,
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        # Regla de negocio: la merma no puede ser mayor a la cantidad de la orden de producción
        if self.peso_merma and self.orden_produccion and self.orden_produccion.peso_neto_requerido:
            if Decimal(str(self.peso_merma)) > Decimal(str(self.orden_produccion.peso_neto_requerido)):
                raise ValidationError({
                    'peso_merma': f'La merma ({self.peso_merma} kg) no puede ser mayor a la cantidad '
                    f'requerida en la orden ({self.orden_produccion.peso_neto_requerido} kg).'
                })

        # Regla de negocio estricta: asignar unidades por defecto solo si no se especificaron explícitamente (>0)
        if self.presentacion and (not self.unidades_empaque or self.unidades_empaque <= 0):
            pres = self.presentacion.lower().strip()
            if pres == 'baño':
                self.unidades_empaque = 225  # Equivalencia total en conos
            elif pres == 'funda':
                self.unidades_empaque = 15   # Equivalencia en conos
            elif pres == 'cono':
                self.unidades_empaque = 1    # Unidad mínima

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_neto_producido__gte=0),
                name='gestion_loteproduccion_peso_neto_positivo'
            ),
            models.CheckConstraint(
                condition=models.Q(peso_bruto__gte=0),
                name='gestion_loteproduccion_peso_bruto_positivo'
            ),
            models.CheckConstraint(
                condition=models.Q(tara__gte=0),
                name='gestion_loteproduccion_tara_positiva'
            )
        ]
        unique_together = ('codigo_lote', 'orden_produccion')

    def __str__(self):
        return self.codigo_lote


class EventoEtiqueta(models.Model):
    """
    Registro inmutable del ciclo de vida de cada etiqueta física impresa para un lote.
    ISO 27001 A.12.4: auditoría de eventos de impresión/reetiquetado.

    Reimpresión (copia idéntica) vs Reetiquetado (cambio de datos, versiona y anula
    la etiqueta previa) — el codigo_lote y el QR de trazabilidad nunca cambian.
    """
    TIPO_EVENTO_CHOICES = [
        ('ORIGINAL', 'Original'),
        ('REIMPRESION', 'Reimpresión Idéntica'),
        ('REETIQUETADO', 'Reetiquetado con Cambio'),
    ]
    MOTIVO_CHOICES = [
        ('DANIADA', 'Etiqueta Dañada'),
        ('PERDIDA', 'Etiqueta Perdida'),
        ('ATASCO', 'Atasco de Impresora'),
        ('CORRECCION_PESO', 'Corrección de Peso'),
        ('RECLASIFICACION', 'Reclasificación de Calidad'),
        ('REEMPAQUE', 'Reempaque'),
        ('OTRO', 'Otro'),
    ]
    FORMATO_CHOICES = [
        ('ZPL', 'ZPL Zebra'),
        ('PDF', 'PDF Universal'),
    ]

    lote = models.ForeignKey(LoteProduccion, on_delete=models.CASCADE, related_name='etiquetas')
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    # secuencia: identifica cada evento físico de impresión (única por lote, siempre creciente).
    # version: versión de los DATOS de la etiqueta — se mantiene igual entre reimpresiones
    # idénticas y solo se incrementa cuando un REETIQUETADO cambia datos y anula la anterior.
    secuencia = models.PositiveIntegerField()
    version = models.PositiveIntegerField()
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES, blank=True, null=True)
    detalle_motivo = models.TextField(blank=True)
    usuario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='eventos_etiqueta')
    timestamp = models.DateTimeField(auto_now_add=True)
    datos_snapshot = models.JSONField()
    formato = models.CharField(max_length=3, choices=FORMATO_CHOICES, default='ZPL')
    anula_a = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='anulada_por'
    )
    anulada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('lote', 'secuencia')
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['lote', 'secuencia']),
        ]
        ordering = ['lote', 'secuencia']

    def __str__(self):
        return f'{self.lote.codigo_lote} v{self.version} #{self.secuencia} ({self.tipo_evento})'


class ComponenteMezclaOP(AuditableModelMixin, models.Model):
    """
    Receta de mezcla para una OP. Definida por Jefe de Área.
    COBIT DSS06: sum(porcentaje) == 100 validado en serializer y service.
    ISO 27001 A.12.4: auditoría automática vía AuditableModelMixin.
    """
    campos_auditables = ['porcentaje', 'cantidad_kg', 'producto', 'bodega']

    orden = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='componentes_mezcla',
        verbose_name='Orden de Producción'
    )
    producto = models.ForeignKey(
        'Producto', on_delete=models.PROTECT,
        verbose_name='Producto Componente'
    )
    bodega = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        verbose_name='Bodega Origen del Componente'
    )
    porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Porcentaje (%)'
    )
    cantidad_kg = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Cantidad calculada (kg)'
    )

    class Meta:
        verbose_name = 'Componente de Mezcla'
        unique_together = [('orden', 'producto')]
        constraints = [
            models.CheckConstraint(
                check=models.Q(porcentaje__gt=0) & models.Q(porcentaje__lte=100),
                name='componente_porcentaje_rango'
            )
        ]

    def __str__(self):
        return f'{self.orden.codigo} — {self.producto.codigo} ({self.porcentaje}%)'


class ConsumoLoteDetalle(AuditableModelMixin, models.Model):
    """
    Registro inmutable del consumo real de lotes de entrada al producir un lote.
    ISO 27001 A.12.4: NO permite UPDATE. Solo DELETE vía endpoint rechazar/ con justificación.
    """
    campos_auditables = ['cantidad_consumida']

    lote_produccion = models.ForeignKey(
        LoteProduccion, on_delete=models.CASCADE,
        related_name='consumos_detalle',
        verbose_name='Lote Producido (output)'
    )
    lote_origen = models.ForeignKey(
        LoteProduccion, on_delete=models.PROTECT,
        related_name='usos_como_input',
        verbose_name='Lote de Origen (input)'
    )
    cantidad_consumida = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Cantidad Consumida (kg)'
    )
    genera_nuevo_lote = models.BooleanField(
        default=True,
        verbose_name='¿Genera nuevo código de lote?'
    )

    class Meta:
        verbose_name = 'Detalle de Consumo de Lote'
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad_consumida__gt=0),
                name='consumo_cantidad_positiva'
            )
        ]

    def __str__(self):
        return (f'{self.lote_produccion.codigo_lote} ← '
                f'{self.lote_origen.codigo_lote} ({self.cantidad_consumida} kg)')


class EtapaProduccion(models.Model):
    """
    Define las etapas secuenciales de producción dentro de un área.
    Cada etapa es ejecutada por una máquina específica y tiene:
    - Bodega de entrada (donde obtiene material)
    - Bodega de salida (donde deja resultado)

    Ejemplo Área Tintura:
    - Etapa 1: Teñido (Máquina Tintura 1) → Bodega Tintura → Bodega Sec Tintura
    - Etapa 2: Secado (Máquina Secadora) → Bodega Sec Tintura → Bodega Final Tintura
    """
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='etapas_produccion')
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(help_text="Orden secuencial de ejecución (1, 2, 3...)")
    maquina = models.ForeignKey(Maquina, on_delete=models.PROTECT)

    bodega_entrada = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='etapas_entrada',
        help_text="Bodega de donde toma el material"
    )
    bodega_salida = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='etapas_salida',
        help_text="Bodega donde deposita el resultado"
    )

    tiempo_procesamiento_minutos = models.IntegerField(
        null=True, blank=True,
        help_text="Tiempo promedio estimado para esta etapa"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('area', 'orden')
        ordering = ['area', 'orden']
        verbose_name = 'Etapa de Producción'
        verbose_name_plural = 'Etapas de Producción'

    def __str__(self):
        return f"{self.area.nombre} → Etapa {self.orden}: {self.nombre}"


class TransferenciaInterarea(models.Model):
    """
    Registra la transferencia de producto de una área a la siguiente.
    Cuando un área termina su producción, transfiere el producto a la bodega
    inicial de la siguiente área.

    Vincula dos órdenes de producción (una por cada área).
    """
    orden_area_origen = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='transferencias_salida',
        help_text="Orden de producción que generó el producto"
    )
    orden_area_destino = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='transferencias_entrada',
        help_text="Orden de producción que recibe el producto"
    )

    bodega_origen = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='transferencias_origen',
        help_text="Bodega final del área origen"
    )
    bodega_destino = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='transferencias_destino',
        help_text="Bodega inicial del área destino (= MP para el área destino)"
    )

    cantidad_transferida = models.DecimalField(max_digits=12, decimal_places=3)
    fecha_transferencia = models.DateTimeField(auto_now_add=True)

    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_transferencia']
        indexes = [
            models.Index(fields=['orden_area_origen', 'orden_area_destino']),
            models.Index(fields=['fecha_transferencia']),
        ]
        verbose_name = 'Transferencia Interárea'
        verbose_name_plural = 'Transferencias Interárea'

    def __str__(self):
        return (
            f"Transferencia: OP-{self.orden_area_origen.codigo} "
            f"→ OP-{self.orden_area_destino.codigo} ({self.cantidad_transferida}kg)"
        )


class TransformacionProducto(AuditableModelMixin, models.Model):
    """
    Registra cada transformación de producto en una máquina dentro de una OP.

    Cada máquina del flujo recibe un producto con un código y entrega otro
    producto con código distinto (ej: TELA-001 → TELA-001-REC). El peso de
    salida suele ser menor por la merma del proceso.

    Diseño (SOLID):
    - SRP: única responsabilidad — modelar un paso de transformación y su merma.
    - La orquestación (asignar secuencia, validar continuidad de cadena, aislar
      por sede) vive en TransformacionService, no aquí.

    Trazabilidad: la cadena de transformaciones de una OP, encadenada entre
    áreas vía TransferenciaInterarea, reconstruye el flujo completo.
    ISO 27001 A.12.4: auditoría automática vía AuditableModelMixin.
    """
    campos_auditables = [
        'numero_secuencia', 'producto_entrada', 'producto_salida',
        'maquina', 'operario', 'peso_entrada', 'peso_salida', 'merma', 'estado',
    ]
    ESTADO_CHOICES = [
        ('completada', 'Completada'),
        ('rechazada', 'Rechazada'),
    ]

    orden_produccion = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='transformaciones',
        verbose_name='Orden de Producción'
    )
    etapa = models.ForeignKey(
        EtapaProduccion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transformaciones',
        help_text='Etapa planificada que ejecuta esta transformación (opcional)'
    )
    numero_secuencia = models.PositiveIntegerField(
        default=1,
        help_text='Orden secuencial de la transformación dentro de la OP (1, 2, 3...)'
    )

    producto_entrada = models.ForeignKey(
        'Producto', on_delete=models.PROTECT,
        related_name='transformaciones_como_entrada',
        verbose_name='Producto que entra a la máquina'
    )
    producto_salida = models.ForeignKey(
        'Producto', on_delete=models.PROTECT,
        related_name='transformaciones_como_salida',
        verbose_name='Producto que sale de la máquina (nuevo código)'
    )

    maquina = models.ForeignKey('Maquina', on_delete=models.PROTECT, related_name='transformaciones')
    operario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transformaciones_operadas'
    )

    peso_entrada = models.DecimalField(max_digits=12, decimal_places=3)
    peso_salida = models.DecimalField(max_digits=12, decimal_places=3)
    merma = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0'), editable=False,
        help_text='Calculada automáticamente: peso_entrada - peso_salida'
    )

    cantidad_entrada = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    cantidad_salida = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='completada', db_index=True)
    observaciones = models.CharField(max_length=500, blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['orden_produccion', 'numero_secuencia']
        constraints = [
            models.UniqueConstraint(
                fields=['orden_produccion', 'numero_secuencia'],
                name='transf_unica_por_secuencia_en_op',
            ),
            models.CheckConstraint(
                condition=models.Q(peso_entrada__gte=0) & models.Q(peso_salida__gte=0),
                name='gestion_transformacion_pesos_no_negativos',
            ),
        ]
        indexes = [
            models.Index(fields=['orden_produccion', 'numero_secuencia']),
            models.Index(fields=['maquina', 'fecha_creacion']),
        ]
        verbose_name = 'Transformación de Producto'
        verbose_name_plural = 'Transformaciones de Producto'

    def clean(self):
        super().clean()
        # Regla de negocio: una transformación debe procesar material (> 0 kg).
        if self.peso_entrada is not None and self.peso_entrada <= 0:
            raise ValidationError({
                'peso_entrada': 'El peso de entrada debe ser mayor que cero.'
            })
        # Calcular merma aquí para que full_clean() la valide aun sin guardar.
        if self.peso_entrada is not None and self.peso_salida is not None:
            self.merma = self.peso_entrada - self.peso_salida
            if self.merma < 0:
                raise ValidationError({
                    'peso_salida': 'El peso de salida no puede superar el peso de entrada (merma negativa).'
                })
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({
                'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'
            })

    def __str__(self):
        return (
            f"OP-{self.orden_produccion.codigo} #{self.numero_secuencia}: "
            f"{self.producto_entrada.codigo} → {self.producto_salida.codigo} "
            f"({self.maquina.nombre})"
        )
