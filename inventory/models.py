from typing import Any

from django.conf import settings
from django.db import models

from gestion.models import AuditableModelMixin, Bodega, LoteProduccion, Producto, Proveedor, Sede, SedeResolvableMixin


class StockBodega(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Representa el stock actual (saldo) de un producto específico en una bodega.
    Esta tabla se actualiza mediante las operaciones en MovimientoInventario.
    """

    campos_auditables = ["cantidad", "stock_comprometido"]

    requiere_justificacion_auditoria = True

    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name="stock_items")

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="stock_items")

    lote = models.ForeignKey(
        LoteProduccion, on_delete=models.CASCADE, null=True, blank=True, related_name="stock_items"
    )

    cantidad = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)

    stock_comprometido = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0.000,
        verbose_name="Stock Comprometido / Reservado",
        help_text="Cantidad reservada exclusivamente para pedidos comerciales (MTO)",
    )

    class Meta:
        verbose_name = "Stock en Bodega"
        verbose_name_plural = "Stock en Bodegas"
        constraints = [
            models.UniqueConstraint(
                fields=["bodega", "producto"],
                condition=models.Q(lote__isnull=True),
                name="inventory_stockbodega_unique_without_lote",
            ),
            models.UniqueConstraint(
                fields=["bodega", "producto", "lote"],
                condition=models.Q(lote__isnull=False),
                name="inventory_stockbodega_unique_with_lote",
            ),
            models.CheckConstraint(
                check=models.Q(stock_comprometido__gte=0),
                name="chk_stockbodega_comprometido_nonneg",
            ),
        ]

    def __str__(self):
        lote_code = f" (Lote: {self.lote.codigo_lote})" if self.lote else ""
        return f"{self.cantidad} x {self.producto.descripcion} en {self.bodega.nombre}{lote_code}"

    @property
    def stock_disponible(self):
        from decimal import Decimal

        return max(Decimal("0.000"), self.cantidad - (self.stock_comprometido or Decimal("0.000")))

    def get_audit_sede_id(self):
        return self.bodega.sede_id if self.bodega else None


class MovimientoInventario(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Registra cada transacción de inventario. Es la fuente de verdad para la trazabilidad (Kardex).
    """

    campos_auditables = ["cantidad", "saldo_resultante", "editado", "bodega_origen", "bodega_destino"]
    requiere_justificacion_auditoria = True
    TIPO_MOVIMIENTO_CHOICES = [
        ("COMPRA", "Compra de Material"),
        ("PRODUCCION", "Entrada por Producción"),
        ("TRANSFERENCIA", "Transferencia entre Bodegas"),
        ("AJUSTE", "Ajuste de Inventario"),
        ("VENTA", "Salida por Venta"),
        ("DEVOLUCION", "Devolución de Cliente"),
        ("CONSUMO", "Consumo para Producción"),
        ("MERMA", "Merma / Desperdicio"),
    ]

    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES, db_index=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, db_index=True)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True, blank=True)

    # Origen y Destino del movimiento
    bodega_origen = models.ForeignKey(
        Bodega, on_delete=models.PROTECT, related_name="movimientos_salida", null=True, blank=True, db_index=True
    )
    bodega_destino = models.ForeignKey(
        Bodega, on_delete=models.PROTECT, related_name="movimientos_entrada", null=True, blank=True, db_index=True
    )

    cantidad = models.DecimalField(max_digits=12, decimal_places=3)

    # Protocolo 3-fase (Sprint 6): rastrea materiales en tránsito entre bodegas.
    # solicitado → en_transito → completado; 'revertido' cancela la transición.
    # Default 'completado' = compatibilidad con movimientos históricos (1-fase).
    ESTADO_MOVIMIENTO_CHOICES = [
        ("solicitado", "Reservado - Solicitud creada"),
        ("en_transito", "En Tránsito - Entre bodegas"),
        ("completado", "Completado - En bodega destino"),
        ("revertido", "Revertido - Cancelado"),
    ]
    estado_movimiento = models.CharField(
        max_length=20,
        choices=ESTADO_MOVIMIENTO_CHOICES,
        default="completado",
        db_index=True,
        help_text="Fase del movimiento en transición",
    )
    bodega_transicion = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_en_transito",
        help_text="Bodega intermedia si es transferencia entre áreas",
    )

    # Referencia a otros documentos (Orden de Compra, Venta, etc.)
    documento_ref = models.CharField(max_length=100, blank=True, default="", db_index=True)

    # Usuario responsable de la transacción
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # Nuevos campos para bodeguero
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos"
    )
    # COMPRA originada en una recepción F0-001: editarla o borrarla sincroniza el lote de MP.
    materia_prima_lote = models.ForeignKey(
        "gestion.MateriaPrimaLote", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos"
    )
    pais = models.CharField(max_length=100, blank=True, default="")
    calidad = models.CharField(max_length=100, blank=True, default="")
    observaciones = models.CharField(max_length=500, blank=True, default="")

    # Campo denormalizado para facilitar el cálculo del Kardex
    saldo_resultante = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)

    # Campos de auditoría
    editado = models.BooleanField(default=False, help_text="Indica si este movimiento ha sido editado")
    fecha_ultima_edicion = models.DateTimeField(null=True, blank=True, help_text="Fecha de la última edición")

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=0), name="inventory_movimientoinventario_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_resultante__gte=0), name="inventory_movimientoinventario_saldo_positivo"
            ),
        ]
        indexes = [
            models.Index(
                fields=["bodega_origen", "fecha"],
                include=["producto", "cantidad", "saldo_resultante"],
                name="idx_mov_bodega_fecha_incl",
            )
        ]

    def __str__(self):
        return (
            f"{self.get_tipo_movimiento_display()} de "
            f"{self.producto.descripcion} ({self.cantidad}) - "
            f"{self.fecha.strftime('%Y-%m-%d')}"
        )

    def get_audit_sede_id(self):
        if self.bodega_origen:
            return self.bodega_origen.sede_id
        if self.bodega_destino:
            return self.bodega_destino.sede_id
        return None


