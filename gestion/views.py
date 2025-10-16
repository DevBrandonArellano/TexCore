from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser, Material, Batch, Inventory, ProcessStep
from .serializers import SedeSerializer, AreaSerializer, CustomUserSerializer, MaterialSerializer, BatchSerializer, InventorySerializer, ProcessStepSerializer

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

class SedeAPIView(APIView):
    """
    API endpoint for Sede objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all sedes or a single sede.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT * FROM gestion_sede_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Sede not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = SedeSerializer(data[0])
                else:
                    cursor.execute("SELECT * FROM gestion_sede_view")
                    data = dictfetchall(cursor)
                    serializer = SedeSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new sede.
        """
        serializer = SedeSerializer(data=request.data)
        if serializer.is_valid():
            nombre = serializer.validated_data.get('nombre')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_sede(%s)", [nombre])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a sede.
        """
        serializer = SedeSerializer(data=request.data)
        if serializer.is_valid():
            nombre = serializer.validated_data.get('nombre')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_sede(%s, %s)", [pk, nombre])
                # We return the validated data because the SP doesn't return the object
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a sede.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_sede(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AreaAPIView(APIView):
    """
    API endpoint for Area objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all areas or a single area.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT * FROM gestion_area_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = AreaSerializer(data[0])
                else:
                    cursor.execute("SELECT * FROM gestion_area_view")
                    data = dictfetchall(cursor)
                    serializer = AreaSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new area.
        """
        serializer = AreaSerializer(data=request.data)
        if serializer.is_valid():
            nombre = serializer.validated_data.get('nombre')
            sede_id = serializer.validated_data.get('sede').id
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_area(%s, %s)", [nombre, sede_id])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an area.
        """
        serializer = AreaSerializer(data=request.data)
        if serializer.is_valid():
            nombre = serializer.validated_data.get('nombre')
            sede_id = serializer.validated_data.get('sede').id
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_area(%s, %s, %s)", [pk, nombre, sede_id])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete an area.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_area(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomUserAPIView(APIView):
    """
    API endpoint for CustomUser objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all users or a single user.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT * FROM gestion_customuser_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = CustomUserSerializer(data[0])
                else:
                    cursor.execute("SELECT * FROM gestion_customuser_view")
                    data = dictfetchall(cursor)
                    serializer = CustomUserSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new user with a securely hashed password.
        """
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            # Use Django's create_user to handle password hashing
            user = CustomUser.objects.create_user(
                username=serializer.validated_data['username'],
                email=serializer.validated_data.get('email', ''),
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                sede=serializer.validated_data.get('sede'),
                area=serializer.validated_data.get('area'),
                date_of_birth=serializer.validated_data.get('date_of_birth')
            )
            if 'superior' in serializer.validated_data:
                user.superior.set(serializer.validated_data['superior'])
            user.save() # Save to update superior relationship
            # Return the created user data (excluding password)
            return Response(CustomUserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a user's profile data (password is not changed here).
        """
        # We don't need a full serializer validation if we only update specific fields
        # and call a SP. However, it's good practice to validate the incoming data.
        serializer = CustomUserSerializer(data=request.data, partial=True) # partial=True allows not providing all fields
        if serializer.is_valid():
            v_data = serializer.validated_data
            try:
                user = CustomUser.objects.get(pk=pk)

                # Update date_of_birth if provided
                if 'date_of_birth' in v_data:
                    user.date_of_birth = v_data['date_of_birth']

                # Update superior relationship if provided
                if 'superior' in v_data:
                    user.superior.set(v_data['superior'])
                
                user.save() # Save user object to persist date_of_birth and superior changes

                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT update_user(%s, %s, %s, %s, %s, %s)",
                        [
                            pk,
                            v_data.get('first_name'),
                            v_data.get('last_name'),
                            v_data.get('email'),
                            v_data.get('sede').id if v_data.get('sede') else None,
                            v_data.get('area').id if v_data.get('area') else None,
                        ]
                    )
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Deactivate a user.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_user(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MaterialAPIView(APIView):
    """
    API endpoint for Material objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all materials or a single material.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, name, unit_of_measure FROM gestion_material_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Material not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = MaterialSerializer(data[0])
                else:
                    cursor.execute("SELECT id, name, unit_of_measure FROM gestion_material_view")
                    data = dictfetchall(cursor)
                    serializer = MaterialSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new material.
        """
        serializer = MaterialSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_material(%s, %s)", [name, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a material.
        """
        serializer = MaterialSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_material(%s, %s, %s)", [pk, name, unit_of_measure])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a material.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_material(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BatchAPIView(APIView):
    """
    API endpoint for Batch objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all batches or a single batch.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received FROM gestion_batch_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Batch not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = BatchSerializer(data[0])
                else:
                    cursor.execute("SELECT id, material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received FROM gestion_batch_view")
                    data = dictfetchall(cursor)
                    serializer = BatchSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new batch.
        """
        serializer = BatchSerializer(data=request.data)
        if serializer.is_valid():
            material_id = serializer.validated_data.get('material').id
            code = serializer.validated_data.get('code')
            initial_quantity = serializer.validated_data.get('initial_quantity')
            current_quantity = serializer.validated_data.get('current_quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            # date_received is auto_now_add, so not passed here
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_batch(%s, %s, %s, %s, %s)", [material_id, code, initial_quantity, current_quantity, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a batch.
        """
        serializer = BatchSerializer(data=request.data)
        if serializer.is_valid():
            material_id = serializer.validated_data.get('material').id
            code = serializer.validated_data.get('code')
            initial_quantity = serializer.validated_data.get('initial_quantity')
            current_quantity = serializer.validated_data.get('current_quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_batch(%s, %s, %s, %s, %s, %s)", [pk, material_id, code, initial_quantity, current_quantity, unit_of_measure])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a batch.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_batch(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InventoryAPIView(APIView):
    """
    API endpoint for Inventory objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all inventory items or a single inventory item.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, material_id, sede_id, area_id, quantity FROM gestion_inventory_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Inventory item not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = InventorySerializer(data[0])
                else:
                    cursor.execute("SELECT id, material_id, sede_id, area_id, quantity FROM gestion_inventory_view")
                    data = dictfetchall(cursor)
                    serializer = InventorySerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new inventory item.
        """
        serializer = InventorySerializer(data=request.data)
        if serializer.is_valid():
            material_id = serializer.validated_data.get('material').id
            sede_id = serializer.validated_data.get('sede').id
            area_id = serializer.validated_data.get('area').id
            quantity = serializer.validated_data.get('quantity')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_inventory(%s, %s, %s, %s)", [material_id, sede_id, area_id, quantity])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an inventory item.
        """
        serializer = InventorySerializer(data=request.data)
        if serializer.is_valid():
            material_id = serializer.validated_data.get('material').id
            sede_id = serializer.validated_data.get('sede').id
            area_id = serializer.validated_data.get('area').id
            quantity = serializer.validated_data.get('quantity')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_inventory(%s, %s, %s, %s, %s)", [pk, material_id, sede_id, area_id, quantity])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete an inventory item.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_inventory(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProcessStepAPIView(APIView):
    """
    API endpoint for ProcessStep objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all process steps or a single process step.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, name, description FROM gestion_processstep_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "ProcessStep not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = ProcessStepSerializer(data[0])
                else:
                    cursor.execute("SELECT id, name, description FROM gestion_processstep_view")
                    data = dictfetchall(cursor)
                    serializer = ProcessStepSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new process step.
        """
        serializer = ProcessStepSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_processstep(%s, %s)", [name, description])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a process step.
        """
        serializer = ProcessStepSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_processstep(%s, %s, %s)", [pk, name, description])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a process step.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_processstep(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MaterialMovementAPIView(APIView):
    """
    API endpoint for MaterialMovement objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all material movements or a single material movement.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id FROM gestion_materialmovement_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "MaterialMovement not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = MaterialMovementSerializer(data[0])
                else:
                    cursor.execute("SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id FROM gestion_materialmovement_view")
                    data = dictfetchall(cursor)
                    serializer = MaterialMovementSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new material movement.
        """
        serializer = MaterialMovementSerializer(data=request.data)
        if serializer.is_valid():
            batch_id = serializer.validated_data.get('batch').id
            from_sede_id = serializer.validated_data.get('from_sede').id if serializer.validated_data.get('from_sede') else None
            from_area_id = serializer.validated_data.get('from_area').id if serializer.validated_data.get('from_area') else None
            to_sede_id = serializer.validated_data.get('to_sede').id
            to_area_id = serializer.validated_data.get('to_area').id
            process_step_id = serializer.validated_data.get('process_step').id
            quantity = serializer.validated_data.get('quantity')
            movement_type = serializer.validated_data.get('movement_type')
            responsible_user_id = serializer.validated_data.get('responsible_user').id
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_materialmovement(%s, %s, %s, %s, %s, %s, %s, %s, %s)", [batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, responsible_user_id])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a material movement.
        """
        serializer = MaterialMovementSerializer(data=request.data)
        if serializer.is_valid():
            batch_id = serializer.validated_data.get('batch').id
            from_sede_id = serializer.validated_data.get('from_sede').id if serializer.validated_data.get('from_sede') else None
            from_area_id = serializer.validated_data.get('from_area').id if serializer.validated_data.get('from_area') else None
            to_sede_id = serializer.validated_data.get('to_sede').id
            to_area_id = serializer.validated_data.get('to_area').id
            process_step_id = serializer.validated_data.get('process_step').id
            quantity = serializer.validated_data.get('quantity')
            movement_type = serializer.validated_data.get('movement_type')
            responsible_user_id = serializer.validated_data.get('responsible_user').id
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_materialmovement(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", [pk, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, responsible_user_id])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a material movement.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_materialmovement(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChemicalAPIView(APIView):
    """
    API endpoint for Chemical objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all chemicals or a single chemical.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Chemical not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = ChemicalSerializer(data[0])
                else:
                    cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view")
                    data = dictfetchall(cursor)
                    serializer = ChemicalSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new chemical.
        """
        serializer = ChemicalSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data.get('code')
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            current_stock = serializer.validated_data.get('current_stock')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_chemical(%s, %s, %s, %s, %s)", [code, name, description, current_stock, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a chemical.
        """
        serializer = ChemicalSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data.get('code')
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            current_stock = serializer.validated_data.get('current_stock')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_chemical(%s, %s, %s, %s, %s, %s)", [pk, code, name, description, current_stock, unit_of_measure])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a chemical.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_chemical(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChemicalAPIView(APIView):
    """
    API endpoint for Chemical objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all chemicals or a single chemical.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Chemical not found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = ChemicalSerializer(data[0])
                else:
                    cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view")
                    data = dictfetchall(cursor)
                    serializer = ChemicalSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new chemical.
        """
        serializer = ChemicalSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data.get('code')
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            current_stock = serializer.validated_data.get('current_stock')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_chemical(%s, %s, %s, %s, %s)", [code, name, description, current_stock, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a chemical.
        """
        serializer = ChemicalSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data.get('code')
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            current_stock = serializer.validated_data.get('current_stock')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_chemical(%s, %s, %s, %s, %s, %s)", [pk, code, name, description, current_stock, unit_of_measure])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a chemical.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_chemical(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)