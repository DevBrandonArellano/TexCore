"""
Servicio de Reversión de Pagos del Cliente
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-ReversionPagoCliente
Patrón: Service Layer + Transactional Script
SOLID: SRP — este módulo solo gestiona reversión de pagos de clientes.

Permite deshacer pagos registrados y restaurar la deuda del cliente
al monto anterior (anterior al abono). Operación atómica con auditoría completa.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from gestion.models import Cliente
import logging

logger = logging.getLogger(__name__)


class PagoReversionService:
    """
    Servicio de reversión de pagos.
    Responsable único: deshacer un pago y restaurar deuda del cliente.
    """

    @staticmethod
    @transaction.atomic
    def revertir_pago(pago, usuario, justificacion: str) -> dict:
        """
        Revierte un pago deshaciendo el abono registrado.

        Validaciones:
        - Justificación obligatoria y no vacía
        - Pago debe existir
        - Cliente debe existir

        Operación atómica: si algo falla, todo se revierte.

        Args:
            pago (PagoCliente): Instancia del pago a revertir
            usuario (CustomUser): Usuario que ejecuta la reversión
            justificacion (str): Razón de la reversión

        Returns:
            dict: Estadísticas de reversión {
                'pago_id': int,
                'cliente_id': int,
                'cliente_nombre': str,
                'monto_revertido': Decimal,
                'saldo_anterior_pago': Decimal,  # deuda ANTES del pago
                'saldo_despues_reversion': Decimal  # deuda DESPUÉS de revertir
            }

        Raises:
            ValueError: Si justificación está vacía
            ValidationError: Si el pago no puede ser revertido
        """
        # Validación: justificación obligatoria
        if not justificacion or not str(justificacion).strip():
            raise ValueError("Justificación obligatoria para revertir pago")

        # Obtenemos el cliente a través del manager para asegurar que saldo_calculado esté disponible
        cliente = Cliente.objects.get(pk=pago.cliente_id)
        if not cliente:
            raise ValidationError("Pago no tiene cliente asociado")

        pago_id = pago.id  # preserve before delete() sets pk to None
        monto = pago.monto

        # Calculamos el saldo del cliente ANTES del pago:
        # Saldo_antes_pago = Saldo_actual + monto_pago (el pago redujo la deuda,
        # así que sumarlo de vuelta la restaura — no se itera el historial de pagos).

        logger.info(
            f"[REVERSIÓN PAGO] Usuario: {usuario.username}, "
            f"Pago: {pago.id}, Cliente: {cliente.nombre_razon_social}, "
            f"Monto: {monto}, Justificación: {justificacion}"
        )

        # Registrar el pago a revertir (valor anterior antes de borrar)
        saldo_anterior_pago = cliente.saldo_calculado + monto if cliente.saldo_calculado else monto

        try:
            # Eliminar el pago (la deuda se restaurará automáticamente en el cálculo)
            pago.delete()

            logger.info(
                f"[REVERSIÓN PAGO EXITOSA] Pago {pago.id} eliminado. "
                f"Deuda restaurada a: {saldo_anterior_pago}"
            )

            resultado = {
                'pago_id': pago_id,
                'cliente_id': cliente.id,
                'cliente_nombre': cliente.nombre_razon_social,
                'monto_revertido': monto,
                'saldo_anterior_pago': saldo_anterior_pago,
                'saldo_despues_reversion': saldo_anterior_pago  # Será el nuevo saldo calculado
            }

            return resultado

        except Exception as e:
            logger.error(
                f"[ERROR REVERSIÓN PAGO] Pago {pago.id}, Cliente {cliente.id}: {str(e)}",
                exc_info=True
            )
            raise
