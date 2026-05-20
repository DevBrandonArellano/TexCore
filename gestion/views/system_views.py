from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
import logging
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, IsAdminUser, AllowAny
from gestion.permissions import IsSystemAdmin, IsTintoreroOrAdmin, IsAdminSistemasOrSede, IsJefeAreaOrAdmin
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.pago_reversion import PagoReversionService
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db.models import Count
from gestion.models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente, PagoCliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Maquina,
    Proveedor, FaseReceta
)
from gestion.utils import PrintingService, PaymentReconciler
from gestion.serializers import (
    GroupSerializer, SedeSerializer, AreaSerializer, CustomUserSerializer, ProductoSerializer,
    BatchSerializer, BodegaSerializer, ProcessStepSerializer,
    FormulaColorSerializer, FormulaColorWriteSerializer,
    DetalleFormulaSerializer, DosificacionSerializer,
    ClienteSerializer, ClienteListSerializer, OrdenProduccionSerializer, OrdenProduccionEstadoSerializer,
    LoteProduccionSerializer, PedidoVentaSerializer, DetallePedidoSerializer,
    MaquinaSerializer, RegistrarLoteProduccionSerializer, PagoClienteSerializer,
    ProveedorSerializer, AnulacionPedidoSerializer, ModificacionPedidoSerializer,
)
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db.models import Sum, F, Avg, DurationField, ExpressionWrapper, Q
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


from django.db.models import OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class FrontendLogView(APIView):
    """
    Relay para logs del frontend. Recibe LogEntry (LogEntry.ts) via navigator.sendBeacon
    o fetch POST y los re-emite mediante el logger del backend en formato RFC 5424.
    """
    authentication_classes = [] # Permitir incluso sin sesión
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            entry = request.data
            if not isinstance(entry, dict):
                return Response(status=status.HTTP_400_BAD_REQUEST)
                
            severity = entry.get('severity', 6)
            msgid = entry.get('msgid', 'frontend').replace('.', '-')
            message = entry.get('message', '')
            sd = entry.get('sd', {})
            
            # Datos adicionales de contexto
            sd['source'] = 'browser'
            sd['ip'] = request.META.get('REMOTE_ADDR', 'unknown')
            
            f_logger = logging.getLogger(f"frontend.{msgid}")
            
            # Mapeo RFC 5424 -> Python levels
            if severity <= 2:
                level = logging.CRITICAL
            elif severity == 3:
                level = logging.ERROR
            elif severity == 4:
                level = logging.WARNING
            elif severity >= 5:
                level = logging.INFO
            else:
                level = logging.DEBUG
                
            f_logger.log(level, message, extra={'sd': sd})
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            # Fallo silencioso para el cliente, pero registrar en el backend si es posible
            return Response(status=status.HTTP_400_BAD_REQUEST)

