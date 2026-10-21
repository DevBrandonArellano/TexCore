"""
RUP - Capa de Servicio: ExecutiveKPIService
===========================================
Artefacto   : Diseño de Componentes
Módulo      : Inventario / MRP / KPIs Ejecutivos
Patrón      : Service Layer — agrega datos de MRP, stock y cobranza en un único punto de acceso
Principios  : SOLID — S: una clase por dominio de datos, O: extensible sin modificar vistas,
              D: vistas dependen de la interfaz del servicio, no del ORM directamente.

Responsabilidad: Proveer KPIs gerenciales de MRP, alertas de stock y cartera para el
dashboard ejecutivo. Solo lectura — no modifica estado del sistema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Max, OuterRef, Subquery, Sum

from gestion.models import Cliente, PedidoVenta
from inventory.models import MRPEjecucion, OrdenCompraSugerida, StockBodega

# RFC 5424: logger bajo el namespace 'inventory' — capturado por el handler de settings.py
logger = logging.getLogger("inventory.services.executive_kpi")


# ---------------------------------------------------------------------------
# Objetos de valor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MRPKPIs:
    """KPIs del MRP para la vista ejecutiva (ADR-012)."""

    sugerencias_compra: int  # sugerencias vigentes (informativas)
    productos_a_producir: int  # de la última ejecución completada de cada sede
    ultima_ejecucion: datetime | None  # la más reciente de esas ejecuciones


@dataclass(frozen=True)
class StockKPIs:
    """KPIs de alertas de inventario."""

    productos_bajo_minimo: int


@dataclass(frozen=True)
class CarteraKPIs:
    """KPIs financieros de cartera y cobranza."""

    cuentas_por_cobrar: Decimal
    cartera_vencida: Decimal
    pedidos_pendientes: int
    pedidos_despachados: int


@dataclass(frozen=True)
class ExecutiveKPIs:
    """
    Contrato consolidado para el endpoint /kpi-ejecutivo/.
    Inmutable — garantiza consistencia entre el servicio y las vistas.
    """

    mrp: MRPKPIs
    stock: StockKPIs
    cartera: CarteraKPIs


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------


class ExecutiveKPIService:
    """
    Agrega KPIs de MRP, stock y cartera en un único objeto.

    Uso:
        service = ExecutiveKPIService(sede_id=None)  # None = todas las sedes
        kpis = service.obtener_kpis()

    Inversión de dependencias: solo usa abstracciones de Django ORM.
    No conoce la capa HTTP (sin Request/Response).
    """

    def __init__(self, sede_id: int | None = None) -> None:
        self._sede_id = sede_id

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def obtener_kpis(self) -> ExecutiveKPIs:
        """Punto de entrada único — Fachada."""
        logger.info(
            "Calculando KPIs ejecutivos consolidados",
            extra={"sd": {"sede_id": str(self._sede_id or "all")}},
        )
        try:
            result = ExecutiveKPIs(
                mrp=self._mrp_kpis(),
                stock=self._stock_kpis(),
                cartera=self._cartera_kpis(),
            )
        except Exception as exc:
            logger.exception(
                "Error calculando KPIs ejecutivos: %s",
                exc,
                extra={"sd": {"sede_id": str(self._sede_id or "all"), "error": type(exc).__name__}},
            )
            raise
        logger.info(
            "KPIs ejecutivos calculados — sugerencias_compra=%s bajo_minimo=%s cxc=%s",
            result.mrp.sugerencias_compra,
            result.stock.productos_bajo_minimo,
            result.cartera.cuentas_por_cobrar,
            extra={
                "sd": {
                    "sede_id": str(self._sede_id or "all"),
                    "sugerencias_compra": str(result.mrp.sugerencias_compra),
                    "bajo_minimo": str(result.stock.productos_bajo_minimo),
                    "cxc": str(result.cartera.cuentas_por_cobrar),
                    "cartera_vencida": str(result.cartera.cartera_vencida),
                }
            },
        )
        return result

    # ------------------------------------------------------------------
    # Métodos privados — SRP estricto
    # ------------------------------------------------------------------

    def _filtrar_sede(self, qs, campo_sede: str = "sede_id"):
        if self._sede_id:
            return qs.filter(**{campo_sede: self._sede_id})
        return qs

    def _mrp_kpis(self) -> MRPKPIs:
        completadas = MRPEjecucion.objects.filter(estado=MRPEjecucion.ESTADO_COMPLETADA)
        ultima_de_su_sede = completadas.filter(sede_id=OuterRef("sede_id")).order_by("-inicio", "-id").values("pk")[:1]
        ultimas = (
            self._filtrar_sede(completadas)
            .filter(pk=Subquery(ultima_de_su_sede))
            .aggregate(
                productos=Sum("productos_a_producir"),
                fecha=Max("inicio"),
            )
        )
        return MRPKPIs(
            sugerencias_compra=self._filtrar_sede(OrdenCompraSugerida.objects.all()).count(),
            productos_a_producir=ultimas["productos"] or 0,
            ultima_ejecucion=ultimas["fecha"],
        )

    def _stock_kpis(self) -> StockKPIs:
        """
        Cuenta productos con stock actual < stock_mínimo.
        Filtra por sede a través de bodega__sede si aplica.
        """
        from django.db.models import F as Fdb

        qs = StockBodega.objects.filter(cantidad__lt=Fdb("producto__stock_minimo"))
        if self._sede_id:
            qs = qs.filter(bodega__sede_id=self._sede_id)

        bajo_minimo = qs.values("producto_id").distinct().count()
        return StockKPIs(productos_bajo_minimo=bajo_minimo)

    def _cartera_kpis(self) -> CarteraKPIs:
        clientes_qs = self._filtrar_sede(Cliente.objects.filter(is_active=True))

        totales = clientes_qs.aggregate(
            cxc=Sum("saldo_calculado"),
            vencida=Sum("cartera_vencida"),
        )

        pedidos_qs = self._filtrar_sede(PedidoVenta.objects.all())
        pedidos_counts = pedidos_qs.values("estado").annotate(total=Count("id"))
        estados_pedidos = {row["estado"]: row["total"] for row in pedidos_counts}

        return CarteraKPIs(
            cuentas_por_cobrar=totales["cxc"] or Decimal("0"),
            cartera_vencida=totales["vencida"] or Decimal("0"),
            pedidos_pendientes=estados_pedidos.get("pendiente", 0),
            pedidos_despachados=estados_pedidos.get("despachado", 0),
        )
