from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import OrdenProduccion, DetalleFormula

@receiver(post_save, sender=OrdenProduccion)
def debit_inventory_on_production_completion(sender, instance, created, **kwargs):
    """
    Cuando una OrdenProduccion se marca como 'Finalizada', este signal
    descuenta automáticamente los insumos requeridos de la bodega asociada.
    """
    from inventory.models import StockItem # MOVED IMPORT

    # Ejecutar solo si el estado es 'finalizada' y el inventario no ha sido descontado aún.
    if instance.estado == 'finalizada' and not instance.inventario_descontado:
        
        # Validar que la orden tenga una bodega y una fórmula asignadas.
        if not instance.bodega:
            # En un caso real, podríamos registrar esto como un error en lugar de levantarlo,
            # pero para este ejemplo, es importante que la validación sea clara.
            raise ValidationError("La orden de producción debe tener una bodega asignada para descontar el inventario.")

        if not instance.formula_color:
            raise ValidationError("La orden de producción debe tener una fórmula de color para calcular los insumos.")

        try:
            # Usar una transacción atómica para asegurar que todas las operaciones de BD
            # se completen exitosamente, o se reviertan si alguna falla.
            with transaction.atomic():
                # Obtener los componentes de la fórmula.
                detalles_formula = instance.formula_color.detalleformula_set.all()

                if not detalles_formula.exists():
                    # Si la fórmula no tiene componentes, no hay nada que descontar.
                    # Marcamos como descontado y terminamos.
                    instance.inventario_descontado = True
                    instance.save(update_fields=['inventario_descontado'])
                    return

                for detalle in detalles_formula:
                    # Calcular la cantidad necesaria del químico.
                    # La fórmula está en gramos/kilo, y el peso de la orden en kilos.
                    cantidad_requerida_gramos = detalle.gramos_por_kilo * instance.peso_neto_requerido
                    # Asumiendo que la unidad de medida del stock de químicos es KILOGRAMOS.
                    cantidad_requerida_kg = cantidad_requerida_gramos / 1000

                    # Obtener el item de stock para el químico y bodega, con bloqueo para evitar concurrencia.
                    stock_item, created = StockItem.objects.select_for_update().get_or_create(
                        bodega=instance.bodega,
                        chemical=detalle.chemical,
                        defaults={'quantity': 0}
                    )

                    # Verificar si hay stock suficiente.
                    if stock_item.quantity < cantidad_requerida_kg:
                        raise ValidationError(
                            f"Stock insuficiente para '{detalle.chemical.name}' en la bodega '{instance.bodega.nombre}'. "
                            f"Requerido: {cantidad_requerida_kg:.2f} kg, Disponible: {stock_item.quantity} kg."
                        )

                    # Descontar el stock.
                    stock_item.quantity -= cantidad_requerida_kg
                    stock_item.save()

                # Si todo el bucle se completa sin errores, marcar la orden como procesada.
                instance.inventario_descontado = True
                # Usamos update_fields para evitar llamar al signal de nuevo en un bucle infinito.
                instance.save(update_fields=['inventario_descontado'])

        except ValidationError as e:
            # Si se captura una ValidationError (stock insuficiente), se debe notificar o manejar.
            # La transacción se revierte automáticamente al salir del bloque 'with'.
            # Aquí podríamos añadir un log o enviar una notificación al usuario.
            # Por ahora, simplemente relanzamos la excepción para que DRF la maneje y la muestre en la API.
            raise e
        except Exception as e:
            # Capturar cualquier otra excepción inesperada durante la transacción.
            # La transacción también se revierte.
            # Loggear el error sería importante en producción.
            raise e
