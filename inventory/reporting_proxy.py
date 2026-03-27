import httpx
import os
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from gestion.models import Bodega

class ReportingProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, report_path):
        user = request.user
        
        # 1. Obtener parámetros
        bodega_id = request.query_params.get('bodega_id')
        
        # 2. Validación de permisos para reportes que requieren bodega_id
        # Reportes generales que no requieren bodega_id específica (ej: catalogo productos)
        reports_requiring_bodega = [
            'kardex', 'stock-actual', 'valorizacion', 
            'aging', 'rotacion', 'resumen-movimientos'
        ]
        
        is_restricted_report = any(req in report_path for req in reports_requiring_bodega)
        
        if is_restricted_report:
            if not bodega_id:
                return JsonResponse({"detail": "bodega_id es requerido para este reporte"}, status=400)
            
            try:
                bodega = Bodega.objects.get(id=bodega_id)
            except Bodega.DoesNotExist:
                return JsonResponse({"detail": "Bodega no encontrada"}, status=404)
            
            # Verificar si el usuario es admin o tiene la bodega asignada
            is_admin = user.is_superuser or user.groups.filter(
                name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']
            ).exists()
            
            if not is_admin:
                if not user.bodegas_asignadas.filter(id=bodega_id).exists():
                    return JsonResponse({"detail": "No tiene permiso para acceder a esta bodega"}, status=403)
                
                # Opcional: Validar que la bodega pertenezca a la misma sede si es admin_sede (pero admin_sede ya pasó arriba)
                # Si quisiéramos ser ultra-estrictos con admin_sede:
                # if user.groups.filter(name='admin_sede').exists() and bodega.sede_id != getattr(user, 'sede_id', None):
                #     return JsonResponse({"detail": "No tiene permiso para bodegas de otra sede"}, status=403)

        # 3. Preparar llamada al microservicio
        service_url = os.getenv("REPORTING_SERVICE_URL", "http://reporting_excel:8002")
        internal_key = os.getenv("REPORTING_INTERNAL_KEY", "dev-internal-secret-key-change-in-prod")
        
        # Limpiar el path para asegurar que no haya dobles slashes
        clean_path = report_path.lstrip('/')
        target_url = f"{service_url}/{clean_path}"
        
        # Forwarding params
        params = request.query_params.dict()
        
        # Agregar sede_id del usuario si existe para filtrar en el SP (opcional para el SP)
        if hasattr(user, 'sede_id') and user.sede_id:
            params['user_sede_id'] = user.sede_id

        headers = {
            "X-Internal-Key": internal_key
        }

        try:
            # Usar un timeout razonable para generación de Excel
            with httpx.Client(timeout=60.0) as client:
                response = client.get(target_url, params=params, headers=headers)
                
                if response.status_code != 200:
                    try:
                        error_detail = response.json()
                    except:
                        error_detail = {"detail": "Error en el microservicio de reportes"}
                    return JsonResponse(error_detail, status=response.status_code)
                
                # 4. Retornar el binario
                django_response = HttpResponse(
                    content=response.content,
                    status=response.status_code,
                    content_type=response.headers.get("Content-Type")
                )
                
                # Copiar headers importantes de descarga
                if "Content-Disposition" in response.headers:
                    django_response["Content-Disposition"] = response.headers["Content-Disposition"]
                
                return django_response

        except httpx.RequestError as exc:
            return JsonResponse({"detail": f"Error de conexión con el servicio de reportes: {str(exc)}"}, status=502)
        except Exception as e:
            return JsonResponse({"detail": f"Error interno en el proxy: {str(e)}"}, status=500)
