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
        
        sedes = Sede.objects.filter(status='activo')
        
        for sede in sedes:
            logger.info(f"Procesando MRP para sede: {sede.nombre}")
            self._procesar_pedidos_venta(sede)
            self._procesar_ordenes_produccion(sede)
            self._generar_sugerencias_compra(sede)
            
        logger.info(f"MRP finalizado. Requerimientos: {self.requerimientos_generados}, OCS: {self.ocs_generadas}")

    def _limpiar_datos_previos(self):
        RequerimientoMaterial.objects.all().delete()
        # Solo eliminamos las sugeridas que sigan pendientes
        OrdenCompraSugerida.objects.filter(estado='PENDIENTE').delete()

    def _procesar_pedidos_venta(self, sede):
        # Pedidos pendientes no despachados
        pedidos = PedidoVenta.objects.filter(sede=sede, estado='pendiente')
        
        for pedido in pedidos:
            for detalle in pedido.detalles.all():
                # Regla: 300 conos pedidos -> calculamos cuántos baños.
                # Si piden 300 conos: 300 / 225 = 1.333 baños correspondientes a fabricar
                # Asumimos que los detalles del pedido son siempre la presentacion minima (conos)
                # En un caso real se ajustaría según `detalle.producto.unidad_medida` o presentación.
                
                # Buscamos si el producto tiene una fórmula de color activa o la más reciente.
                # TODO: Mapear la fórmula al producto o sustrato específico.
                formula = FormulaColor.objects.filter(estado='aprobada').order_by('-id').first()
                if not formula:
                    # Si no hay fórmula, es un producto directo o no necesita químicos
                    continue
                
                cantidad_pedida = Decimal(str(detalle.cantidad))
                banos_necesarios = cantidad_pedida / self.CONVERSION_BANOS_CONOS
                
                self._crear_requerimientos_desde_formula(
                    formula=formula,
                    banos=banos_necesarios,
                    sede=sede,
                    origen_tipo='PEDIDO',
                    origen_id=pedido.id
                )

    def _procesar_ordenes_produccion(self, sede):
        # OPs en curso o pendientes
        ops = OrdenProduccion.objects.filter(sede=sede, estado__in=['pendiente', 'en_proceso'])
        
        for op in ops:
            if not op.formula_color:
                continue
                
            # Dependiendo de la unidad de la OP (peso o baños), convertimos a baños.
            # Asumimos que la OP indica los "baños" o un factor equivalente en peso.
            # Si peso_neto_requerido representa los baños a hacer:
            banos_necesarios = Decimal(str(op.peso_neto_requerido))
            
            self._crear_requerimientos_desde_formula(
                formula=op.formula_color,
                banos=banos_necesarios,
                sede=sede,
                origen_tipo='OP',
                origen_id=op.id
            )

    def _crear_requerimientos_desde_formula(self, formula, banos, sede, origen_tipo, origen_id):
        detalles_formula = DetalleFormula.objects.filter(fase__formula=formula)
        
        for detalle_f in detalles_formula:
            if not detalle_f.producto:
                continue
            
            # Calculamos la necesidad: Concentración/Porcentaje * Baños (Factor)
            # Para simplificar, asumimos que gramos_por_kilo o concentracion_gr_l es la base por 1 baño
            base_por_bano = detalle_f.concentracion_gr_l or detalle_f.gramos_por_kilo or Decimal('0')
            cantidad_total = base_por_bano * banos
            
            if cantidad_total > 0:
                RequerimientoMaterial.objects.create(
                    producto_requerido=detalle_f.producto,
                    cantidad_necesaria=cantidad_total,
                    sede=sede,
                    origen_tipo=origen_tipo,
                    origen_id=origen_id
                )
                self.requerimientos_generados += 1

    def _generar_sugerencias_compra(self, sede):
        # Sumar los requerimientos de la sede, agrupados por producto
        requerimientos_sede = RequerimientoMaterial.objects.filter(sede=sede).values('producto_requerido').annotate(
            total_requerido=Sum('cantidad_necesaria')
        )
        
        for req in requerimientos_sede:
            producto_id = req['producto_requerido']
            total_req = req['total_requerido']
            
            # Sumar el stock actual de este producto en todas las bodegas de la sede
            # Alternativa: usar el Stored Procedure `sp_GetKardexBodega` u otra view.
            # stock_actual = sp_GetStockAgrupadoPorSede(...)
            stock_actual = StockBodega.objects.filter(
                bodega__sede=sede, 
                producto_id=producto_id
            ).aggregate(total_stock=Sum('cantidad'))['total_stock'] or Decimal('0')
            
            diferencia = total_req - stock_actual
            
            if diferencia > 0:
                OrdenCompraSugerida.objects.create(
                    producto_id=producto_id,
                    sede=sede,
                    cantidad_sugerida=diferencia,
                    estado='PENDIENTE',
                    observaciones=f"Generado automáticamente por MRP. Requerido: {total_req}, Stock: {stock_actual}"
                )
                self.ocs_generadas += 1

def run_mrp():
    engine = MRPEngine()
    engine.ejecutar_mrp()
