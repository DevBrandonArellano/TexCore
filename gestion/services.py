from decimal import Decimal
from django.db import transaction

class ProduccionService:
    @staticmethod
    @transaction.atomic
    def calcular_y_empaquetar_lote(lote_produccion, peso_bruto, tara, unidades_empaque, presentacion):
        """
        Servicio para manejar la lógica de empaquetado de Lotes de Producción.
        Desacopla la lógica de negocio del modelo LoteProduccion.
        """
        if tara >= peso_bruto:
             raise ValueError("La tara no puede ser mayor o igual al peso bruto.")
             
        peso_neto = Decimal(str(peso_bruto)) - Decimal(str(tara))
        
        lote_produccion.peso_bruto = peso_bruto
        lote_produccion.tara = tara
        lote_produccion.peso_neto_producido = peso_neto
        lote_produccion.unidades_empaque = unidades_empaque
        lote_produccion.presentacion = presentacion
        lote_produccion.save()
        
        return lote_produccion
