import datetime
import logging
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from gestion.middleware import get_cascade_justification, get_current_ip, get_current_user

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


# Relaciones cuya sede define la del objeto, en orden de prioridad. La primera relación
# presente decide, aunque su sede_id sea None.
_RELACIONES_CON_SEDE = (
    'bodega', 'orden_produccion', 'pedido_venta', 'bodega_origen', 'bodega_destino', 'area', 'producto',
)


def _sede_id_por_atributos(obj):
    """Resuelve la sede de un modelo sin SedeResolvableMixin a partir de sus atributos."""
    if obj.__class__.__name__ == 'Sede' and getattr(obj, 'pk', None):
        return obj.pk
    if getattr(obj, 'sede_id', None) is not None:
        return obj.sede_id
    sede = getattr(obj, 'sede', None)
    if sede and hasattr(sede, 'pk'):
        return sede.pk
    fase = getattr(obj, 'fase', None)
    if fase and hasattr(fase, 'formula'):
        return getattr(fase.formula, 'sede_id', None) if fase.formula else None
    for relacion in _RELACIONES_CON_SEDE:
        relacionado = getattr(obj, relacion, None)
        if relacionado:
            return getattr(relacionado, 'sede_id', None)
    lote = getattr(obj, 'lote', None)
    orden = getattr(lote, 'orden_produccion', None) if lote else None
    if orden:
        return getattr(orden, 'sede_id', None)
    return None