class AuditoriaMovimiento(models.Model):
    """
    Registra cada modificación realizada a un MovimientoInventario.
    Permite trazabilidad completa de cambios para control y auditoría.
    """

    movimiento = models.ForeignKey(MovimientoInventario, on_delete=models.CASCADE, related_name="auditorias")
    fecha_modificacion = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario_modificador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # Campos modificados
    campo_modificado = models.CharField(max_length=50, help_text="Nombre del campo que fue modificado")
    valor_anterior = models.TextField(help_text="Valor antes de la modificación")
    valor_nuevo = models.TextField(help_text="Valor después de la modificación")
    razon_cambio = models.TextField(blank=True, help_text="Justificación del cambio")

    class Meta:
        ordering = ["-fecha_modificacion"]
        verbose_name = "Auditoría de Movimiento"
        verbose_name_plural = "Auditorías de Movimientos"
        indexes = [
            models.Index(fields=["movimiento", "-fecha_modificacion"]),
        ]

    def __str__(self):
        usuario = self.usuario_modificador.get_full_name() if self.usuario_modificador else "Sistema"
        return (
            f"{self.campo_modificado} modificado por {usuario} - {self.fecha_modificacion.strftime('%Y-%m-%d %H:%M')}"
        )


class HistorialDespacho(models.Model):
    fecha_despacho = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    pedidos: "models.ManyToManyField[Any, Any]" = models.ManyToManyField(
        "gestion.PedidoVenta", through="DetalleHistorialDespachoPedido"
    )
    total_bultos = models.IntegerField()
    total_peso = models.DecimalField(max_digits=12, decimal_places=3)
    observaciones = models.TextField(blank=True, default="")
    items_no_despachados = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Productos del pedido no cubiertos completamente. "
            'Ej: {"Hilo Nylon": {"requerido": 100.0, '
            '"escaneado": 60.0, "faltante": 40.0}}'
        ),
    )

    def __str__(self):
        return f"Despacho {self.id} - {self.fecha_despacho}"


class DetalleHistorialDespachoPedido(models.Model):
    historial = models.ForeignKey(HistorialDespacho, on_delete=models.PROTECT)
    pedido = models.ForeignKey("gestion.PedidoVenta", on_delete=models.PROTECT)
    cantidad_despachada = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)

    class Meta:
        verbose_name = "Detalle de Historial de Despacho del Pedido"

    def __str__(self):
        return f"Despacho {self.id} - {self.historial.fecha_despacho}"


