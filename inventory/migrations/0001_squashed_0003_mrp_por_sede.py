"""Consolidación de `inventory` 0001 a 0003 en una sola migración.

Reemplaza a 0001_initial, 0002_cadenas_vacias_sin_null (DJ001: '' en vez de NULL) y
0003_mrp_por_sede (ADR-012).

Las bases que ya aplicaron las tres originales ven esta migración como aplicada gracias a
`replaces`; **no se debe quitar** esa lista, o Django la volvería a ejecutar. Las bases nuevas la
ejecutan una sola vez, sobre tablas vacías, así que los dos `RunPython` conservan su lógica pero no
tienen filas que tocar.

Depende de `gestion.0003_squashed_0009`: el MRP por sede necesita el índice de auditoría por sedes
(`gestion.0008`) que esa migración ya incluye.
"""

import django.db.migrations.operations.special
import django.db.models.deletion
import gestion.models.core
from django.conf import settings
from django.db import migrations, models

# ── de 0002_cadenas_vacias_sin_null ─────────────────────────────────────────────
CAMPOS = {
    "historialdespacho": ("observaciones",),
    "movimientoinventario": ("calidad", "documento_ref", "observaciones", "pais"),
    "ordencomprasugerida": ("observaciones",),
}


def nulos_a_vacio(apps, schema_editor):
    for modelo, campos in CAMPOS.items():
        Modelo = apps.get_model("inventory", modelo)
        for campo in campos:
            Modelo.objects.filter(**{f"{campo}__isnull": True}).update(**{campo: ""})


# ── de 0003_mrp_por_sede ────────────────────────────────────────────────────────
def borrar_resultados_calculados(apps, schema_editor):
    """Los requerimientos y las sugerencias son datos calculados: se regeneran con el MRP."""
    apps.get_model("inventory", "RequerimientoMaterial").objects.all().delete()
    apps.get_model("inventory", "OrdenCompraSugerida").objects.all().delete()


