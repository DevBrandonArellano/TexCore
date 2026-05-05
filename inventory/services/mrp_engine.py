from django.db import transaction
from django.db.models import Sum, F, Q
from decimal import Decimal
import logging
from inventory.models import RequerimientoMaterial, OrdenCompraSugerida, StockBodega
from gestion.models import PedidoVenta, OrdenProduccion, FormulaColor, DetalleFormula, Sede

logger = logging.getLogger('inventory.mrp')

class MRPEngine:
    CONVERSION_BANOS_FUNDAS = Decimal('15')
    CONVERSION_FUNDAS_CONOS = Decimal('15')
    # 1 baño = 15 fundas * 15 conos = 225 conos
    CONVERSION_BANOS_CONOS = Decimal('225')

    def __init__(self):
        self.requerimientos_generados = 0
        self.ocs_generadas = 0
        # Cache de detalles de fórmula para evitar queries repetidas
        self._detalles_formula_cache = {}

    @transaction.atomic
    def ejecutar_mrp(self):
        """
        Ejecuta el cálculo completo del MRP:
        1. Limpia requerimientos y sugerencias previas no aprobadas.
        2. Calcula necesidades de Pedidos de Venta.
        3. Calcula necesidades de Órdenes de Producción en curso.
        4. Cruza las necesidades totales con el Stock (agrupado por Sede) y genera Órdenes de Compra Sugeridas.
        """
        logger.info("Iniciando ejecución del MRP...")
        self._limpiar_datos_previos()

        # Pre-cargar la fórmula aprobada UNA sola vez para todos los pedidos
        self._formula_default = FormulaColor.objects.filter(
            estado='aprobada'
        ).order_by('-id').first()

        sedes = Sede.objects.filter(status='activo')

        for sede in sedes:
            logger.info(f"Procesando MRP para sede: {sede.nombre}")
            reqs_bulk = []
            self._procesar_pedidos_venta(sede, reqs_bulk)
            self._procesar_ordenes_produccion(sede, reqs_bulk)
            if reqs_bulk:
                RequerimientoMaterial.objects.bulk_create(reqs_bulk, batch_size=500)
                self.requerimientos_generados += len(reqs_bulk)
            self._generar_sugerencias_compra(sede)

        logger.info(f"MRP finalizado. Requerimientos: {self.requerimientos_generados}, OCS: {self.ocs_generadas}")

    def _limpiar_datos_previos(self):
        RequerimientoMaterial.objects.all().delete()
        # Solo eliminamos las sugeridas que sigan pendientes
        OrdenCompraSugerida.objects.filter(estado='PENDIENTE').delete()

    def _procesar_pedidos_venta(self, sede, reqs_bulk):
        if not self._formula_default:
            return

        # prefetch_related evita N+1 al iterar detalles
        pedidos = PedidoVenta.objects.filter(
            sede=sede, estado='pendiente'
        ).prefetch_related('detalles')

        for pedido in pedidos:
            for detalle in pedido.detalles.all():
                cantidad_pedida = Decimal(str(detalle.cantidad))
                banos_necesarios = cantidad_pedida / self.CONVERSION_BANOS_CONOS

                self._crear_requerimientos_desde_formula(
                    formula=self._formula_default,
                    banos=banos_necesarios,
                    sede=sede,
                    origen_tipo='PEDIDO',
                    origen_id=pedido.id,
                    reqs_bulk=reqs_bulk,
                )

    def _procesar_ordenes_produccion(self, sede, reqs_bulk):
        # select_related evita query extra por cada op.formula_color
        ops = OrdenProduccion.objects.filter(
            sede=sede, estado__in=['pendiente', 'en_proceso']
        ).select_related('formula_color')

        for op in ops:
            if not op.formula_color:
                continue

            banos_necesarios = Decimal(str(op.peso_neto_requerido))

            self._crear_requerimientos_desde_formula(
                formula=op.formula_color,
                banos=banos_necesarios,
                sede=sede,
                origen_tipo='OP',
                origen_id=op.id,
                reqs_bulk=reqs_bulk,
            )

    def _get_detalles_formula(self, formula):
        """Devuelve los detalles de una fórmula usando caché en memoria."""
        if formula.id not in self._detalles_formula_cache:
            self._detalles_formula_cache[formula.id] = list(
                DetalleFormula.objects.filter(
                    fase__formula=formula
                ).select_related('producto')
            )
        return self._detalles_formula_cache[formula.id]

    def _crear_requerimientos_desde_formula(self, formula, banos, sede, origen_tipo, origen_id, reqs_bulk):
        detalles_formula = self._get_detalles_formula(formula)

        for detalle_f in detalles_formula:
            if not detalle_f.producto:
                continue

            base_por_bano = detalle_f.concentracion_gr_l or detalle_f.gramos_por_kilo or Decimal('0')
            cantidad_total = base_por_bano * banos

            if cantidad_total > 0:
                reqs_bulk.append(RequerimientoMaterial(
                    producto_requerido=detalle_f.producto,
                    cantidad_necesaria=cantidad_total,
                    sede=sede,
                    origen_tipo=origen_tipo,
                    origen_id=origen_id,
                ))

    def _generar_sugerencias_compra(self, sede):
        # Sumar los requerimientos de la sede, agrupados por producto
        requerimientos_sede = RequerimientoMaterial.objects.filter(sede=sede).values('producto_requerido').annotate(
            total_requerido=Sum('cantidad_necesaria')
        )

        if not requerimientos_sede:
            return

        producto_ids = [r['producto_requerido'] for r in requerimientos_sede]

        # Una sola query para obtener todo el stock de la sede de una vez
        stock_por_producto = {
            row['producto_id']: row['total_stock']
            for row in StockBodega.objects.filter(
                bodega__sede=sede,
                producto_id__in=producto_ids,
            ).values('producto_id').annotate(total_stock=Sum('cantidad'))
        }

        ocs_bulk = []
        for req in requerimientos_sede:
            producto_id = req['producto_requerido']
            total_req = req['total_requerido']
            stock_actual = stock_por_producto.get(producto_id) or Decimal('0')
            diferencia = total_req - stock_actual

            if diferencia > 0:
                ocs_bulk.append(OrdenCompraSugerida(
                    producto_id=producto_id,
                    sede=sede,
                    cantidad_sugerida=diferencia,
                    estado='PENDIENTE',
                    observaciones=f"Generado automáticamente por MRP. Requerido: {total_req}, Stock: {stock_actual}",
                ))

        if ocs_bulk:
            OrdenCompraSugerida.objects.bulk_create(ocs_bulk, batch_size=500)
            self.ocs_generadas += len(ocs_bulk)


def run_mrp():
    engine = MRPEngine()
    engine.ejecutar_mrp()