class DetalleHistorialDespacho(models.Model):
    historial = models.ForeignKey(HistorialDespacho, related_name="detalles", on_delete=models.CASCADE)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    peso = models.DecimalField(max_digits=12, decimal_places=3)
    es_devolucion = models.BooleanField(default=False)
    # P1-007: vínculo directo al movimiento VENTA que originó el despacho —
    # la reversión restaura stock vía FK en lugar de buscar por documento_ref
    # (nullable: registros previos a la migración usan el fallback por string)
    movimiento_venta = models.ForeignKey(
        MovimientoInventario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detalles_despacho",
    )
    # F5 (despacho parcial): a qué pedido específico se asignó este lote escaneado,
    # cuando un despacho cubre varios pedidos a la vez. Nullable: registros previos
    # a esta migración, y lotes excedentes que ningún pedido seleccionado requería,
    # quedan sin asignar. Es la fuente de verdad para saber cuánto lleva despachado
    # cada pedido (ver DespachoEstadoService), y para acotar la nota de venta a lo
    # realmente despachado en un evento específico (?historial_id= en download_pdf).
    pedido = models.ForeignKey(
        "gestion.PedidoVenta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detalles_historial_despacho",
    )

    def __str__(self):
        return f"{self.lote} - {self.peso} kg"


class MRPEjecucion(models.Model):
    """
    Una corrida del motor MRP sobre una sede (ADR-012). Es el historial y la
    auditoría del cálculo: quién lo lanzó, cuándo, con qué resultado y qué
    advertencias dejó. Los requerimientos y las sugerencias de la sede son siempre
    los de su última corrida completada.
    """

    ESTADO_COMPLETADA = "completada"
    ESTADO_FALLIDA = "fallida"
    ESTADO_CHOICES = [
        (ESTADO_COMPLETADA, "Completada"),
        (ESTADO_FALLIDA, "Fallida"),
    ]

    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name="ejecuciones_mrp")
    iniciada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ejecuciones_mrp",
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    requerimientos = models.PositiveIntegerField(default=0)
    sugerencias_compra = models.PositiveIntegerField(default=0)
    productos_a_producir = models.PositiveIntegerField(default=0)
    advertencias = models.JSONField(default=list, blank=True)
    mensaje_error = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Ejecución del MRP"
        verbose_name_plural = "Ejecuciones del MRP"
        ordering = ["-inicio", "-id"]
        indexes = [models.Index(fields=["sede", "-inicio"])]

    def __str__(self):
        return f"MRP {self.sede.nombre} {self.inicio:%Y-%m-%d %H:%M} ({self.estado})"


class RequerimientoMaterial(models.Model):
    """
    Material comprado que necesita una orden de producción abierta para completarse:
    lo que falta de su producto de entrada y sus químicos aún no descargados (ADR-012).
    """

    ejecucion = models.ForeignKey(MRPEjecucion, on_delete=models.CASCADE, related_name="requerimientos_material")
    orden_produccion = models.ForeignKey(
        "gestion.OrdenProduccion",
        on_delete=models.CASCADE,
        related_name="requerimientos_mrp",
    )
    producto_requerido = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="requerimientos")
    cantidad_necesaria = models.DecimalField(max_digits=12, decimal_places=3, help_text="Cantidad en kg")
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    fecha_requerida = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Requerimiento de Material"
        verbose_name_plural = "Requerimientos de Materiales"
        indexes = [
            models.Index(fields=["sede", "producto_requerido"]),
        ]

    def __str__(self):
        return (
            f"{self.cantidad_necesaria} kg de {self.producto_requerido.descripcion} para OP {self.orden_produccion_id}"
        )


class OrdenCompraSugerida(models.Model):
    """
    Sugerencia de compra informativa de un material comprado en una sede (ADR-012):
    lo que piden las órdenes abiertas más el stock mínimo, menos lo disponible.
    La compra se gestiona fuera del sistema; la sugerencia no tiene estados.
    """

    ejecucion = models.ForeignKey(MRPEjecucion, on_delete=models.CASCADE, related_name="sugerencias")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    requerido = models.DecimalField(
        max_digits=12, decimal_places=3, help_text="Suma de lo que piden las órdenes abiertas (kg)"
    )
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3)
    stock_disponible = models.DecimalField(
        max_digits=12, decimal_places=3, help_text="Stock de la sede menos lo comprometido (kg)"
    )
    cantidad_sugerida = models.DecimalField(
        max_digits=12, decimal_places=3, help_text="Requerido + stock mínimo − disponible (kg)"
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Orden de Compra Sugerida"
        verbose_name_plural = "Órdenes de Compra Sugeridas"
        constraints = [
            models.UniqueConstraint(fields=["ejecucion", "producto"], name="inventory_sugerencia_unica_por_ejecucion"),
        ]

    def __str__(self):
        return f"Sugerencia Compra: {self.cantidad_sugerida} de {self.producto.descripcion} (Sede: {self.sede.nombre})"
