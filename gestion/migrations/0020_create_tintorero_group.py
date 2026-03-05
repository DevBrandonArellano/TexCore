"""
Migration 0020: Crea el grupo 'tintorero' y le asigna permisos de
view, add y change sobre FormulaColor y DetalleFormula.
NO incluye permiso de delete por restriccion de negocio.
Incluye view sobre Producto para el autocompletado de quimicos.
"""
from django.db import migrations


def create_tintorero_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    group, _ = Group.objects.get_or_create(name='tintorero')

    # Helper function to get or create content type (safe for migrations)
    def get_ct(app_label, model):
        try:
            return ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            # Fallback for tests or inconsistent environments
            return ContentType.objects.create(app_label=app_label, model=model)

    # Permisos sobre FormulaColor: view, add, change (sin delete)
    fc_ct = get_ct('gestion', 'formulacolor')
    fc_perms = Permission.objects.filter(
        content_type=fc_ct,
        codename__in=['view_formulacolor', 'add_formulacolor', 'change_formulacolor']
    )
    group.permissions.add(*fc_perms)

    # Permisos sobre DetalleFormula: view, add, change (sin delete)
    df_ct = get_ct('gestion', 'detalleformula')
    df_perms = Permission.objects.filter(
        content_type=df_ct,
        codename__in=['view_detalleformula', 'add_detalleformula', 'change_detalleformula']
    )
    group.permissions.add(*df_perms)

    # Permiso de lectura sobre Producto (para buscar quimicos en el autocompletado)
    prod_ct = get_ct('gestion', 'producto')
    view_prod = Permission.objects.filter(content_type=prod_ct, codename='view_producto')
    group.permissions.add(*view_prod)


def remove_tintorero_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='tintorero').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0019_formulas_quimicas_v2'),
    ]

    operations = [
        migrations.RunPython(create_tintorero_group, remove_tintorero_group),
    ]
