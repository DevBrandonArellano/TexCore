from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0054_merge_20260505_1955'),
    ]

    operations = [
        # ----------------------------------------------------------
        # PedidoVenta — lectura muy intensiva en dashboards y KPIs
        # ----------------------------------------------------------
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(fields=['estado'], name='pv_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(fields=['esta_pagado'], name='pv_pagado_idx'),
        ),
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(fields=['fecha_vencimiento'], name='pv_vencimiento_idx'),
        ),
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(fields=['fecha_pedido'], name='pv_fecha_pedido_idx'),
        ),
        # Compuesto principal — ClienteManager subquery (cartera vencida)
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(
                fields=['cliente', 'anulado', 'esta_pagado', 'fecha_vencimiento'],
                name='pv_cartera_vencida_idx',
            ),
        ),
        # Compuesto — saldo general por cliente
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(
                fields=['cliente', 'anulado'],
                name='pv_cliente_anulado_idx',
            ),
        ),
        # Compuesto — listados por sede
        migrations.AddIndex(
            model_name='pedidoventa',
            index=models.Index(
                fields=['sede', 'anulado'],
                name='pv_sede_anulado_idx',
            ),
        ),

        # ----------------------------------------------------------
        # Cliente — poca escritura, alta lectura en listados
        # ----------------------------------------------------------
        migrations.AddIndex(
            model_name='cliente',
            index=models.Index(fields=['is_active'], name='cli_activo_idx'),
        ),
        migrations.AddIndex(
            model_name='cliente',
            index=models.Index(fields=['sede', 'is_active'], name='cli_sede_activo_idx'),
        ),

        # ----------------------------------------------------------
        # LoteProduccion — KPIs de producción (escritura moderada)
        # Solo hora_inicio; evitar índices compuestos en tabla de movimiento
        # ----------------------------------------------------------
        migrations.AddIndex(
            model_name='loteproduccion',
            index=models.Index(fields=['hora_inicio'], name='lote_hora_inicio_idx'),
        ),
    ]
