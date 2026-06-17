from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
import logging
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from gestion.permissions import (
    IsAdminSistemasOrSede, IsVendedorOrEjecutivoOrAdmin
)
from gestion.services.pago_reversion import PagoReversionService
from django.utils import timezone
from gestion.models import (
    Cliente, PagoCliente, PedidoVenta, DetallePedido
)
from gestion.utils import PrintingService, PaymentReconciler
from gestion.serializers import (
    ClienteSerializer, ClienteListSerializer, PedidoVentaSerializer, DetallePedidoSerializer, PagoClienteSerializer,
    AnulacionPedidoSerializer, ModificacionPedidoSerializer,
)
from django.db import transaction

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ClienteListSerializer
        return ClienteSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Cliente.objects.all()

        # Solo prefecheamos si es detalle o si realmente necesitamos ver pedidos anidados
        if self.action != 'list':
            queryset = queryset.prefetch_related(
                'pedidoventa_set',
                'pedidoventa_set__detalles',
                'pedidoventa_set__detalles__producto'
            )

        # Filtro opcional por vendedor (solo para roles con visión gerencial/sistemas)
        vendedor_id = self.request.query_params.get('vendedor_id')
        vendedor_username = self.request.query_params.get('vendedor_username')
        if (vendedor_id or vendedor_username) and (
            user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()
        ):
            if vendedor_id:
                try:
                    queryset = queryset.filter(vendedor_asignado_id=int(vendedor_id))
                except (TypeError, ValueError):
                    pass
            elif vendedor_username:
                queryset = queryset.filter(vendedor_asignado__username=vendedor_username)

        # Multi-tenancy: Superusers, system admins and executives can see all sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(sede=user.sede)

        # If user is a salesman, only show their assigned clients
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(vendedor_asignado=user)

        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

        return queryset.all()

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}

        # Auto-asignar vendedor si el usuario pertenece al grupo 'vendedor'
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            save_kwargs['vendedor_asignado'] = user

        # Auto-asignar sede del usuario si no se proporcionó una explícitamente
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            save_kwargs['sede'] = user.sede

        serializer.save(**save_kwargs)

    def perform_destroy(self, instance):
        from gestion.middleware import set_cascade_justification, clear_cascade_justification
        justificacion = self.request.query_params.get('_justificacion_auditoria') or \
            self.request.headers.get('X-Justificacion-Auditoria') or \
            self.request.data.get('_justificacion_auditoria')
        if not justificacion:
            justificacion = "Eliminación desde panel de administración"
        instance._justificacion_auditoria = justificacion
        set_cascade_justification(justificacion)
        try:
            instance.delete()
        finally:
            clear_cascade_justification()


