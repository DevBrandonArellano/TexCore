import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TexCore.settings')
django.setup()

import traceback
from inventory.serializers import TransferenciaSerializer
from gestion.models import Bodega, Producto

try:
    producto = Producto.objects.first()
    bodegas = list(Bodega.objects.all()[:2])

    if producto and len(bodegas) >= 2:
        print(f"Testing transfer of {producto} from {bodegas[0]} to {bodegas[1]}")
        payload = {
            "producto_id": producto.id,
            "bodega_origen_id": bodegas[0].id,
            "bodega_destino_id": bodegas[1].id,
            "cantidad": 1,
            "observaciones": "Test transfer"
        }
        
        serializer = TransferenciaSerializer(data=payload)
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)
        else:
            print("Serializer Validated Data:", serializer.validated_data)
            from inventory.models import StockBodega
            from inventory.utils import safe_get_or_create_stock
            from inventory.models import MovimientoInventario
            from django.db import transaction
            
            with transaction.atomic():
                stock_origen, _ = safe_get_or_create_stock(StockBodega, bodega=bodegas[0], producto=producto)
                if stock_origen.cantidad < 1:
                    stock_origen.cantidad += 10
                    stock_origen.save()

                stock_origen = StockBodega.objects.select_for_update().get(
                    bodega=bodegas[0], producto=producto, lote=None
                )
                print(f"Stock origen before: {stock_origen.cantidad}")
                stock_origen.cantidad -= 1
                stock_origen.save()

                stock_destino, _ = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodegas[1], 
                    producto=producto, 
                    lote=None
                )
                stock_destino.cantidad += 1
                stock_destino.save()

                MovimientoInventario.objects.create(
                    tipo_movimiento='TRANSFERENCIA',
                    producto=producto,
                    cantidad=1,
                    bodega_origen=bodegas[0],
                    bodega_destino=bodegas[1],
                    lote=None,
                    usuario=None,
                    documento_ref=None,
                    observaciones="Test"
                )
                print("Transfer successful!")
    else:
        print("Not enough data to test")
except Exception as e:
    print("Exception happened:")
    traceback.print_exc()
