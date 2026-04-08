"""
Migration: Añadir CHECK constraint para peso_neto_requerido > 0 en OrdenProduccion.

COBIT APO12 — Gestión del Riesgo: previene órdenes de producción con peso cero
o negativo que pasarían las validaciones de capa de aplicación pero corromperían
los cálculos de planificación y eficiencia.

Requerimiento: G4.8 (Sprint 4 — Gobierno y Operaciones)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0049_auditlog_content_object_index'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='ordenproduccion',
            constraint=models.CheckConstraint(
                condition=models.Q(peso_neto_requerido__gt=0),
                name='gestion_ordenproduccion_peso_neto_positivo',
            ),
        ),
    ]
