import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import CustomUser, EventoEtiqueta, LoteProduccion, OrdenProduccion
from gestion.permissions import (
    IsAdminSistemasOrSede,
    IsJefeAreaOrAdmin,
    IsLoteEditorRole,
    IsRegistroLoteRole,
    IsTrazabilidadCostosRole,
    filtrar_lotes_por_sede,
    filtrar_por_sede,
    ve_todas_las_sedes,
)
from gestion.serializers import (
    LoteProduccionSerializer,
    RegistrarLoteProduccionSerializer,
)
from gestion.services.evento_etiqueta_service import EventoEtiquetaService
from gestion.services.lote_stock_adjustment import LoteStockAdjustmentService
from gestion.services.registro_lote import RegistroLoteService
from gestion.services.trazabilidad import TrazabilidadService
from gestion.utils import PrintingService

from ._common import parse_int_param

logger = logging.getLogger('gestion.views')


class LotesProduccionPagination(PageNumberPagination):
    """Siempre activa: el historial de lotes crece con la operación y una lista sin
    tope degradó el endpoint bajo carga. El frontend pide bloques de 4 páginas de
    30 (page_size=120) y los muestra de 30 en 30 (usePaginacionIncremental)."""
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 120


_FILTROS_ENTEROS = (
    ('operario', 'operario_id'),
    ('sede_id', 'orden_produccion__sede_id'),
    ('orden_produccion', 'orden_produccion_id'),
)
_FILTROS_TEXTO = (
    ('turno', 'turno__icontains'),
    ('codigo_lote', 'codigo_lote__icontains'),
    ('clasificacion_calidad', 'clasificacion_calidad'),
    ('presentacion', 'presentacion__icontains'),
)


def _parse_fecha(params, nombre):
    crudo = params.get(nombre)
    if not crudo:
        return None
    fecha = parse_date(crudo)
    if not fecha:
        raise ValidationError({nombre: 'Formato de fecha inválido (usar YYYY-MM-DD).'})
    return fecha


def _filtrar_por_rango_de_fechas(queryset, params):
    """Filtra por fecha de cierre del lote (hora_final) validando formato y orden del rango."""
    fecha_desde = _parse_fecha(params, 'fecha_desde')
    fecha_hasta = _parse_fecha(params, 'fecha_hasta')
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValidationError({'fecha_desde': 'fecha_desde no puede ser posterior a fecha_hasta.'})
    if fecha_desde:
        queryset = queryset.filter(hora_final__date__gte=fecha_desde)
    if fecha_hasta:
        queryset = queryset.filter(hora_final__date__lte=fecha_hasta)
    return queryset


