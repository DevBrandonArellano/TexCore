from django.core.management.base import BaseCommand
from inventory.services.mrp_engine import MRPEngine
import logging

logger = logging.getLogger('inventory.mrp')

class Command(BaseCommand):
    help = "Ejecuta el Motor MRP para calcular y sugerir órdenes de compra."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando ejecución del Motor MRP..."))
        
        try:
            mrp = MRPEngine()
            mrp.ejecutar_mrp()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"MRP ejecutado exitosamente. Se generaron {mrp.requerimientos_generados} requerimientos y {mrp.ocs_generadas} órdenes de compra sugeridas."
                )
            )
        except Exception as e:
            logger.exception("Error ejecutando el motor MRP")
            self.stdout.write(self.style.ERROR(f"Error ejecutando MRP: {str(e)}"))