class Migration(migrations.Migration):
    replaces = [
        ("inventory", "0001_initial"),
        ("inventory", "0002_cadenas_vacias_sin_null"),
        ("inventory", "0003_mrp_por_sede"),
    ]

    dependencies = [
        ("gestion", "0001_initial"),
        ("gestion", "0003_squashed_0009_paromaquina_origen"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DetalleHistorialDespachoPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad_despachada", models.DecimalField(decimal_places=3, default=0.0, max_digits=12)),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="gestion.pedidoventa")),
            ],
            options={
                "verbose_name": "Detalle de Historial de Despacho del Pedido",
            },
        ),
        migrations.CreateModel(
            name="HistorialDespacho",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_despacho", models.DateTimeField(auto_now_add=True)),
                ("total_bultos", models.IntegerField()),
                ("total_peso", models.DecimalField(decimal_places=3, max_digits=12)),
                ("observaciones", models.TextField(blank=True, null=True)),
                (
                    "items_no_despachados",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Productos del pedido no cubiertos completamente. Ej: {"Hilo Nylon": {"requerido": 100.0, "escaneado": 60.0, "faltante": 40.0}}',
                    ),
                ),
                (
                    "pedidos",
                    models.ManyToManyField(
                        through="inventory.DetalleHistorialDespachoPedido", to="gestion.pedidoventa"
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="detallehistorialdespachopedido",
            name="historial",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="inventory.historialdespacho"),
        ),
        migrations.CreateModel(
            name="MovimientoInventario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "tipo_movimiento",
                    models.CharField(
                        choices=[
                            ("COMPRA", "Compra de Material"),
                            ("PRODUCCION", "Entrada por Producción"),
                            ("TRANSFERENCIA", "Transferencia entre Bodegas"),
                            ("AJUSTE", "Ajuste de Inventario"),
                            ("VENTA", "Salida por Venta"),
                            ("DEVOLUCION", "Devolución de Cliente"),
                            ("CONSUMO", "Consumo para Producción"),
                            ("MERMA", "Merma / Desperdicio"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("cantidad", models.DecimalField(decimal_places=3, max_digits=12)),
                (
                    "estado_movimiento",
                    models.CharField(
                        choices=[
                            ("solicitado", "Reservado - Solicitud creada"),
                            ("en_transito", "En Tránsito - Entre bodegas"),
                            ("completado", "Completado - En bodega destino"),
                            ("revertido", "Revertido - Cancelado"),
                        ],
                        db_index=True,
                        default="completado",
                        help_text="Fase del movimiento en transición",
                        max_length=20,
                    ),
                ),
                ("documento_ref", models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ("pais", models.CharField(blank=True, max_length=100, null=True)),
                ("calidad", models.CharField(blank=True, max_length=100, null=True)),
                ("observaciones", models.CharField(blank=True, max_length=500, null=True)),
                ("saldo_resultante", models.DecimalField(decimal_places=3, default=0.0, max_digits=12)),
                ("editado", models.BooleanField(default=False, help_text="Indica si este movimiento ha sido editado")),
                (
                    "fecha_ultima_edicion",
                    models.DateTimeField(blank=True, help_text="Fecha de la última edición", null=True),
                ),
                (
                    "bodega_destino",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos_entrada",
                        to="gestion.bodega",
                    ),
                ),
                (
                    "bodega_origen",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos_salida",
                        to="gestion.bodega",
                    ),
                ),
                (
                    "bodega_transicion",
                    models.ForeignKey(
                        blank=True,
                        help_text="Bodega intermedia si es transferencia entre áreas",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movimientos_en_transito",
                        to="gestion.bodega",
                    ),
                ),
                (
                    "lote",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="gestion.loteproduccion"
                    ),
                ),
                (
                    "materia_prima_lote",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movimientos",
                        to="gestion.materiaprimalote",
                    ),
                ),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="gestion.producto")),
                (
                    "proveedor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movimientos",
                        to="gestion.proveedor",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name": "Movimiento de Inventario",
                "verbose_name_plural": "Movimientos de Inventario",
                "ordering": ["-fecha"],
            },
            bases=(gestion.models.core.SedeResolvableMixin, models.Model),
        ),
        migrations.CreateModel(
            name="DetalleHistorialDespacho",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("peso", models.DecimalField(decimal_places=3, max_digits=12)),
                ("es_devolucion", models.BooleanField(default=False)),
                (
                    "lote",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL, to="gestion.loteproduccion"
                    ),
                ),
                (
                    "pedido",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="detalles_historial_despacho",
                        to="gestion.pedidoventa",
                    ),
                ),
                (
                    "producto",
                    models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="gestion.producto"),
                ),
                (
                    "historial",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detalles",
                        to="inventory.historialdespacho",
                    ),
                ),
                (
                    "movimiento_venta",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="detalles_despacho",
                        to="inventory.movimientoinventario",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AuditoriaMovimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_modificacion", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("campo_modificado", models.CharField(help_text="Nombre del campo que fue modificado", max_length=50)),
                ("valor_anterior", models.TextField(help_text="Valor antes de la modificación")),
                ("valor_nuevo", models.TextField(help_text="Valor después de la modificación")),
                ("razon_cambio", models.TextField(blank=True, help_text="Justificación del cambio")),
                (
                    "usuario_modificador",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "movimiento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auditorias",
                        to="inventory.movimientoinventario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Auditoría de Movimiento",
                "verbose_name_plural": "Auditorías de Movimientos",
                "ordering": ["-fecha_modificacion"],
            },
        ),
        migrations.CreateModel(
            name="OrdenCompraSugerida",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "cantidad_sugerida",
                    models.DecimalField(
                        decimal_places=3,
                        help_text="Cantidad sugerida a comprar (Requerimiento - Stock Actual)",
                        max_digits=12,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("APROBADA", "Convertida en OC"),
                            ("RECHAZADA", "Rechazada"),
                        ],
                        default="PENDIENTE",
                        max_length=20,
                    ),
                ),
                ("fecha_generacion", models.DateTimeField(auto_now_add=True)),
                ("observaciones", models.TextField(blank=True, null=True)),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="gestion.producto")),
                ("sede", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="gestion.sede")),
            ],
            options={
                "verbose_name": "Orden de Compra Sugerida",
                "verbose_name_plural": "Órdenes de Compra Sugeridas",
            },
        ),
        migrations.CreateModel(
            name="RequerimientoMaterial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad_necesaria", models.DecimalField(decimal_places=3, max_digits=12)),
                (
                    "origen_tipo",
                    models.CharField(
                        choices=[("PEDIDO", "Pedido de Venta"), ("OP", "Orden de Producción")], max_length=20
                    ),
                ),
                (
                    "origen_id",
                    models.PositiveIntegerField(help_text="ID del Pedido o de la OP que genera este requerimiento"),
                ),
                ("fecha_requerida", models.DateField(blank=True, null=True)),
                ("fecha_calculo", models.DateTimeField(auto_now_add=True)),
                (
                    "producto_requerido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requerimientos",
                        to="gestion.producto",
                    ),
                ),
                ("sede", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="gestion.sede")),
            ],
            options={
                "verbose_name": "Requerimiento de Material",
                "verbose_name_plural": "Requerimientos de Materiales",
            },
        ),
        migrations.CreateModel(
            name="StockBodega",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.DecimalField(decimal_places=3, default=0.0, max_digits=12)),
                (
                    "stock_comprometido",
                    models.DecimalField(
                        decimal_places=3,
                        default=0.0,
                        help_text="Cantidad reservada exclusivamente para pedidos comerciales (MTO)",
                        max_digits=12,
                        verbose_name="Stock Comprometido / Reservado",
                    ),
                ),
                (
                    "bodega",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="stock_items", to="gestion.bodega"
                    ),
                ),
                (
                    "lote",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_items",
                        to="gestion.loteproduccion",
                    ),
                ),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="stock_items", to="gestion.producto"
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock en Bodega",
                "verbose_name_plural": "Stock en Bodegas",
            },
            bases=(gestion.models.core.SedeResolvableMixin, models.Model),
        ),
        migrations.AddIndex(
            model_name="movimientoinventario",
            index=models.Index(
                fields=["bodega_origen", "fecha"],
                include=("producto", "cantidad", "saldo_resultante"),
                name="idx_mov_bodega_fecha_incl",
            ),
        ),
        migrations.AddConstraint(
            model_name="movimientoinventario",
            constraint=models.CheckConstraint(
                condition=models.Q(("cantidad__gte", 0)), name="inventory_movimientoinventario_cantidad_positiva"
            ),
        ),
        migrations.AddConstraint(
            model_name="movimientoinventario",
            constraint=models.CheckConstraint(
                condition=models.Q(("saldo_resultante__gte", 0)), name="inventory_movimientoinventario_saldo_positivo"
            ),
        ),
        migrations.AddIndex(
            model_name="auditoriamovimiento",
            index=models.Index(fields=["movimiento", "-fecha_modificacion"], name="inventory_a_movimie_1bd024_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="ordencomprasugerida",
            unique_together={("producto", "sede", "estado")},
        ),
        migrations.AddIndex(
            model_name="requerimientomaterial",
            index=models.Index(fields=["sede", "producto_requerido"], name="inventory_r_sede_id_ab1ed1_idx"),
        ),
        migrations.AddConstraint(
            model_name="stockbodega",
            constraint=models.UniqueConstraint(
                condition=models.Q(("lote__isnull", True)),
                fields=("bodega", "producto"),
                name="inventory_stockbodega_unique_without_lote",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockbodega",
            constraint=models.UniqueConstraint(
                condition=models.Q(("lote__isnull", False)),
                fields=("bodega", "producto", "lote"),
                name="inventory_stockbodega_unique_with_lote",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockbodega",
            constraint=models.CheckConstraint(
                condition=models.Q(("stock_comprometido__gte", 0)), name="chk_stockbodega_comprometido_nonneg"
            ),
        ),
        migrations.RunPython(
            code=nulos_a_vacio,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="historialdespacho",
            name="observaciones",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="calidad",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="documento_ref",
            field=models.CharField(blank=True, db_index=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="observaciones",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="pais",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="ordencomprasugerida",
            name="observaciones",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(
            code=borrar_resultados_calculados,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.CreateModel(
            name="MRPEjecucion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("inicio", models.DateTimeField()),
                ("fin", models.DateTimeField()),
                (
                    "estado",
                    models.CharField(choices=[("completada", "Completada"), ("fallida", "Fallida")], max_length=20),
                ),
                ("requerimientos", models.PositiveIntegerField(default=0)),
                ("sugerencias_compra", models.PositiveIntegerField(default=0)),
                ("productos_a_producir", models.PositiveIntegerField(default=0)),
                ("advertencias", models.JSONField(blank=True, default=list)),
                ("mensaje_error", models.TextField(blank=True, default="")),
                (
                    "iniciada_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ejecuciones_mrp",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "sede",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="ejecuciones_mrp", to="gestion.sede"
                    ),
                ),
            ],
            options={
                "verbose_name": "Ejecución del MRP",
                "verbose_name_plural": "Ejecuciones del MRP",
                "ordering": ["-inicio", "-id"],
                "indexes": [models.Index(fields=["sede", "-inicio"], name="inventory_m_sede_id_0c8697_idx")],
            },
        ),
        migrations.AlterUniqueTogether(
            name="ordencomprasugerida",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="ordencomprasugerida",
            name="estado",
        ),
        migrations.RemoveField(
            model_name="ordencomprasugerida",
            name="observaciones",
        ),
        migrations.AddField(
            model_name="ordencomprasugerida",
            name="ejecucion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="sugerencias", to="inventory.mrpejecucion"
            ),
        ),
        migrations.AddField(
            model_name="ordencomprasugerida",
            name="requerido",
            field=models.DecimalField(
                decimal_places=3, default=0, help_text="Suma de lo que piden las órdenes abiertas (kg)", max_digits=12
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="ordencomprasugerida",
            name="stock_minimo",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="ordencomprasugerida",
            name="stock_disponible",
            field=models.DecimalField(
                decimal_places=3, default=0, help_text="Stock de la sede menos lo comprometido (kg)", max_digits=12
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="ordencomprasugerida",
            name="cantidad_sugerida",
            field=models.DecimalField(
                decimal_places=3, help_text="Requerido + stock mínimo − disponible (kg)", max_digits=12
            ),
        ),
        migrations.AddConstraint(
            model_name="ordencomprasugerida",
            constraint=models.UniqueConstraint(
                fields=("ejecucion", "producto"), name="inventory_sugerencia_unica_por_ejecucion"
            ),
        ),
        migrations.RemoveField(
            model_name="requerimientomaterial",
            name="origen_tipo",
        ),
        migrations.RemoveField(
            model_name="requerimientomaterial",
            name="origen_id",
        ),
        migrations.RemoveField(
            model_name="requerimientomaterial",
            name="fecha_calculo",
        ),
        migrations.AddField(
            model_name="requerimientomaterial",
            name="ejecucion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="requerimientos_material",
                to="inventory.mrpejecucion",
            ),
        ),
        migrations.AddField(
            model_name="requerimientomaterial",
            name="orden_produccion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="requerimientos_mrp",
                to="gestion.ordenproduccion",
            ),
        ),
        migrations.AlterField(
            model_name="requerimientomaterial",
            name="cantidad_necesaria",
            field=models.DecimalField(decimal_places=3, help_text="Cantidad en kg", max_digits=12),
        ),
    ]
