"""
ReportFactory: crea el ReportService con el formateador correcto.
Factory Pattern + OCP: agregar un formato nuevo no requiere modificar el router.
"""
from ..formatters.excel_formatter import ExcelFormatter
from ..formatters.csv_formatter import CsvFormatter
from .report_service import ReportService


class ReportFactory:
    """Construye el ReportService para un formato de salida dado."""

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
        formatters = {
            "xlsx": ExcelFormatter(),
            "csv": CsvFormatter(),
        }

        formatter = formatters.get(format)
        if formatter is None:
            raise ValueError(f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")

        return ReportService(formatter=formatter)
