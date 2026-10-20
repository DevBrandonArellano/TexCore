"""Consolidación de `gestion` 0003 a 0009 en una sola migración.

Reemplaza a (en este orden):
- 0003_cadenas_vacias_sin_null: DJ001, los CharField/TextField opcionales usan '' en vez de NULL.
- 0004_auditlog_usuario_sede: sede del usuario en cada registro de auditoría.
- 0005_rellenar_auditlog_usuario_sede: relleno de esa sede en los registros anteriores.
- 0006_configuracion_empaque_explicita: TEX-43 CA-3, equivalencias de empaque sin valor del sistema.
- 0007_metros_tela_cuatro_decimales: `cantidad_metros` a DECIMAL(12, 4).
- 0008_auditlog_indice_fecha_sedes: índice `idx_audit_fecha_sedes` (ADR-010).
- 0009_paromaquina_origen: `ParoMaquina.origen` (ADR-013).

Las bases que ya aplicaron las siete originales (producción, desarrollo) ven esta migración como
aplicada gracias a `replaces`; **no se debe quitar** esa lista, o Django la volvería a ejecutar. Las
bases nuevas la ejecutan una sola vez, sobre tablas vacías: por eso los tres `RunPython` conservan su
lógica (la cubren sus pruebas) pero ya no necesitan el modo no atómico de la 0005, y los dos índices
que la 0004 creaba para retirarlos en la 0008 no se crean.

`gestion.0001` y `gestion.0002` no se fusionan aquí: la 0002 depende de `token_blacklist`, que a su vez
depende del modelo de usuario que crea la 0001; unirlas formaría una dependencia circular.
"""

import django.core.validators
import django.db.migrations.operations.special
from django.db import migrations, models
from django.db.models import OuterRef, Subquery

# ── de 0003_cadenas_vacias_sin_null ─────────────────────────────────────────────
CAMPOS = {
    "auditlog": ("justificacion",),
    "corridaproduccion": ("observaciones",),
    "descargaquimicoop": ("justificacion",),
    "detalleformula": ("notas",),
    "eventoetiqueta": ("motivo",),
    "fasereceta": ("observaciones",),
    "formulacolor": ("description", "observaciones"),
    "lineaproduccion": ("descripcion",),
    "loteproduccion": ("presentacion", "tipo_merma"),
    "operacionproduccion": ("motivo_reversion", "observaciones"),
    "ordenproduccion": ("observaciones",),
    "ordenproduccionsubproceso": ("motivo_rechazo", "observaciones"),
    "pagocliente": ("comprobante", "notas"),
    "pedidoventa": ("motivo_anulacion",),
    "procesotintoreria": ("descripcion",),
    "processstep": ("description",),
    "producto": ("calidad", "pais_origen", "presentacion"),
    "transferenciainterarea": ("observaciones",),
    "transformacionproducto": ("observaciones",),
}


def nulos_a_vacio(apps, schema_editor):
    for modelo, campos in CAMPOS.items():
        Modelo = apps.get_model("gestion", modelo)
        for campo in campos:
            Modelo.objects.filter(**{f"{campo}__isnull": True}).update(**{campo: ""})


# ── de 0005_rellenar_auditlog_usuario_sede ──────────────────────────────────────
TAMANO_LOTE = 10_000


def rellenar_usuario_sede(apps, schema_editor, tamano_lote=TAMANO_LOTE):
    """Rellena AuditLog.usuario_sede_id de los registros anteriores con la sede actual del usuario.

    Va por bloques de ids y solo toca filas con usuario y sin sede, así que se puede repetir.
    """
    AuditLog = apps.get_model("gestion", "AuditLog")
    CustomUser = apps.get_model("gestion", "CustomUser")
    # _base_manager: el manager del modelo bloquea update() (TEX-09); el relleno es la
    # única escritura permitida sobre filas existentes y ocurre una sola vez.
    pendientes = AuditLog._base_manager.filter(usuario_id__isnull=False, usuario_sede_id__isnull=True)
    sede_del_usuario = Subquery(CustomUser.objects.filter(pk=OuterRef("usuario_id")).values("sede_id")[:1])

    desde = 0
    while True:
        ids = list(pendientes.filter(pk__gt=desde).order_by("pk").values_list("pk", flat=True)[:tamano_lote])
        if not ids:
            return
        AuditLog._base_manager.filter(pk__in=ids).update(usuario_sede_id=sede_del_usuario)
        desde = ids[-1]


# ── de 0006_configuracion_empaque_explicita ─────────────────────────────────────
FUNDAS_POR_BANO = 15
CONOS_POR_FUNDA = 15


def crear_configuracion_existente(apps, schema_editor):
    Sede = apps.get_model("gestion", "Sede")
    ConfiguracionEmpaqueSede = apps.get_model("gestion", "ConfiguracionEmpaqueSede")
    ConfiguracionEmpaqueSede.objects.bulk_create(
        [
            ConfiguracionEmpaqueSede(sede=sede, fundas_por_bano=FUNDAS_POR_BANO, conos_por_funda=CONOS_POR_FUNDA)
            for sede in Sede.objects.filter(configuracion_empaque__isnull=True)
        ]
    )


