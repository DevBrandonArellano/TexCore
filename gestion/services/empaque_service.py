"""
RUP - Capa de Servicio: EmpaqueService
=======================================
Artefacto   : Diseño de Componentes
Módulo      : Producción / Empaquetado Jerárquico
Patrón      : Service Layer + Strategy (resolución de configuración por prioridad)
              + Template Method (DTO EtiquetaBulto + generación ZPL masiva)
Principios  : SOLID — S: una clase, una responsabilidad de empaque.
              O: la jerarquía de fallback se extiende sin modificar la vista.
              D: las vistas dependen de esta interfaz, no del ORM ni del HTTP client.

Casos de Uso:
    CU-EMP-01  Configurar Empaque    — gestión de ConfiguracionEmpaque vía API.
    CU-EMP-02  Generar Bultos        — generación atómica de BultoEmpaque por lote.
    CU-EMP-03  Impresión Masiva      — payload de etiquetas + ZPL unificado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When

from gestion.models import BultoEmpaque, ConfiguracionEmpaque, LoteProduccion

logger = logging.getLogger("gestion.services.empaque")

_CUANTIA = Decimal("0.001")  # 3 decimales para kg


# ---------------------------------------------------------------------------
# Excepciones personalizadas — Domain Errors
# ---------------------------------------------------------------------------

class EmpaqueException(Exception):
    """Base de todas las excepciones del dominio de empaque."""


class ConfiguracionEmpaqueNoEncontrada(EmpaqueException):
    """Lanzada cuando no hay configuración aplicable y no se permite fallback global."""


class BultosYaGenerados(EmpaqueException):
    """Lanzada al intentar generar bultos para un lote que ya los tiene."""


class LoteSinPesoValido(EmpaqueException):
    """Lanzada cuando el lote no tiene peso_neto_producido > 0."""


# ---------------------------------------------------------------------------
# Value Objects (DTO inmutables)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfigEmpaque:
    """Configuración resuelta (inmutable) para un lote concreto."""
    bultos_por_lote: int
    unidades_por_bulto: int
    tara_bulto: Decimal


@dataclass(frozen=True)
class EtiquetaBulto:
    """Payload de etiqueta (DTO) para enviar al microservicio de impresión."""
    lote_codigo: str
    bulto_correlativo: int
    bulto_total: int
    producto_descripcion: str
    sede_nombre: str
    peso_neto: Decimal
    peso_bruto: Decimal
    tara: Decimal
    unidades: int
    qr_data: str

    def to_print_payload(self) -> dict:
        """Serializa al formato que espera el endpoint /zpl/etiqueta del microservicio."""
        return {
            "empresa": self.sede_nombre,
            "producto_desc": self.producto_descripcion,
            "lote_codigo": f"{self.lote_codigo}-B{self.bulto_correlativo:02d}",
            "peso_neto": float(self.peso_neto),
            "unidad": "kg",
            "qr_data": self.qr_data,
        }


@dataclass
class ResultadoEmpaque:
    """Resultado completo de una operación de generación de bultos."""
    bultos_generados: int
    etiquetas: list[EtiquetaBulto] = field(default_factory=list)
    zpl_unificado: Optional[str] = None  # Bloque ZPL listo para enviar a la impresora


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------

class EmpaqueService:
    """
    Capa de servicio para Empaquetado Jerárquico de hilos.

    Uso:
        service = EmpaqueService()
        resultado = service.generar_bultos(lote, usuario)
        # resultado.bultos_generados → int
        # resultado.etiquetas       → list[EtiquetaBulto]
        # resultado.zpl_unificado   → str (todas las etiquetas concatenadas)

    Resolución de configuración (Strategy):
        (producto + sede) → (solo producto) → (solo sede) → global → defaults (15×15)
    """

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    @transaction.atomic
    def generar_bultos(
        self,
        lote: LoteProduccion,
        usuario,
        incluir_zpl: bool = True,
    ) -> ResultadoEmpaque:
        """
        Genera todos los BultoEmpaque para el lote y, opcionalmente, retorna
        el bloque ZPL unificado para impresión masiva.

        Args:
            lote:           LoteProduccion al que se le generarán bultos.
            usuario:        Usuario que dispara la operación (para auditoría).
            incluir_zpl:    Si True, llama al microservicio printing_service
                            para construir un ZPL unificado de todas las etiquetas.

        Raises:
            BultosYaGenerados:  Si el lote ya tiene bultos persistidos.
            LoteSinPesoValido:  Si peso_neto_producido <= 0.
        """
        if lote.peso_neto_producido is None or lote.peso_neto_producido <= 0:
            raise LoteSinPesoValido(
                f"El lote {lote.codigo_lote} no tiene peso_neto_producido válido (>0)."
            )
        if lote.bultos.exists():
            raise BultosYaGenerados(
                f"El lote {lote.codigo_lote} ya tiene bultos generados. "
                "Use el flujo de regeneración con justificación."
            )

        config = self._resolver_config(lote)
        bultos = self._crear_bultos(lote, config, usuario)
        etiquetas = self._construir_etiquetas(lote, bultos, config)
        zpl = self._construir_zpl_unificado(etiquetas) if incluir_zpl else None

        logger.info(
            "Bultos generados para lote %s: %d bultos (config: %dx%d, tara=%s).",
            lote.codigo_lote,
            len(bultos),
            config.bultos_por_lote,
            config.unidades_por_bulto,
            config.tara_bulto,
        )
        return ResultadoEmpaque(
            bultos_generados=len(bultos),
            etiquetas=etiquetas,
            zpl_unificado=zpl,
        )

    def obtener_etiquetas(
        self, lote: LoteProduccion, incluir_zpl: bool = True
    ) -> ResultadoEmpaque:
        """
        Construye las etiquetas y ZPL desde los bultos ya persistidos.
        Útil para reimpresión sin regenerar registros.
        """
        bultos = list(
            lote.bultos.select_related(
                "lote__orden_produccion__producto",
                "lote__orden_produccion__sede",
            ).order_by("correlativo")
        )
        if not bultos:
            raise BultosYaGenerados(
                f"El lote {lote.codigo_lote} no tiene bultos generados todavía."
            )
        config = self._resolver_config(lote)
        etiquetas = self._construir_etiquetas(lote, bultos, config)
        zpl = self._construir_zpl_unificado(etiquetas) if incluir_zpl else None
        return ResultadoEmpaque(
            bultos_generados=len(bultos),
            etiquetas=etiquetas,
            zpl_unificado=zpl,
        )

    # ------------------------------------------------------------------
    # Resolución de configuración — Strategy
    # ------------------------------------------------------------------

    def _resolver_config(
        self, lote: LoteProduccion, permitir_default: bool = True
    ) -> ConfigEmpaque:
        """
        Busca ConfiguracionEmpaque en orden de especificidad decreciente:
          1. (producto, sede)
          2. (producto, sede=None)
          3. (producto=None, sede)
          4. (producto=None, sede=None)  ← global de fallback
          5. Defaults hardcoded (15×15, tara=0)  — solo si permitir_default=True
        """
        orden = lote.orden_produccion
        producto_id: Optional[int] = orden.producto_id if orden else None
        sede_id: Optional[int] = orden.sede_id if orden else None

        candidato = (
            ConfiguracionEmpaque.objects.filter(
                Q(producto_id=producto_id, sede_id=sede_id)
                | Q(producto_id=producto_id, sede__isnull=True)
                | Q(producto__isnull=True, sede_id=sede_id)
                | Q(producto__isnull=True, sede__isnull=True)
            )
            .order_by(
                Case(
                    When(producto__isnull=False, sede__isnull=False, then=Value(0)),
                    When(producto__isnull=False, sede__isnull=True, then=Value(1)),
                    When(producto__isnull=True, sede__isnull=False, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .first()
        )

        if candidato:
            return ConfigEmpaque(
                bultos_por_lote=candidato.bultos_por_lote,
                unidades_por_bulto=candidato.unidades_por_bulto,
                tara_bulto=candidato.tara_bulto,
            )

        if not permitir_default:
            raise ConfiguracionEmpaqueNoEncontrada(
                f"Sin configuración para producto={producto_id} sede={sede_id}."
            )
        logger.debug(
            "Sin ConfiguracionEmpaque para lote %s — usando defaults 15×15.",
            lote.codigo_lote,
        )
        return ConfigEmpaque(
            bultos_por_lote=15, unidades_por_bulto=15, tara_bulto=Decimal("0")
        )

    # ------------------------------------------------------------------
    # Creación de bultos
    # ------------------------------------------------------------------

    def _crear_bultos(
        self,
        lote: LoteProduccion,
        config: ConfigEmpaque,
        usuario,
    ) -> list[BultoEmpaque]:
        n = config.bultos_por_lote
        peso_total = Decimal(str(lote.peso_neto_producido))
        peso_base = (peso_total / n).quantize(_CUANTIA, rounding=ROUND_DOWN)
        # El último bulto absorbe el residuo de redondeo para preservar la suma.
        peso_ultimo = peso_total - peso_base * (n - 1)

        bultos: list[BultoEmpaque] = []
        for i in range(1, n + 1):
            peso = peso_ultimo if i == n else peso_base
            bulto = BultoEmpaque(
                lote=lote,
                correlativo=i,
                peso_neto=peso,
                unidades=config.unidades_por_bulto,
                tara=config.tara_bulto,
                impreso=False,
            )
            # Inyectar justificación para AuditableModelMixin
            bulto._justificacion_auditoria = (
                f"Generación automática para lote {lote.codigo_lote} "
                f"por {getattr(usuario, 'username', 'system')}"
            )
            bulto.save()
            bultos.append(bulto)
        return bultos

    # ------------------------------------------------------------------
    # Etiquetas y ZPL
    # ------------------------------------------------------------------

    def _construir_etiquetas(
        self,
        lote: LoteProduccion,
        bultos: list[BultoEmpaque],
        config: ConfigEmpaque,
    ) -> list[EtiquetaBulto]:
        orden = lote.orden_produccion
        producto_desc = (
            orden.producto.descripcion if orden and orden.producto else "N/A"
        )
        sede_nombre = (
            orden.sede.nombre if orden and orden.sede else "Sede Principal"
        )
        return [
            EtiquetaBulto(
                lote_codigo=lote.codigo_lote,
                bulto_correlativo=b.correlativo,
                bulto_total=config.bultos_por_lote,
                producto_descripcion=producto_desc,
                sede_nombre=sede_nombre,
                peso_neto=b.peso_neto,
                peso_bruto=b.peso_bruto,
                tara=b.tara,
                unidades=b.unidades,
                qr_data=f"https://app.texcore.com/empaque/{lote.codigo_lote}/{b.correlativo}",
            )
            for b in bultos
        ]

    def _construir_zpl_unificado(self, etiquetas: list[EtiquetaBulto]) -> Optional[str]:
        """
        Llama al microservicio printing_service para construir un único bloque
        ZPL con todas las etiquetas. Si el microservicio no está disponible,
        emite advertencia y retorna None — el frontend hará fallback local.
        """
        from gestion.utils import PrintingService

        payload = [e.to_print_payload() for e in etiquetas]
        zpl = PrintingService.generate_zpl_labels_batch(payload)
        if zpl is None:
            logger.warning(
                "ZPL masivo no disponible (printing_service caído). "
                "El frontend deberá hacer fallback con %d etiquetas individuales.",
                len(etiquetas),
            )
        return zpl