class PagoClienteViewSet(viewsets.ModelViewSet):
    serializer_class = PagoClienteSerializer
    # P0-017: solo roles del dominio comercial gestionan pagos (ISO 27001 A.9.4)
    permission_classes = [IsAuthenticated, IsVendedorOrEjecutivoOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = PagoCliente.objects.select_related('cliente', 'sede').order_by('-fecha')

        # Filtering: Salesmen only see payments of their assigned clients
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(cliente__vendedor_asignado=user)

        return queryset

    def perform_create(self, serializer):
        """
        P0-005: pago + reconciliación en una sola transacción, con lock
        pesimista sobre el cliente para evitar pagos concurrentes que lean
        el mismo saldo (race condition).
        """
        user = self.request.user
        cliente = serializer.validated_data['cliente']
        monto = serializer.validated_data['monto']

        with transaction.atomic():
            # Lock sin las anotaciones del manager (subqueries no se pueden
            # bloquear); serializa los pagos concurrentes del mismo cliente
            Cliente._base_manager.select_for_update().get(pk=cliente.pk)

            # Saldo leído DENTRO del lock — ningún otro pago puede intercalarse
            saldo_actual = Cliente.objects.get(pk=cliente.pk).saldo_calculado

            if monto <= 0:
                raise ValidationError({'monto': 'El monto del pago debe ser mayor a cero.'})

            # P1-002: sobrepago solo con marca explícita de anticipo — previene
            # errores de digitación sin bloquear pagos por adelantado legítimos
            es_anticipo = serializer.validated_data.get('es_anticipo', False)
            if monto > saldo_actual and not es_anticipo:
                raise ValidationError({
                    'monto': (
                        f'El pago (${monto}) excede la deuda actual del cliente '
                        f'(${saldo_actual}). Si es un pago por adelantado, '
                        f'marque la opción "Anticipo".'
                    )
                })

            # Auto-assign sede from user
            if hasattr(user, 'sede') and user.sede:
                serializer.save(sede=user.sede)
            else:
                serializer.save()

            # Reconciliación dentro de la misma transacción: si falla,
            # el pago se revierte junto con ella (sin pagos huérfanos)
            PaymentReconciler.reconcile_client_orders(serializer.instance.cliente)

    def destroy(self, request, *args, **kwargs):
        """
        Artefacto RUP: Eliminación de Pago con Reversión
        Caso de Uso: CU-ReversionPagoCliente

        DELETE /pagos-cliente/{id}/ con justificación obligatoria.

        Valida: justificación no vacía (requerida para auditoría).
        Si falta: HTTP 400 Bad Request.
        Si éxito: HTTP 204 No Content.
        """
        pago = self.get_object()
        justificacion = request.data.get('justificacion', '').strip() if request.data else ''

        if not justificacion:
            return Response(
                {'justificacion': 'Justificación obligatoria para revertir pago'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # P0-005: reversión + reconciliación atómicas, con lock del cliente
            with transaction.atomic():
                Cliente._base_manager.select_for_update().get(pk=pago.cliente_id)

                resultado = PagoReversionService.revertir_pago(
                    pago,
                    request.user,
                    justificacion
                )

                # Trigger Reconciliation for the client after reversal
                PaymentReconciler.reconcile_client_orders(pago.cliente)

            logger.info(
                f"[REVERSIÓN PAGO EXITOSA] Pago {resultado['pago_id']} revertido. "
                f"Cliente: {resultado['cliente_nombre']}, "
                f"Monto: {resultado['monto_revertido']}"
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValueError as e:
            return Response(
                {'justificacion': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[ERROR REVERSIÓN PAGO] {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error al revertir pago'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='revertir',
            permission_classes=[IsAuthenticated, IsVendedorOrEjecutivoOrAdmin])
    def revertir(self, request, pk=None):
        """
        Artefacto RUP: Acción de Reversión de Pago (alternativa a DELETE)
        Caso de Uso: CU-ReversionPagoCliente

        POST /pagos-cliente/{id}/revertir/ con justificación en body.

        Más amigable que DELETE para usuarios/frontend.
        Respuesta: 200 OK con estadísticas o 400 Bad Request.
        """
        pago = self.get_object()
        justificacion = request.data.get('justificacion', '').strip() if request.data else ''

        if not justificacion:
            return Response(
                {'error': 'Justificación obligatoria para revertir pago'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # P0-005: reversión + reconciliación atómicas, con lock del cliente
            with transaction.atomic():
                Cliente._base_manager.select_for_update().get(pk=pago.cliente_id)

                resultado = PagoReversionService.revertir_pago(
                    pago,
                    request.user,
                    justificacion
                )

                # Trigger Reconciliation for the client after reversal
                PaymentReconciler.reconcile_client_orders(pago.cliente)

            return Response(
                {
                    'message': (
                        'Pago revertido exitosamente. '
                        'Deuda del cliente restaurada a '
                        f'${resultado["saldo_anterior_pago"]}'
                    ),
                    'resultado': {
                        'pago_id': resultado['pago_id'],
                        'cliente_id': resultado['cliente_id'],
                        'cliente_nombre': resultado['cliente_nombre'],
                        'monto_revertido': str(
                            resultado['monto_revertido']),
                        'saldo_anterior_pago': str(
                            resultado['saldo_anterior_pago'])}},
                status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[ERROR REVERSIÓN PAGO] {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error al revertir pago'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PedidoVentaViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoVentaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = PedidoVenta.objects.select_related('cliente', 'sede').order_by('-fecha_pedido')

        # Filtro opcional por vendedor (solo para roles con visión gerencial/sistemas)
        vendedor_id = self.request.query_params.get('vendedor_id')
        vendedor_username = self.request.query_params.get('vendedor_username')
        if (vendedor_id or vendedor_username) and (
            user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()
        ):
            if vendedor_id:
                try:
                    queryset = queryset.filter(vendedor_asignado_id=int(vendedor_id))
                except (TypeError, ValueError):
                    pass
            elif vendedor_username:
                queryset = queryset.filter(vendedor_asignado__username=vendedor_username)

        # Filtering: Salesmen only see their own orders
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(vendedor_asignado=user)

        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

        # Optional: Skip older orders to avoid memory overload (e.g., last 100) only for list action
        if self.action == 'list':
            limit = self.request.query_params.get('limit', 100)
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 100
            return queryset[:limit]

        return queryset

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        pedido = self.get_object()
        cliente = pedido.cliente
        sede = pedido.sede
        detalles = pedido.detalles.select_related('producto').all()

        items = []
        for d in detalles:
            items.append({
                "producto_descripcion": d.producto.descripcion,
                "cantidad": float(d.cantidad),
                "piezas": d.piezas,
                "peso": float(d.peso),
                "precio_unitario": float(d.precio_unitario),
                "incluye_iva": d.incluye_iva
            })

        data = {
            "id": pedido.id,
            "guia_remision": pedido.guia_remision,
            "fecha_pedido": pedido.fecha_pedido.isoformat(),
            "cliente_nombre": cliente.nombre_razon_social,
            "cliente_ruc": cliente.ruc_cedula,
            "cliente_direccion": cliente.direccion_envio,
            "vendedor_nombre": pedido.vendedor_asignado.username if pedido.vendedor_asignado else None,
            "sede_nombre": sede.location if sede else "Matriz",  # Mostrar ubicación como subtítulo
            "empresa_nombre": sede.nombre if sede else "Empresa Principal",  # Nombre Sede como Empresa Principal
            "esta_pagado": pedido.esta_pagado,
            "valor_retencion": float(pedido.valor_retencion or 0),
            "detalles": items
        }

        # Call microservice
        pdf_content = PrintingService.generate_nota_venta_pdf(data)

        if pdf_content:
            from django.http import HttpResponse
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="pedido_{pedido.guia_remision or pedido.id}.pdf"'
            return response
        else:
            return Response({"error": "El servicio de impresión no está disponible temporalmente."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}

        try:
            # Auto-asignar vendedor si el usuario pertenece al grupo 'vendedor'
            if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
                save_kwargs['vendedor_asignado'] = user

            # Auto-asignar sede del usuario si no se proporcionó una explícitamente
            if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
                save_kwargs['sede'] = user.sede

            serializer.save(**save_kwargs)
            logger.info(
                "Pedido de venta creado exitosamente",
                extra={
                    "sd": {
                        "entity": "PedidoVenta",
                        "id": serializer.instance.id,
                        "user": user.username}})

            # Trigger Reconciliation
            # Note: serializer.save() returns the instance, but
            # perform_create doesn't return anything by default in DRF
            # ViewSet logic unless overridden in standard create()
            # However, serializer.instance is populated.

            if serializer.instance:
                PaymentReconciler.reconcile_client_orders(serializer.instance.cliente)
        except Exception as e:
            logger.error("Error al crear Pedido de Venta", extra={"sd": {"entity": "PedidoVenta", "error": str(e)}})
            raise

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """
        Anula un pedido en estado 'pendiente'.
        Requiere motivo_anulacion (mínimo 10 caracteres).
        El saldo del cliente se recalcula automáticamente al excluir pedidos anulados.
        """
        pedido = self.get_object()
        user = request.user

        allowed_groups = ['vendedor', 'jefe_area', 'jefe_planta', 'admin_sede', 'admin_sistemas']
        if not (user.is_superuser or user.groups.filter(name__in=allowed_groups).exists()):
            return Response({"error": "No tienes permisos para anular pedidos."}, status=status.HTTP_403_FORBIDDEN)

        if pedido.anulado:
            return Response({"error": "Este pedido ya fue anulado."}, status=status.HTTP_400_BAD_REQUEST)

        if pedido.estado != 'pendiente':
            return Response(
                {"error": f"Solo se pueden anular pedidos en estado 'pendiente'. Estado actual: {pedido.estado}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AnulacionPedidoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        motivo = serializer.validated_data['motivo_anulacion']

        try:
            with transaction.atomic():
                pedido.anulado = True
                pedido.motivo_anulacion = motivo
                pedido.anulado_por = user
                pedido.fecha_anulacion = timezone.now()
                pedido.save()

                from gestion.models import AuditLog
                from django.contrib.contenttypes.models import ContentType
                from gestion.middleware import _local
                AuditLog.objects.create(
                    usuario=user,
                    ip_address=getattr(_local, 'ip_address', '0.0.0.0'),  # nosec B104
                    content_type=ContentType.objects.get_for_model(pedido),
                    object_id=pedido.pk,
                    object_sede_id=pedido.sede_id,
                    accion='UPDATE',
                    valor_anterior={'anulado': False, 'estado': pedido.estado},
                    valor_nuevo={'anulado': True, 'motivo_anulacion': motivo},
                    justificacion=motivo,
                )

                if pedido.cliente:
                    PaymentReconciler.reconcile_client_orders(pedido.cliente)

                logger.info(
                    "Pedido de venta anulado",
                    extra={'sd': {'entity': 'PedidoVenta', 'id': pedido.id, 'user': user.username}}
                )
                return Response({"message": "Pedido anulado correctamente."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Error al anular pedido",
                extra={
                    'sd': {
                        'entity': 'PedidoVenta',
                        'id': pk,
                        'error': str(e)}},
                exc_info=True)
            return Response({"error": "Error inesperado al anular el pedido."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'])
    def modificar(self, request, pk=None):
        """
        Modifica campos de un pedido en estado 'pendiente' y no anulado.
        Requiere motivo (mínimo 10 caracteres). Registra auditoría.
        """
        pedido = self.get_object()
        user = request.user

        allowed_groups = ['vendedor', 'jefe_area', 'jefe_planta', 'admin_sede', 'admin_sistemas']
        if not (user.is_superuser or user.groups.filter(name__in=allowed_groups).exists()):
            return Response({"error": "No tienes permisos para modificar pedidos."}, status=status.HTTP_403_FORBIDDEN)

        if pedido.anulado:
            return Response({"error": "No se puede modificar un pedido anulado."}, status=status.HTTP_400_BAD_REQUEST)

        if pedido.estado != 'pendiente':
            return Response(
                {"error": f"Solo se pueden modificar pedidos en estado 'pendiente'. Estado actual: {pedido.estado}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ModificacionPedidoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        motivo = data.pop('motivo')
        campos_modificados = []
        valor_anterior = {}

        try:
            with transaction.atomic():
                for campo, nuevo_valor in data.items():
                    valor_viejo = getattr(pedido, campo)
                    if str(valor_viejo) != str(nuevo_valor):
                        valor_anterior[campo] = str(valor_viejo)
                        setattr(pedido, campo, nuevo_valor)
                        campos_modificados.append(campo)

                if not campos_modificados:
                    return Response({"message": "No se detectaron cambios."}, status=status.HTTP_200_OK)

                pedido.save()

                from gestion.models import AuditLog
                from django.contrib.contenttypes.models import ContentType
                from gestion.middleware import _local
                AuditLog.objects.create(
                    usuario=user,
                    ip_address=getattr(_local, 'ip_address', '0.0.0.0'),  # nosec B104
                    content_type=ContentType.objects.get_for_model(pedido),
                    object_id=pedido.pk,
                    object_sede_id=pedido.sede_id,
                    accion='UPDATE',
                    valor_anterior=valor_anterior,
                    valor_nuevo={c: str(getattr(pedido, c)) for c in campos_modificados},
                    justificacion=motivo,
                )

                if pedido.cliente:
                    PaymentReconciler.reconcile_client_orders(pedido.cliente)

                logger.info(
                    "Pedido de venta modificado",
                    extra={
                        'sd': {
                            'entity': 'PedidoVenta',
                            'id': pedido.id,
                            'cambios': campos_modificados,
                            'user': user.username}})
                return Response({"message": "Pedido modificado correctamente.",
                                "cambios": campos_modificados}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Error al modificar pedido",
                extra={
                    'sd': {
                        'entity': 'PedidoVenta',
                        'id': pk,
                        'error': str(e)}},
                exc_info=True)
            return Response({"error": "Error inesperado al modificar el pedido."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def _reconciliar_cliente(self, detalle):
        """
        P1-002: al cambiar los detalles cambia el valor del pedido — se
        re-reconcilia para que anticipos existentes se apliquen de inmediato.
        """
        if detalle.pedido_venta and detalle.pedido_venta.cliente:
            PaymentReconciler.reconcile_client_orders(detalle.pedido_venta.cliente)

    def perform_create(self, serializer):
        detalle = serializer.save()
        self._reconciliar_cliente(detalle)

    def perform_update(self, serializer):
        detalle = serializer.save()
        self._reconciliar_cliente(detalle)

    def perform_destroy(self, instance):
        cliente = instance.pedido_venta.cliente if instance.pedido_venta else None
        instance.delete()
        if cliente:
            PaymentReconciler.reconcile_client_orders(cliente)