class Migration(migrations.Migration):
    replaces = [
        ("gestion", "0003_cadenas_vacias_sin_null"),
        ("gestion", "0004_auditlog_usuario_sede"),
        ("gestion", "0005_rellenar_auditlog_usuario_sede"),
        ("gestion", "0006_configuracion_empaque_explicita"),
        ("gestion", "0007_metros_tela_cuatro_decimales"),
        ("gestion", "0008_auditlog_indice_fecha_sedes"),
        ("gestion", "0009_paromaquina_origen"),
    ]

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("gestion", "0002_fix_token_blacklist_mssql"),
    ]

    operations = [
        migrations.RunPython(
            code=nulos_a_vacio,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="justificacion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="corridaproduccion",
            name="observaciones",
            field=models.TextField(blank=True, default="", verbose_name="Observaciones"),
        ),
        migrations.AlterField(
            model_name="descargaquimicoop",
            name="justificacion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="detalleformula",
            name="notas",
            field=models.TextField(
                blank=True, default="", help_text="Observaciones tecnicas del insumo en esta formula"
            ),
        ),
        migrations.AlterField(
            model_name="eventoetiqueta",
            name="motivo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DANIADA", "Etiqueta Dañada"),
                    ("PERDIDA", "Etiqueta Perdida"),
                    ("ATASCO", "Atasco de Impresora"),
                    ("CORRECCION_PESO", "Corrección de Peso"),
                    ("RECLASIFICACION", "Reclasificación de Calidad"),
                    ("REEMPAQUE", "Reempaque"),
                    ("OTRO", "Otro"),
                ],
                default="",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="fasereceta",
            name="observaciones",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="formulacolor",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="formulacolor",
            name="observaciones",
            field=models.CharField(
                blank=True, default="", help_text="Observaciones generales sobre la formula", max_length=500
            ),
        ),
        migrations.AlterField(
            model_name="lineaproduccion",
            name="descripcion",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="loteproduccion",
            name="presentacion",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="loteproduccion",
            name="tipo_merma",
            field=models.CharField(
                blank=True,
                choices=[
                    ("maquina", "Falla Técnica / Máquina"),
                    ("material", "Calidad de Hilo / Material"),
                    ("setup", "Arranque / Setup"),
                    ("corte", "Corte / Empalme"),
                    ("otro", "Otro"),
                ],
                default="",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="operacionproduccion",
            name="motivo_reversion",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Justificación obligatoria en caso de anulación o reversión de inventarios.",
                verbose_name="Motivo de Reversión",
            ),
        ),
        migrations.AlterField(
            model_name="operacionproduccion",
            name="observaciones",
            field=models.TextField(blank=True, default="", verbose_name="Observaciones"),
        ),
        migrations.AlterField(
            model_name="ordenproduccion",
            name="observaciones",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="ordenproduccionsubproceso",
            name="motivo_rechazo",
            field=models.TextField(blank=True, default="", help_text="Si fue rechazado, incluir el motivo"),
        ),
        migrations.AlterField(
            model_name="ordenproduccionsubproceso",
            name="observaciones",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="pagocliente",
            name="comprobante",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="pagocliente",
            name="notas",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="pedidoventa",
            name="motivo_anulacion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="procesotintoreria",
            name="descripcion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="processstep",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="producto",
            name="calidad",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="producto",
            name="pais_origen",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="producto",
            name="presentacion",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="transferenciainterarea",
            name="observaciones",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="transformacionproducto",
            name="observaciones",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="usuario_sede_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="object_sede_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(
            code=rellenar_usuario_sede,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.RunPython(
            code=crear_configuracion_existente,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="configuracionempaquesede",
            name="conos_por_funda",
            field=models.PositiveIntegerField(
                help_text="1 funda = N conos", validators=[django.core.validators.MinValueValidator(1)]
            ),
        ),
        migrations.AlterField(
            model_name="configuracionempaquesede",
            name="fundas_por_bano",
            field=models.PositiveIntegerField(
                help_text="1 baño = N fundas", validators=[django.core.validators.MinValueValidator(1)]
            ),
        ),
        migrations.AlterField(
            model_name="loteproduccion",
            name="cantidad_metros",
            field=models.DecimalField(
                blank=True, decimal_places=4, help_text="Metros reenrollados para telas", max_digits=12, null=True
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(
                fields=["-fecha_hora"], include=("usuario_sede_id", "object_sede_id"), name="idx_audit_fecha_sedes"
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="fecha_hora",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="paromaquina",
            name="origen",
            field=models.CharField(
                choices=[("manual", "Registro manual"), ("estado", "Cambio de estado de la máquina")],
                default="manual",
                help_text="`estado`: lo abrió el sistema al cambiar el estado de la máquina y se cierra solo al volver a operativa. `manual`: lo registró una persona y nunca se modifica.",
                max_length=10,
            ),
        ),
    ]
