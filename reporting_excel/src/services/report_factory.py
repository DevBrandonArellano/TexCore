"""
ReportFactory: crea el ReportService con DjangoReportRepository.
Factory Pattern + OCP: cambiar repositorio no requiere modificar routers.
"""
from ..infrastructure.django_client import DjangoReportRepository
from ..formatters.excel_formatter import ExcelFormatter
from ..formatters.csv_formatter import CsvFormatter
from .report_service import ReportService


def _get_repo() -> DjangoReportRepository:
    """Importa el singleton desde main.py (inicializado al arrancar el servicio)."""
    from ..main import django_report_repo
    return django_report_repo


class ReportFactory:
    """Construye el grafo de dependencias para un reporte dado un formato de salida."""

    @staticmethod
    def create(format: str) -> ReportService:
        """
        Args:
            format: "xlsx" o "csv"

        Returns:
            ReportService configurado con el formateador correcto.

        Raises:
            ValueError: Si el formato no es soportado.
        """
        repo = _get_repo()

        formatters = {
            "xlsx": ExcelFormatter(),
            "csv": CsvFormatter(),
        }

        formatter = formatters.get(format)
        if formatter is None:
            raise ValueError(f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")

        return ReportService(repository=repo, formatter=formatter)