def _get_object_sede_id(obj):
    """
    Obtiene sede_id del objeto para filtrar logs de entidades eliminadas.
    Prioriza el protocolo SedeResolvableMixin si el objeto lo implementa.

    El fallback con hasattr NO es código muerto candidato a eliminarse (barrido de
    higiene Fase 5.4, 2026-09-02): esta función también la llama el sistema de
    auditoría basado en señales (gestion/signals.py, post_save/pre_delete) para 15
    modelos que NO usan AuditableModelMixin — Sede, Area, Bodega, Maquina,
    CustomUser, ProcessStep, FaseReceta, PagoCliente, LoteProduccion,
    DetallePedido, Proveedor, HistorialDespacho, RequerimientoMaterial,
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
                obj.__class__.__name__, getattr(obj, 'pk', 'N/A'), e,
                exc_info=True,
            )
            return None
    # Prioridad 2: fallback por atributos comunes (los 14 modelos auditados por señal)
    try:
        return _sede_id_por_atributos(obj)
    except Exception as e:
        logger.warning(
            "Error calculando sede_id (fallback) para %s pk=%s: %s",
            obj.__class__.__name__, getattr(obj, 'pk', 'N/A'), e,
            exc_info=True,
        )
    return None


class RegistroAuditoriaInmutable(Exception):
    """Intento de modificar o borrar un registro de auditoría (TEX-09 CA-2)."""


class AuditLogQuerySet(models.QuerySet):
    """Sin update()/delete() masivos: la auditoría solo admite altas. Las acciones
    referenciales de la base (SET_NULL del usuario) usan el _base_manager de Django."""

    def update(self, **kwargs):
        raise RegistroAuditoriaInmutable('Los registros de auditoría no se modifican.')

    def delete(self):
        raise RegistroAuditoriaInmutable('Los registros de auditoría no se borran.')


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
    # Sin db_index propio: idx_audit_objsede_fecha empieza por esta columna.
    object_sede_id = models.PositiveIntegerField(null=True, blank=True)
    # Sede del usuario al momento del cambio (denormalizada, la fija save()). El listado
    # filtra `usuario_sede_id OR object_sede_id` sin unir con el usuario: con la unión, el
    # COUNT de la paginación era el 75 % de la CPU de SQL Server (prueba de carga 2026-10-06).
    usuario_sede_id = models.PositiveIntegerField(null=True, blank=True)

    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    justificacion = models.TextField(blank=True, default='')

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        indexes = [
            # Uno por cada rama del OR del listado por sede, con la fecha para el rango
            # de 30 días y el orden: SQL Server los combina (index union) en el COUNT.
            models.Index(fields=['object_sede_id', '-fecha_hora'], name='idx_audit_objsede_fecha'),
            models.Index(fields=['usuario_sede_id', '-fecha_hora'], name='idx_audit_usrsede_fecha'),
        ]

    def __str__(self):
        return f"{self.accion} - {self.content_type} ({self.object_id}) - {self.fecha_hora}"

    def save(self, *args, **kwargs):
        # TEX-09 CA-2: inmutable en el modelo, no solo por no exponer un endpoint.
        if not self._state.adding:
            raise RegistroAuditoriaInmutable('Los registros de auditoría no se modifican.')
        if self.usuario_sede_id is None and self.usuario_id is not None:
            self.usuario_sede_id = self.usuario.sede_id
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RegistroAuditoriaInmutable('Los registros de auditoría no se borran.')


class AuditableModelMixin(models.Model):
    """
    Mixin para auditar cambios. Guarda estados y emite AuditLogs en save/delete.
    """

    _justificacion_auditoria: str | None = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_state = self._get_auditable_data()

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
                justificacion=self._justificacion_auditoria or '',
            )

        self._initial_state = new_state
        self._justificacion_auditoria = None

    def _get_auditable_data(self):
        data = {}
        campos = getattr(
            self, 'campos_auditables', [
                f.name for f in self._meta.fields if f.name not in (
                    'id', 'fecha_creacion', 'fecha_modificacion')])
        # Campos diferidos (.only()/.defer(), p. ej. el colector de borrado de Django al
        # revisar PROTECT/CASCADE): leerlos dispara refresh_from_db, que vuelve a
        # instanciar el modelo y recursa sin fin. No se auditan en esa carga parcial.
        diferidos = self.get_deferred_fields()
        for field in campos:
            if field in diferidos or f'{field}_id' in diferidos:
                continue
            # FK: se lee la columna <fk>_id, no el objeto. getattr(self, fk) consulta
            # la base, y en __init__ la caché de select_related aún no está poblada
            # -> una consulta por fila leída (N+1 en todo listado; RNF-03).
            try:
                modelo_field = self._meta.get_field(field)
            except FieldDoesNotExist:
                modelo_field = None
            if modelo_field is not None and modelo_field.many_to_one:
                data[field] = getattr(self, modelo_field.attname)
                continue
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
            justificacion=justificacion or '',
        )


class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=100, default='Ubicación no especificada')
    status = models.CharField(max_length=10, choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')], default='activo')

    def __str__(self):
        return self.nombre


class ConfiguracionEmpaqueSede(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Equivalencias de empaque configurables por sede (TEX-43). CLAUDE.md: "Packaging
    equivalences (e.g. Yarns: 1 baño = 15 fundas = 225 conos) are configurable
    reference examples per sede, not system-wide hardcoded constants." Cubre la
    equivalencia de hilos (baño → fundas → conos); la de telas (baño → metros) queda
    para cuando exista un caso de uso que la lea.

    Sin fila no hay equivalencia (TEX-43 CA-3): LoteProduccion.clean() rechaza la
    conversión con un aviso y el MRP omite la sede, en vez de aplicar una constante
    del sistema. La configura el Administrador de Sede (la suya) o el de Sistemas;
    es un dato maestro, así que modificarla exige justificación (TEX-10).
    """
    requiere_justificacion_auditoria = True

    sede = models.OneToOneField(Sede, on_delete=models.CASCADE, related_name='configuracion_empaque')
    fundas_por_bano = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text='1 baño = N fundas')
    conos_por_funda = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text='1 funda = N conos')

    class Meta:
        verbose_name = 'Configuración de Empaque por Sede'
        verbose_name_plural = 'Configuraciones de Empaque por Sede'

    def __str__(self):
        return (f'Empaque {self.sede.nombre}: 1 baño = {self.fundas_por_bano} fundas '
                f'= {self.conos_por_bano} conos')

    def get_audit_sede_id(self):
        return self.sede_id

    @property
    def conos_por_bano(self):
        return self.fundas_por_bano * self.conos_por_funda

    @classmethod
    def para_sede(cls, sede):
        """La configuración de la sede, o None si aún no la tiene (o no hay sede)."""
        return cls.objects.filter(sede=sede).first() if sede else None

    @staticmethod
    def mensaje_sin_configuracion(sede):
        if sede is None:
            return ('No se puede determinar la sede del lote para aplicar las equivalencias '
                    'de empaque.')
        return (f'La sede {sede.nombre} no tiene configuradas las equivalencias de empaque: '
                'el Administrador de Sede debe registrarlas.')


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
    bodegas_asignadas: "models.ManyToManyField[Any, Any]" = models.ManyToManyField(
        'Bodega', blank=True, related_name='usuarios_asignados'
    )

    def __str__(self):
        return self.username
