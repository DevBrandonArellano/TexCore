import logging

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal
import datetime

from gestion.middleware import get_current_user, get_current_ip, get_cascade_justification

logger = logging.getLogger(__name__)


class SedeResolvableMixin:
    """
    Protocolo para que cada modelo declare cómo obtener su sede_id para auditoría.
    Implementar get_audit_sede_id() en cada modelo que use AuditableModelMixin.
    Esto reemplaza la función _get_object_sede_id() con su lógica condicional anidada.
    """

    def get_audit_sede_id(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} debe implementar get_audit_sede_id()"
        )


def _get_object_sede_id(obj):
    """
    Obtiene sede_id del objeto para filtrar logs de entidades eliminadas.
    Prioriza el protocolo SedeResolvableMixin si el objeto lo implementa.

    El fallback con hasattr NO es código muerto candidato a eliminarse (barrido de
    higiene Fase 5.4, 2026-09-02): esta función también la llama el sistema de
    auditoría basado en señales (gestion/signals.py, post_save/pre_delete) para 15
    modelos que NO usan AuditableModelMixin — Sede, Area, Bodega, Maquina,
    CustomUser, ProcessStep, FaseReceta, PagoCliente, LoteProduccion,
    DetallePedido, Batch, Proveedor, HistorialDespacho, RequerimientoMaterial,
    OrdenCompraSugerida — y por lo tanto tampoco implementan (ni deben implementar,
    fuera de alcance de esta fase) el protocolo SedeResolvableMixin. Los 13 modelos
    con AuditableModelMixin sí lo implementan todos y resuelven por Prioridad 1.
    """
    if obj is None:
        return None
    # Prioridad 1: protocolo explícito (los 13 modelos con AuditableModelMixin)
    if isinstance(obj, SedeResolvableMixin):
        try:
            return obj.get_audit_sede_id()
        except Exception as e:
            logger.warning(
                "Error en get_audit_sede_id() para %s pk=%s: %s",
                obj.__class__.__name__, getattr(obj, 'pk', 'N/A'), e
            )
            return None
    # Prioridad 2: fallback por atributos comunes (los 15 modelos auditados por señal)
    try:
        if obj.__class__.__name__ == 'Sede' and hasattr(obj, 'pk') and obj.pk:
            return obj.pk
        if hasattr(obj, 'sede_id') and obj.sede_id is not None:
            return obj.sede_id
        if hasattr(obj, 'sede') and obj.sede and hasattr(obj.sede, 'pk'):
            return obj.sede.pk
        if hasattr(obj, 'fase') and obj.fase and hasattr(obj.fase, 'formula'):
            f = obj.fase.formula
            return getattr(f, 'sede_id', None) if f else None
        if hasattr(obj, 'bodega') and obj.bodega:
            return getattr(obj.bodega, 'sede_id', None)
        if hasattr(obj, 'orden_produccion') and obj.orden_produccion:
            return getattr(obj.orden_produccion, 'sede_id', None)
        if hasattr(obj, 'pedido_venta') and obj.pedido_venta:
            return getattr(obj.pedido_venta, 'sede_id', None)
        if hasattr(obj, 'bodega_origen') and obj.bodega_origen:
            return getattr(obj.bodega_origen, 'sede_id', None)
        if hasattr(obj, 'bodega_destino') and obj.bodega_destino:
            return getattr(obj.bodega_destino, 'sede_id', None)
        if hasattr(obj, 'area') and obj.area:
            return getattr(obj.area, 'sede_id', None)
        if hasattr(obj, 'producto') and obj.producto:
            return getattr(obj.producto, 'sede_id', None)
        if hasattr(obj, 'lote') and obj.lote and hasattr(obj.lote, 'orden_produccion') and obj.lote.orden_produccion:
            return getattr(obj.lote.orden_produccion, 'sede_id', None)
    except Exception as e:
        logger.warning(
            "Error calculando sede_id (fallback) para %s pk=%s: %s",
            obj.__class__.__name__, getattr(obj, 'pk', 'N/A'), e
        )
    return None


class AuditLog(models.Model):
    ACCION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación')
    ]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Relación polimórfica (Generic)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Sede del objeto afectado (denormalizado para filtrar logs de entidades eliminadas)
    object_sede_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    justificacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"

    def __str__(self):
        return f"{self.accion} - {self.content_type} ({self.object_id}) - {self.fecha_hora}"


