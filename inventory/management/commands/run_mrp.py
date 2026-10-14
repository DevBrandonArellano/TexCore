from django.core.management.base import BaseCommand, CommandError

from gestion.models import Sede
from inventory.models import MRPEjecucion
from inventory.services.mrp import MRPEngine


class Command(BaseCommand):
    help = "Ejecuta el motor MRP de una sede (--sede) o de todas las sedes activas (ADR-012)."

    def add_arguments(self, parser):
        parser.add_argument("--sede", type=int, help="ID de la sede a calcular; sin él, todas las activas.")

    def handle(self, *args, **options):
        if options["sede"]:
            sede = Sede.objects.filter(pk=options["sede"]).first()
            if sede is None:
                raise CommandError(f"No existe la sede {options['sede']}.")
            sedes = [sede]
        else:
            sedes = list(Sede.objects.filter(status="activo").order_by("nombre"))

        fallidas = []
        for sede in sedes:
            ejecucion = MRPEngine.ejecutar(sede)
            if ejecucion.estado == MRPEjecucion.ESTADO_FALLIDA:
                fallidas.append(sede.nombre)
                self.stdout.write(self.style.ERROR(f"{sede.nombre}: {ejecucion.mensaje_error}"))
                continue
            self.stdout.write(
                self.style.SUCCESS(
                    f"{sede.nombre}: {ejecucion.requerimientos} requerimientos, "
                    f"{ejecucion.sugerencias_compra} sugerencias de compra, "
                    f"{ejecucion.productos_a_producir} productos a producir, "
                    f"{len(ejecucion.advertencias)} advertencias."
                )
            )
            for advertencia in ejecucion.advertencias:
                self.stdout.write(self.style.WARNING(f"  - {advertencia}"))
        if fallidas:
            raise CommandError(f"El MRP falló en: {', '.join(fallidas)}.")
