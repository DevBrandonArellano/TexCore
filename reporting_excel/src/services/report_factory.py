"""
ReportFactory: crea el ReportService correcto según el formato de salida solicitado.
Factory Pattern + OCP: agregar un nuevo formato solo requiere agregar un caso aquí.
"""
from ..repositories.sql_repository import SqlReportRepository
from ..formatters.excel_formatter import ExcelFormatter
from ..formatters.csv_formatter import CsvFormatter
from .report_service import ReportService


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
        repo = SqlReportRepository()

        formatters = {
            "xlsx": ExcelFormatter(),
            "csv": CsvFormatter(),
        }

        formatter = formatters.get(format)
        if formatter is None:
            raise ValueError(f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")

        return ReportService(repository=repo, formatter=formatter)