class AuditableModelMixin(models.Model):
    """
    Mixin para auditar cambios. Guarda estados y emite AuditLogs en save/delete.
    """
    _justificacion_auditoria = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_state = self._get_auditable_data()

    def _get_auditable_data(self):
        data = {}
        campos = getattr(
            self, 'campos_auditables', [
                f.name for f in self._meta.fields if f.name not in (
                    'id', 'fecha_creacion', 'fecha_modificacion')])
        for field in campos:
            try:
                val = getattr(self, field)
                if isinstance(val, models.Model):
                    data[field] = val.pk
                elif isinstance(val, (Decimal, datetime.datetime, datetime.date)):
                    data[field] = str(val)
                else:
                    data[field] = val
            except AttributeError as e:
                logger.warning(
                    "Campo auditable '%s' no encontrado en %s pk=%s: %s",
                    field, self.__class__.__name__, getattr(self, 'pk', 'N/A'), e
                )
        return data

    def clean(self):
        """
        Validaciones de negocio que requieren contexto de auditoría.
        Se llama automáticamente por full_clean() y desde los formularios de Django Admin.
        """
        super().clean()
        is_new = self.pk is None
        requiere_justificacion = getattr(self, 'requiere_justificacion_auditoria', False)

        if not is_new and requiere_justificacion and not self._justificacion_auditoria:
            current_state = self._get_auditable_data()
            changed_auditable = any(
                self._initial_state.get(k) != v
                for k, v in current_state.items()
            )
            if changed_auditable:
                raise ValidationError(
                    "Debe proporcionar una justificación (_justificacion_auditoria) "
                    "para modificar este registro crítico."
                )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        accion = 'CREATE' if is_new else 'UPDATE'

        # Ejecutar validaciones de clean() antes de guardar
        # (los formularios DRF ya llaman full_clean, pero las operaciones directas de ORM no)
        self.full_clean()

        super().save(*args, **kwargs)
        new_state = self._get_auditable_data()

        if is_new:
            changed = True
            valor_anterior = None
            valor_nuevo = new_state
        else:
            changed = False
            valor_anterior = {}
            valor_nuevo = {}
            for k, v in new_state.items():
                if self._initial_state.get(k) != v:
                    changed = True
                    valor_anterior[k] = self._initial_state.get(k)
                    valor_nuevo[k] = v

        if changed:
            user = get_current_user()
            ip = get_current_ip()
            object_sede_id = _get_object_sede_id(self)
            AuditLog.objects.create(
                usuario=user if user and user.is_authenticated else None,
                ip_address=ip,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.pk,
                object_sede_id=object_sede_id,
                accion=accion,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                justificacion=self._justificacion_auditoria
            )

        self._initial_state = new_state
        self._justificacion_auditoria = None

    def delete(self, *args, **kwargs):
        requiere_justificacion = getattr(self, 'requiere_justificacion_auditoria', False)
        justificacion = self._justificacion_auditoria or get_cascade_justification()
        if requiere_justificacion and not justificacion:
            raise ValidationError(
                "Debe proporcionar una justificación (_justificacion_auditoria) para eliminar este registro crítico.")
        if justificacion and not self._justificacion_auditoria:
            self._justificacion_auditoria = justificacion

        user = get_current_user()
        ip = get_current_ip()
        valor_anterior = self._get_auditable_data()

        ct = ContentType.objects.get_for_model(self)
        pk = self.pk
        justificacion = self._justificacion_auditoria

        object_sede_id = _get_object_sede_id(self)
        super().delete(*args, **kwargs)

        AuditLog.objects.create(
            usuario=user if user and user.is_authenticated else None,
            ip_address=ip,
            content_type=ct,
            object_id=pk,
            object_sede_id=object_sede_id,
            accion='DELETE',
            valor_anterior=valor_anterior,
            valor_nuevo=None,
            justificacion=justificacion
        )


class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=100, default='Ubicación no especificada')
    status = models.CharField(max_length=10, choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')], default='activo')

    def __str__(self):
        return self.nombre


class ConfiguracionEmpaqueSede(models.Model):
    """
    Equivalencias de empaque configurables por sede (barrido de higiene Fase
    5.1, 2026-09-02) — antes hardcodeadas en LoteProduccion.clean() y en
    MRPEngine. Requerido explícitamente por CLAUDE.md: "Packaging equivalences
    (e.g. Yarns: 1 baño = 15 fundas = 225 conos; Fabrics: 1 baño = 600m) are
    configurable reference examples per sede, not system-wide hardcoded
    constants." Esta primera versión cubre la equivalencia de hilos (baño→
    fundas→conos), que es la única hardcodeada hoy en el código; la de telas
    (baño→metros) queda para cuando exista un caso de uso real que la lea.

    Sedes sin fila propia (aún no configuradas) usan los valores de
    referencia originales como default — ver `LoteProduccion.clean()` y
    `MRPEngine._get_conos_por_bano()`, que no fallan si no existe.
    """
    sede = models.OneToOneField(Sede, on_delete=models.CASCADE, related_name='configuracion_empaque')
    fundas_por_bano = models.PositiveIntegerField(
        default=15, help_text='Equivalencia de referencia: 1 baño = N fundas')
    conos_por_funda = models.PositiveIntegerField(
        default=15, help_text='Equivalencia de referencia: 1 funda = N conos')

    class Meta:
        verbose_name = 'Configuración de Empaque por Sede'
        verbose_name_plural = 'Configuraciones de Empaque por Sede'

    def __str__(self):
        return (f'Empaque {self.sede.nombre}: 1 baño = {self.fundas_por_bano} fundas '
                f'= {self.conos_por_bano} conos')

    @property
    def conos_por_bano(self):
        return self.fundas_por_bano * self.conos_por_funda


class Area(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='areas')

    class Meta:
        unique_together = ('nombre', 'sede')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'


class CustomUser(AbstractUser):
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    superior = models.ManyToManyField('self', symmetrical=False, related_name='inferiors_set', blank=True)
    bodegas_asignadas = models.ManyToManyField('Bodega', blank=True, related_name='usuarios_asignados')

    def __str__(self):
        return self.username