class LoteProduccionViewSet(viewsets.ModelViewSet):
    # Sin DELETE: un lote se rechaza (`rechazar`), que revierte su stock y lo audita.
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    serializer_class = LoteProduccionSerializer
    pagination_class = LotesProduccionPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['hora_final', 'hora_inicio', 'peso_neto_producido', 'codigo_lote']
    ordering = ['-hora_final']

    @action(detail=False, methods=['get'], url_path='resumen-hoy')
    def resumen_hoy(self, request):
        """GET /lotes-produccion/resumen-hoy/ — bultos, peso total y promedio de los
        lotes terminados hoy (fecha local), con el mismo alcance que el listado."""
        resumen = self.get_queryset().filter(hora_final__date=timezone.localdate()).aggregate(
            bultos=Count('id'), peso_total_kg=Sum('peso_neto_producido'),
        )
        bultos = resumen['bultos']
        peso_total = resumen['peso_total_kg'] or Decimal('0')
        promedio = (peso_total / bultos).quantize(Decimal('0.001')) if bultos else Decimal('0')
        return Response({'bultos': bultos, 'peso_total_kg': peso_total, 'peso_promedio_kg': promedio})

    @action(detail=True, methods=['get'], url_path='obtener-costo')
    def obtener_costo(self, request, pk=None):
        """GET /api/lotes-produccion/{id}/obtener-costo/ — F0-002.

        Calcula (o recalcula) el desglose de costos del lote: MP + químicos
        + operario + máquina. El vendedor ve el margen antes de fijar precio.
        """
        from gestion.serializers import CostoLoteProduccionSerializer
        from gestion.services.costeo_service import CostoLoteService

        lote = self.get_object()
        costo = CostoLoteService.calcular_costo(lote, request.user)
        return Response(CostoLoteProduccionSerializer(costo).data)

    def get_queryset(self):
        user = self.request.user
        queryset = LoteProduccion.objects.select_related(
            'orden_produccion', 'orden_produccion__producto_entrada',
            'orden_produccion__producto_salida',
            'orden_produccion__sede', 'maquina', 'operario'
        ).all()
        # OWASP A01: también en retrieve y en las acciones de detalle (get_object → 404).
        queryset = filtrar_lotes_por_sede(queryset, user)

        # Security: Jefe de Área only sees lots from their area
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(orden_produccion__area=user.area)
            else:
                return LoteProduccion.objects.none()

        # Los parámetros enteros se validan en este orden (operario lo usa el dashboard "mis entradas").
        params = self.request.query_params
        for param, campo in _FILTROS_ENTEROS:
            valor = parse_int_param(params.get(param), param)
            if valor:
                queryset = queryset.filter(**{campo: valor})

        # F3: buscador dedicado — fecha, turno, código de lote, máquina, calidad, presentación.
        queryset = _filtrar_por_rango_de_fechas(queryset, params)

        maquina_id = parse_int_param(params.get('maquina'), 'maquina')
        if maquina_id:
            queryset = queryset.filter(maquina_id=maquina_id)

        for param, campo in _FILTROS_TEXTO:
            valor = params.get(param)
            if valor:
                queryset = queryset.filter(**{campo: valor})

        return queryset

    def _validar_duenio(self, lote):
        """El operario solo edita o rechaza los lotes que registró."""
        user = self.request.user
        grupos = set(user.groups.values_list('name', flat=True))
        if not user.is_superuser and grupos == {'operario'} and lote.operario_id != user.id:
            raise PermissionDenied('Solo puede modificar los lotes que registró.')

    @transaction.atomic
    def perform_update(self, serializer):
        lote = self.get_object()
        self._validar_duenio(lote)
        old_peso_neto = lote.peso_neto_producido

        # Save the updated lote
        updated_lote = serializer.save()

        LoteStockAdjustmentService.ajustar_por_cambio_peso(
            updated_lote, old_peso_neto, updated_lote.peso_neto_producido, self.request.user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'resumen_hoy', 'generate_zpl', 'generate_pdf_label', 'genealogia',
                           'etiquetas']:
            return [IsAuthenticated()]
        if self.action == 'reetiquetar':
            # F4: reetiquetar cambia datos del lote y anula la etiqueta previa — solo supervisor.
            return [IsAuthenticated(), IsJefeAreaOrAdmin()]
        if self.action in ('update', 'partial_update', 'rechazar'):
            # Editar el peso ajusta stock y rechazar borra el lote revirtiendo su stock:
            # el operario solo sobre sus lotes (ver _validar_duenio); sin empaquetado.
            return [IsAuthenticated(), IsLoteEditorRole()]
        if self.action == 'obtener_costo':
            # F0-002 expone costos de materia prima y químicos.
            return [IsAuthenticated(), IsTrazabilidadCostosRole()]
        if self.request.user.groups.filter(
            name__in=[
                'jefe_area',
                'jefe_planta',
                'admin_sistemas',
                'admin_sede',
                'empaquetado',
                'operario']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    @action(detail=True, methods=['get'])
    def genealogia(self, request, pk=None):
        """
        Retorna la genealogía y trazabilidad inversa del lote.
        Muestra la máquina, operario, fórmula de color, y químicos consumidos.
        """
        lote = self.get_object()
        orden = lote.orden_produccion

        data = {
            "lote_codigo": lote.codigo_lote,
            "producto": (lote.orden_produccion.producto_salida.descripcion
                         if lote.orden_produccion and lote.orden_produccion.producto_salida else None),
            "peso_neto": lote.peso_neto_producido,
            "peso_merma": lote.peso_merma,
            "tipo_merma": lote.get_tipo_merma_display() if lote.tipo_merma else None,
            "calidad": lote.get_clasificacion_calidad_display(),
            "operario": lote.operario.username if lote.operario else None,
            "maquina": lote.maquina.nombre if lote.maquina else None,
            "fechas": {
                "inicio": lote.hora_inicio,
                "final": lote.hora_final},
            "orden_produccion": {
                "codigo": orden.codigo if orden else None,
                "formula_color": (
                    orden.formula_color.nombre_color
                    if orden and orden.formula_color else None
                ),
            },
            "quimicos_consumidos": []}

        if orden:
            # Obtener descargas de químicos de esta OP
            from gestion.models import DescargaQuimicoOP
            descargas = DescargaQuimicoOP.objects.filter(
                orden_produccion=orden,
                estado='aplicada'
            ).select_related('producto', 'fase__proceso')

            # El consumo de la OP es global, proporcionamos el listado de químicos
            # consumidos para producir todo el batch.
            for d in descargas:
                data["quimicos_consumidos"].append({
                    "quimico": d.producto.descripcion,
                    "cantidad_total_op_kg": d.cantidad_real_kg or d.cantidad_calculada_kg,
                    "fase": d.fase.proceso.nombre if d.fase else 'N/A'
                })

        logger.info(
            "Genealogía de lote consultada",
            extra={'sd': {
                'entity': 'LoteProduccion',
                'action': 'READ_GENEALOGY',
                'lote_codigo': lote.codigo_lote,
                'user': request.user.username
            }}
        )

        return Response(data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def rechazar(self, request, pk=None):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        from gestion.services.merma_stock import MermaStockService

        lote = self.get_object()
        self._validar_duenio(lote)
        orden = lote.orden_produccion

        justificacion = request.data.get('justificacion', '')
        if not justificacion:
            return Response(
                {'success': False, 'error': {'message': 'Justificación requerida para rechazar un lote.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Revertir consumo de mezcla (si aplica)
        if lote.consumos_detalle.exists():
            ConsumoMezclaService.revertir(lote, request.user, justificacion)

        # Revertir merma vendible (si aplica)
        MermaStockService.revertir(lote, request.user, justificacion)

        # 1-2. Reversión manual de stock (salida, materia prima, químicos)
        try:
            LoteStockAdjustmentService.revertir_por_rechazo(lote, request.user)
        except ValidationError as e:
            detail = e.detail[0] if isinstance(e.detail, list) else e.detail
            return Response({"error": str(detail)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Mark Lote as rejected or delete
        from gestion.middleware import clear_cascade_justification, set_cascade_justification

        try:
            set_cascade_justification(f"Reversion por rechazo de lote {lote.codigo_lote}")
            # ProduccionSalida.lote_generado es PROTECT (auditoría del motor MES
            # unificado, ver gestion/services/registro_lote.py) — el registro se
            # crea automáticamente para todo lote, incluso los de este flujo
            # clásico. Sin borrar el registro MES espejo primero, lote.delete()
            # siempre falla con ProtectedError (409) al rechazar cualquier lote.
            lote.salidas_mes.all().delete()
            lote.delete()
        finally:
            clear_cascade_justification()

        # 4. Update order status
        total_producido = orden.lotes.aggregate(Sum('peso_neto_producido'))[
            'peso_neto_producido__sum'] or Decimal('0.00')
        requerido = orden.peso_neto_requerido
        if requerido is not None and total_producido < requerido and orden.estado == 'finalizada':
            orden.estado = 'en_proceso'
            orden.save()

        return Response({"message": "Lote rechazado y movimientos revertidos correctamente."},
                        status=status.HTTP_200_OK)

    @staticmethod
    def _build_zpl_payload(lote):
        """Construye el payload base para el microservicio de impresión a partir del lote."""
        orden = lote.orden_produccion

        empresa = orden.sede.nombre if orden and orden.sede else 'Sede Principal'

        if hasattr(orden, 'producto_descripcion'):
            producto_desc = orden.producto_descripcion
        else:
            producto = (orden.producto_salida or orden.producto_entrada) if orden else None
            producto_desc = producto.descripcion if producto else 'N/A'

        peso_neto = float(lote.peso_neto_producido)
        tara = float(lote.tara) if lote.tara else 0.0
        peso_bruto = float(lote.peso_bruto) if lote.peso_bruto else 0.0
        cantidad_metros = float(lote.cantidad_metros) if lote.cantidad_metros else None

        producto_op = (orden.producto_salida or orden.producto_entrada) if orden else None
        unidad = producto_op.unidad_medida if producto_op else 'kg'
        lote_codigo = lote.codigo_lote
        qr_data = f"{settings.TRAZABILIDAD_BASE_URL}/{lote_codigo}"

        return {
            "empresa": empresa,
            "producto_desc": producto_desc,
            "lote_codigo": lote_codigo,
            "peso_neto": peso_neto,
            "tara": tara,
            "peso_bruto": peso_bruto,
            "cantidad_metros": cantidad_metros,
            "unidad": unidad,
            "qr_data": qr_data,
            # F6: lotes con varias piezas físicas (ej. 12 rollos por caja) —
            # cada pieza necesita su propia etiqueta numerada. unidades_empaque
            # default es 1 (un solo bulto), así que la mayoría de lotes no ven
            # ningún cambio de comportamiento.
            "piezas_totales": lote.unidades_empaque or 1,
        }

    @staticmethod
    def _sanitize_zpl_field(value):
        """
        Elimina '^' (prefijo de comando de formato ZPL) y '~' (prefijo de
        comando de control ZPL) de texto libre editable (empresa, producto_desc)
        antes de interpolarlo en el f-string ZPL de _build_zpl_fallback, que no
        tiene ningún escapado propio. Sin esto, un valor de catálogo con '^'
        o '~' corrompe el stream que interpreta la impresora Zebra.
        """
        return value.replace('^', '').replace('~', '') if isinstance(value, str) else value

    @classmethod
    def _build_zpl_fallback(cls, data, sello=None):
        """ZPL local simple, usado si el microservicio de impresión no responde."""
        empresa = cls._sanitize_zpl_field(data['empresa'])
        producto_desc = cls._sanitize_zpl_field(data['producto_desc'])
        lote_codigo = cls._sanitize_zpl_field(data['lote_codigo'])
        metros_text = f"Metros: {data['cantidad_metros']}" if data['cantidad_metros'] else ""
        sello_text = f"^FO50,320^ADN,18,10^FD{sello}^FS" if sello else ""
        piezas_totales = data.get('piezas_totales') or 1
        pieza_text = (
            f"^FO50,300^ADN,18,10^FDPIEZA {data.get('pieza')}/{piezas_totales}^FS"
            if piezas_totales > 1 else ""
        )
        return f"""
^XA
^PW800
^LL400
^FO50,50^ADN,36,20^FD{empresa}^FS
^FO50,100^ADN,18,10^FD{producto_desc} (FALLBACK)^FS
^FO50,150^ADN,18,10^FDLote/Pieza: {lote_codigo}^FS
^FO50,200^ADN,24,14^FDBruto: {data['peso_bruto']}kg  Tara: {data['tara']}kg^FS
^FO50,230^ADN,36,20^FDNeto: {data['peso_neto']} {data['unidad']} {metros_text}^FS
^FO50,280^BCN,80,Y,N,N^FD{lote_codigo}^FS
{sello_text}
{pieza_text}
^XZ
        """.strip()

    @classmethod
    def _generar_zpl_completo(cls, data, sello=None):
        """
        Genera el ZPL final a imprimir para un lote: si `piezas_totales` > 1
        (el lote representa varias piezas físicas — ej. 12 rollos por caja,
        LoteProduccion.unidades_empaque), concatena una etiqueta por pieza,
        cada una con "PIEZA i/N", todas con el mismo lote_codigo/QR de
        trazabilidad (es el mismo lote físico, solo se reparte en bultos).

        Cada bloque ZPL (^XA..^XZ) es una etiqueta física independiente para
        la impresora Zebra — concatenarlos imprime N etiquetas separadas sin
        requerir ningún cambio en el frontend (printLabel ya reenvía el
        string completo tal cual). Si el lote es de una sola pieza, produce
        exactamente el mismo ZPL de siempre.

        Retorna (zpl, uso_fallback).
        """
        total_piezas = data.get('piezas_totales') or 1
        if total_piezas <= 1:
            zpl = PrintingService.generate_zpl_label(data)
            if zpl:
                return zpl, False
            return cls._build_zpl_fallback(data, sello=sello), True

        bloques = []
        uso_fallback = False
        for pieza in range(1, total_piezas + 1):
            payload_pieza = {**data, 'pieza': pieza}
            zpl = PrintingService.generate_zpl_label(payload_pieza)
            if zpl:
                bloques.append(zpl)
            else:
                uso_fallback = True
                bloques.append(cls._build_zpl_fallback(payload_pieza, sello=sello))
        return "\n".join(bloques), uso_fallback

    @action(detail=True, methods=['get'])
    def generate_zpl(self, request, pk=None):
        lote = self.get_object()
        data = self._build_zpl_payload(lote)

        zpl, uso_fallback = self._generar_zpl_completo(data)

        if uso_fallback:
            return Response({"zpl": zpl,
                             "warning": "Servicio de impresión no disponible, usando fallback local."},
                            status=status.HTTP_200_OK)
        return Response({"zpl": zpl}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='generate-pdf-label')
    def generate_pdf_label(self, request, pk=None):
        """
        GET /lotes-produccion/{id}/generate-pdf-label/ — F5: etiqueta en PDF,
        fallback universal para impresoras de etiquetas sin ZPL nativo (no Zebra).

        Acepta ?tipo_evento=REIMPRESION|REETIQUETADO&version=N (opcionales):
        el fallback a Zebra Browser Print del frontend (`printLabel`) también se
        usa tras reimprimir/reetiquetar, y sin esto siempre regeneraba una
        etiqueta "ORIGINAL" plana en PDF — perdiendo el sello de gobernanza que
        el ZPL ya lleva. Sin estos params, se comporta como antes (ORIGINAL).
        """
        lote = self.get_object()
        data = self._build_zpl_payload(lote)

        tipo_evento = request.query_params.get('tipo_evento')
        if tipo_evento in ('REIMPRESION', 'REETIQUETADO'):
            data['tipo_evento'] = tipo_evento
            data['version'] = parse_int_param(request.query_params.get('version'), 'version') or 1
            data['usuario'] = request.user.username

        pdf_bytes = PrintingService.generate_label_pdf(data)
        if not pdf_bytes:
            # Bajo/informativo: a diferencia de generate_zpl, no hay fallback
            # local para PDF — WeasyPrint vive deliberadamente aislado en el
            # microservicio para no bloquear el hilo de Gunicorn (ver
            # printing_service/README.md#Arquitectura). El frontend ya
            # absorbe esta caída con su propio fallback a portapapeles
            # (frontend/src/lib/printing.ts:printLabel). 'code' distingue
            # este 503 de otros para monitoreo/alertas.
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'PRINTING_SERVICE_UNAVAILABLE',
                        'message': 'Servicio de impresión no disponible para generar PDF.',
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{lote.codigo_lote}.pdf"'
        return response

    @action(detail=True, methods=['get'])
    def etiquetas(self, request, pk=None):
        """GET /lotes-produccion/{id}/etiquetas/ — historial de eventos de etiqueta del lote."""
        lote = self.get_object()
        eventos = lote.etiquetas.select_related('usuario', 'anula_a').order_by('secuencia')
        data = [
            {
                "id": e.id,
                "tipo_evento": e.tipo_evento,
                "secuencia": e.secuencia,
                "version": e.version,
                "motivo": e.motivo,
                "detalle_motivo": e.detalle_motivo,
                "usuario": e.usuario.username if e.usuario else None,
                "timestamp": e.timestamp,
                "formato": e.formato,
                "anulada": e.anulada,
                "anula_a": e.anula_a_id,
            }
            for e in eventos
        ]
        return Response(data)

    @action(detail=True, methods=['post'])
    def reimprimir(self, request, pk=None):
        """
        POST /lotes-produccion/{id}/reimprimir/ — reimpresión idéntica gobernada.
        Body: {motivo (requerido), detalle_motivo?, formato?}.
        No cambia datos del lote ni la version vigente; solo registra el evento y
        reimprime la etiqueta con los datos actuales.
        """
        lote = self.get_object()
        motivo = request.data.get('motivo', '')
        if not motivo:
            return Response(
                {'success': False, 'error': {'message': 'Motivo requerido para reimprimir una etiqueta.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        motivos_validos = dict(EventoEtiqueta.MOTIVO_CHOICES)
        if motivo not in motivos_validos:
            return Response(
                {'success': False, 'error': {
                    'message': f"motivo inválido. Debe ser uno de: {', '.join(motivos_validos)}."}},
                status=status.HTTP_400_BAD_REQUEST
            )
        detalle_motivo = request.data.get('detalle_motivo', '')
        formato = request.data.get('formato', 'ZPL')

        evento = EventoEtiquetaService.registrar_reimpresion(
            lote, request.user, motivo=motivo, detalle_motivo=detalle_motivo, formato=formato
        )

        data = self._build_zpl_payload(lote)
        data['motivo'] = motivo
        data['tipo_evento'] = evento.tipo_evento
        data['version'] = evento.version
        data['usuario'] = request.user.username
        data['reimpreso'] = True

        sello = f"REIMPRESION v{evento.version}"
        zpl, _ = self._generar_zpl_completo(data, sello=sello)

        logger.info(
            "Reimpresión de etiqueta",
            extra={'sd': {
                'entity': 'EventoEtiqueta',
                'action': 'REIMPRESION',
                'lote_codigo': lote.codigo_lote,
                'version': evento.version,
                'secuencia': evento.secuencia,
                'motivo': motivo,
                'user': request.user.username,
            }}
        )

        return Response({
            "zpl": zpl,
            "evento": {
                "id": evento.id,
                "tipo_evento": evento.tipo_evento,
                "secuencia": evento.secuencia,
                "version": evento.version,
            },
        }, status=status.HTTP_200_OK)

    CAMBIOS_REETIQUETADO_PERMITIDOS = {
        'peso_bruto', 'tara', 'peso_neto_producido', 'clasificacion_calidad',
        'presentacion', 'cantidad_metros', 'unidades_empaque',
    }

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reetiquetar(self, request, pk=None):
        """
        POST /lotes-produccion/{id}/reetiquetar/ — reetiquetado con cambio de datos.
        Body: {cambios: {...}, motivo (requerido), detalle_motivo?, formato?}.
        Requiere rol supervisor (jefe_area/jefe_planta/admin). El codigo_lote y el QR
        de trazabilidad NUNCA cambian; la etiqueta previa queda anulada y se emite
        una nueva version. Si cambia peso_neto_producido, ajusta stock (misma lógica
        que perform_update).
        """
        lote = self.get_object()
        supervisor_user = request.user
        supervisor_roles = {'jefe_area', 'jefe_planta', 'admin_sistemas', 'admin_sede'}

        def es_supervisor(u):
            # El RBAC del proyecto se basa en grupos de Django (CustomUser no tiene
            # atributo `role`). Consistente con IsJefeAreaOrAdmin y get_permissions.
            return bool(u) and (u.is_superuser or u.groups.filter(name__in=supervisor_roles).exists())

        if not es_supervisor(request.user):
            sup_username = request.data.get('supervisor_username')
            sup_password = request.data.get('supervisor_password')
            if not sup_username or not sup_password:
                return Response(
                    {'success': False, 'error': {
                        'message': 'El reetiquetado requiere autenticación de un Jefe de Área o Supervisor.'}},
                    status=status.HTTP_403_FORBIDDEN
                )
            authenticated_supervisor = authenticate(request, username=sup_username, password=sup_password)
            if not authenticated_supervisor:
                return Response(
                    {'success': False, 'error': {'message': 'Credenciales de supervisor inválidas.'}},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            if not es_supervisor(authenticated_supervisor):
                return Response(
                    {'success': False, 'error': {
                        'message': 'El usuario ingresado no tiene rol de Jefe de Área o Supervisor.'}},
                    status=status.HTTP_403_FORBIDDEN
                )
            supervisor_user = authenticated_supervisor

        motivo = request.data.get('motivo', '')
        if not motivo:
            return Response(
                {'success': False, 'error': {'message': 'Motivo requerido para reetiquetar.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        motivos_validos = dict(EventoEtiqueta.MOTIVO_CHOICES)
        if motivo not in motivos_validos:
            return Response(
                {'success': False, 'error': {
                    'message': f"motivo inválido. Debe ser uno de: {', '.join(motivos_validos)}."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        cambios = request.data.get('cambios') or {}
        if not cambios:
            return Response(
                {'success': False, 'error': {'message': 'Debe indicar al menos un cambio de datos.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        campos_invalidos = set(cambios.keys()) - self.CAMBIOS_REETIQUETADO_PERMITIDOS
        if campos_invalidos:
            return Response(
                {'success': False, 'error': {
                    'message': f"Campos no permitidos en reetiquetado: {', '.join(sorted(campos_invalidos))}"}},
                status=status.HTTP_400_BAD_REQUEST
            )

        detalle_motivo = request.data.get('detalle_motivo', '')
        formato = request.data.get('formato', 'ZPL')

        old_peso_neto = lote.peso_neto_producido
        serializer = self.get_serializer(lote, data=cambios, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_lote = serializer.save()
        LoteStockAdjustmentService.ajustar_por_cambio_peso(
            updated_lote, old_peso_neto, updated_lote.peso_neto_producido, request.user)

        evento = EventoEtiquetaService.registrar_reetiquetado(
            updated_lote, supervisor_user, motivo=motivo, detalle_motivo=detalle_motivo, formato=formato
        )

        data = self._build_zpl_payload(updated_lote)
        data['motivo'] = motivo
        data['tipo_evento'] = evento.tipo_evento
        data['version'] = evento.version
        data['usuario'] = supervisor_user.username
        data['reimpreso'] = False

        sello = f"REETIQUETADO v{evento.version}"
        zpl, _ = self._generar_zpl_completo(data, sello=sello)

        logger.info(
            "Reetiquetado de lote",
            extra={'sd': {
                'entity': 'EventoEtiqueta',
                'action': 'REETIQUETADO',
                'lote_codigo': updated_lote.codigo_lote,
                'version': evento.version,
                'secuencia': evento.secuencia,
                'motivo': motivo,
                'cambios': list(cambios.keys()),
                'user': request.user.username,
            }}
        )

        return Response({
            "zpl": zpl,
            "lote": LoteProduccionSerializer(updated_lote).data,
            "evento": {
                "id": evento.id,
                "tipo_evento": evento.tipo_evento,
                "secuencia": evento.secuencia,
                "version": evento.version,
                "anula_a": evento.anula_a_id,
            },
        }, status=status.HTTP_200_OK)


class TrazabilidadPorCodigoLoteView(APIView):
    """
    GET /api/trazabilidad-lote/{codigo_lote}/ — destino del QR impreso en la
    etiqueta (ver TRAZABILIDAD_BASE_URL / LoteProduccionViewSet._build_zpl_payload).
    Cualquier usuario autenticado puede consultar, sin restricción de rol, pero
    solo lotes de su sede (misma regla multi-tenant que OrdenProduccionViewSet).

    `codigo_lote` no es único a nivel de BD (unique_together con
    orden_produccion), así que ante una colisión entre órdenes distintas se
    resuelve con el lote más reciente por hora_final.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, codigo_lote):
        lote = (
            filtrar_lotes_por_sede(LoteProduccion.objects.all(), request.user)
            .filter(codigo_lote=codigo_lote)
            .select_related('orden_produccion')
            .order_by('-hora_final')
            .first()
        )
        if lote is None or lote.orden_produccion_id is None:
            return Response({'detail': 'Lote no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TrazabilidadService.construir(lote.orden_produccion))


class RegistrarLoteProduccionView(APIView):
    """
    API View to register a production lot and handle all related inventory movements.
    """
    permission_classes = [IsRegistroLoteRole]

    def post(self, request, orden_id, *args, **kwargs):
        user = request.user
        # OWASP A01: una orden de otra sede responde 404, igual que en OrdenProduccionViewSet.
        orden = get_object_or_404(filtrar_por_sede(OrdenProduccion.objects.all(), user), id=orden_id)

        # Jefe de Área: solo su área. Operario: su área o la orden que tiene asignada.
        if (user.groups.filter(name__in=['jefe_area', 'operario']).exists()
                and not ve_todas_las_sedes(user)):
            es_de_su_area = bool(user.area_id) and user.area_id == orden.area_id
            es_su_orden = (orden.operario_asignado_id == user.id
                           and user.groups.filter(name='operario').exists())
            if not (es_de_su_area or es_su_orden):
                return Response({"detail": "No tienes permiso para registrar lotes en esta área."},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = RegistrarLoteProduccionSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Fallo al validar lote de producción",
                extra={
                    "sd": {
                        "entity": "LoteProduccion",
                        "field": "serializer",
                        "reason": str(
                            serializer.errors)}})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lote_data = serializer.validated_data
        completar_orden = lote_data.pop('completar_orden', False)

        # RegistroLoteService toma las bodegas de la máquina: una máquina de otra
        # sede movería stock ajeno. El operario acreditado también es de la sede.
        maquina = lote_data.get('maquina')
        if maquina is not None and not (maquina.area_id and maquina.area.sede_id == orden.sede_id):
            return Response({'maquina': ['La máquina no pertenece a la sede de la orden.']},
                            status=status.HTTP_400_BAD_REQUEST)
        operario_id = lote_data.get('operario')
        if operario_id and not CustomUser.objects.filter(pk=operario_id, sede_id=orden.sede_id).exists():
            return Response({'operario': ['El operario no pertenece a la sede de la orden.']},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            lote = RegistroLoteService.registrar_lote(
                orden=orden,
                lote_data=lote_data,
                user=user,
                completar_orden=completar_orden
            )
            return Response(LoteProduccionSerializer(lote).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.warning(
                'Validation error registering lote for orden %s: %s',
                orden.id,
                e.detail,
            )
            return Response({"detail": str(e.detail) if isinstance(e.detail, (list, dict))
                            else e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            msg = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
            logger.warning(
                'Django validation error registering lote for orden %s: %s',
                orden.id,
                msg,
            )
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            logger.exception("IntegrityError registering lote for orden %s: %s",
                orden.id,
                e)
            return Response({"detail": "Código de lote duplicado. Intenta nuevamente."},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(
                'Unexpected error registering lote: %s',
                e,
            )
            return Response({"detail": "Error al registrar el lote. Contacta al administrador."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
