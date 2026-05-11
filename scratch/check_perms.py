import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TexCore.settings')
django.setup()

from gestion.models import CustomUser, Bodega
from django.contrib.auth.models import Group

def check_permissions():
    print("Checking bodeguero permissions...")
    # Find a bodeguero
    user = CustomUser.objects.filter(groups__name='bodeguero').first()
    if not user:
        print("No user with group 'bodeguero' found.")
        return

    print(f"User: {user.username}")
    print(f"Groups: {[g.name for g in user.groups.all()]}")
    
    bodegas = user.bodegas_asignadas.all()
    print(f"Assigned Bodegas: {[b.id for b in bodegas]}")
    
    if not bodegas:
        print("User has no assigned bodegas. This is likely the problem.")
        return
        
    target_bodega = bodegas[0]
    bodega_id_str = str(target_bodega.id)
    
    # Check filter with string
    exists_str = user.bodegas_asignadas.filter(id=bodega_id_str).exists()
    print(f"Filter with string '{bodega_id_str}' exists: {exists_str}")
    
    # Check filter with int
    exists_int = user.bodegas_asignadas.filter(id=target_bodega.id).exists()
    print(f"Filter with int {target_bodega.id} exists: {exists_int}")

if __name__ == "__main__":
    check_permissions()
