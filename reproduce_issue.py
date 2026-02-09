
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TexCore.settings') # Assuming project name
django.setup()

from inventory.models import MovimientoInventario
from inventory.serializers import MovimientoInventarioSerializer
from gestion.models import Bodega, Producto, LoteProduccion
from django.contrib.auth import get_user_model

User = get_user_model()

def reproduce():
    # Fetch or create dummy data
    try:
        user = User.objects.first()
        if not user:
            print("No user found")
            return

        prod = Producto.objects.filter(pk=10001).first() # From user payload
        bodega = Bodega.objects.filter(pk=20001).first() # From user payload
        
        if not prod:
            # Create dummy product if not exists, just to test serializer
             pass
        # Actually, let's just try to validate and save with the serializer using dummy IDs if needed
        # Or better, just inspect the serializer behavior.

        data = {
            "bodega_destino": 20001,
            "cantidad": 1100,
            "documento_ref": "",
            "lote_codigo": "",
            "producto": 10001,
            "tipo_movimiento": "COMPRA"
        }
        
        print("Data:", data)
        
        # We need actual objects for FK relation if we want to run full save, 
        # but let's see if we can just spot the missing field issue.
        
        serializer = MovimientoInventarioSerializer(data=data)
        if serializer.is_valid():
            print("Serializer valid.")
            print("Validated data:", serializer.validated_data)
            
            # This is what the view does:
            # movimiento = serializer.save(usuario=user, lote=None)
            
            # Since we can't easily mock the DB save without satisfying FKs, 
            # let's look at what would be passed to create().
            
            # MovimientoInventario.objects.create(**serializer.validated_data, usuario=user, lote=None)
            
            # Check if 'saldo_resultante' is in there.
            if 'saldo_resultante' not in serializer.validated_data:
                print("ISSUE CONFIRMED: 'saldo_resultante' is missing from validated_data.")
                print("Model definition requires 'saldo_resultante'.")
            else:
                print("'saldo_resultante' is present.")
                
        else:
            print("Serializer invalid:", serializer.errors)

    except Exception as e:
        print(f"Exception during reproduction: {e}")

if __name__ == '__main__':
    reproduce()
