from django.db import connection
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser, Material, Batch, Inventory, ProcessStep
from .serializers import (
    SedeSerializer,
    AreaSerializer,
    CustomUserSerializer,
    MaterialSerializer,
    BatchSerializer,
    InventorySerializer,
    ProcessStepSerializer,
    FormulaSerializer,
    FormulaChemicalSerializer,
    ChemicalSerializer,
    MaterialMovementSerializer,
)

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

class IndexView(APIView):
    def get(self, request):
        return Response({"message": "TexCore API is running"})

class SedeViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_sede_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_sede_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "Sede not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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

    def update(self, request, pk=None):
        serializer = SedeSerializer(data=request.data)
        if serializer.is_valid():
            nombre = serializer.validated_data.get('nombre')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_sede(%s, %s)", [pk, nombre])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_sede(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                    return Response(data[0])
                    cursor.execute("SELECT * FROM gestion_sede_view")
                    data = dictfetchall(cursor)
                return Response(data)
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
                    return Response(data[0])
                    cursor.execute("SELECT * FROM gestion_area_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AreaViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            # Get user's area_id from request (passed from frontend filter)
            area_id = request.query_params.get('area_id')
            with connection.cursor() as cursor:
                if area_id:
                    cursor.execute(
                        """
                        SELECT a.id AS area_id, a.nombre AS area_nombre, a.sede_id AS sede_id, s.nombre AS sede_nombre
                        FROM gestion_area_view a
                        JOIN gestion_sede_view s ON s.id = a.sede_id
                        WHERE a.id = %s
                        """,
                        [area_id]
                    )
                else:
                    cursor.execute(
                        """
                        SELECT a.id AS area_id, a.nombre AS area_nombre, a.sede_id AS sede_id, s.nombre AS sede_nombre
                        FROM gestion_area_view a
                        JOIN gestion_sede_view s ON s.id = a.sede_id
                        """
                    )
                rows = dictfetchall(cursor)
            data = [
                {
                    "id": row["area_id"],
                    "nombre": row["area_nombre"],
                    "sede": {"id": row["sede_id"], "nombre": row["sede_nombre"]},
                }
                for row in rows
            ]
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT a.id AS area_id, a.nombre AS area_nombre, a.sede_id AS sede_id, s.nombre AS sede_nombre
                    FROM gestion_area_view a
                    JOIN gestion_sede_view s ON s.id = a.sede_id
                    WHERE a.id = %s
                    """,
                    [pk],
                )
                rows = dictfetchall(cursor)
            if not rows:
                return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)
            row = rows[0]
            data = {
                "id": row["area_id"],
                "nombre": row["area_nombre"],
                "sede": {"id": row["sede_id"], "nombre": row["sede_nombre"]},
            }
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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

    def update(self, request, pk=None):
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

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_area(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                    return Response(data[0])
                    cursor.execute("SELECT * FROM gestion_customuser_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomUserViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            # Get user's area_id from request (passed from frontend filter)
            area_id = request.query_params.get('area_id')
            with connection.cursor() as cursor:
                if area_id:
                    cursor.execute("SELECT * FROM gestion_customuser_view WHERE area_id = %s", [area_id])
                else:
                    cursor.execute("SELECT * FROM gestion_customuser_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            # Add a /me/ endpoint to get current user details
            if pk == 'me':
                # This would need authentication middleware to get current user
                # For now, return a placeholder
                return Response({"error": "Me endpoint not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_customuser_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        payload = request.data.copy()
        superior_ids = payload.pop('superior', None)
        serializer = CustomUserSerializer(data=payload)
        if serializer.is_valid():
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
            if superior_ids is not None:
                # Accept both single id or list of ids
                if isinstance(superior_ids, str):
                    try:
                        superior_ids = [int(superior_ids)]
                    except ValueError:
                        superior_ids = []
                if isinstance(superior_ids, int):
                    superior_ids = [superior_ids]
                if isinstance(superior_ids, list):
                    user.superior.set(superior_ids)
            user.save()
            # Return fresh data from the SQL view
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM gestion_customuser_view WHERE id = %s", [user.id])
                    data = dictfetchall(cursor)
                return Response(data[0] if data else {"id": user.id}, status=status.HTTP_201_CREATED)
            except Exception:
                return Response(CustomUserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        payload = request.data.copy()
        superior_ids = payload.pop('superior', None)
        serializer = CustomUserSerializer(data=payload, partial=True)
        if serializer.is_valid():
            v_data = serializer.validated_data
            try:
                user = CustomUser.objects.get(pk=pk)
                if 'date_of_birth' in v_data:
                    user.date_of_birth = v_data['date_of_birth']
                if superior_ids is not None:
                    if isinstance(superior_ids, str):
                        try:
                            superior_ids = [int(superior_ids)]
                        except ValueError:
                            superior_ids = []
                    if isinstance(superior_ids, int):
                        superior_ids = [superior_ids]
                    if isinstance(superior_ids, list):
                        user.superior.set(superior_ids)
                user.save()
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
                # Return fresh data after update
                with connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM gestion_customuser_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                return Response(data[0] if data else serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        # Alias to update with partial=True already handled
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_user(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                    return Response(data[0])
                    cursor.execute("SELECT id, name, unit_of_measure FROM gestion_material_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MaterialViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name, unit_of_measure FROM gestion_material_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name, unit_of_measure FROM gestion_material_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "Material not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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

    def update(self, request, pk=None):
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

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_material(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                    return Response(data[0])
                    cursor.execute("SELECT id, material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received FROM gestion_batch_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BatchViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received FROM gestion_batch_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received FROM gestion_batch_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "Batch not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        serializer = BatchSerializer(data=request.data)
        if serializer.is_valid():
            material_id = serializer.validated_data.get('material').id
            code = serializer.validated_data.get('code')
            initial_quantity = serializer.validated_data.get('initial_quantity')
            current_quantity = serializer.validated_data.get('current_quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_batch(%s, %s, %s, %s, %s)", [material_id, code, initial_quantity, current_quantity, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
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

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_batch(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                    return Response(data[0])
                    cursor.execute("SELECT id, material_id, sede_id, area_id, quantity FROM gestion_inventory_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InventoryViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            # Get user's area_id from request (passed from frontend filter)
            area_id = request.query_params.get('area_id')
            with connection.cursor() as cursor:
                if area_id:
                    cursor.execute("SELECT id, material_id, sede_id, area_id, quantity FROM gestion_inventory_view WHERE area_id = %s", [area_id])
                else:
                    cursor.execute("SELECT id, material_id, sede_id, area_id, quantity FROM gestion_inventory_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, material_id, sede_id, area_id, quantity FROM gestion_inventory_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "Inventory item not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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

    def update(self, request, pk=None):
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

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_inventory(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                    return Response(data[0])
                    cursor.execute("SELECT id, name, description FROM gestion_processstep_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProcessStepViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name, description FROM gestion_processstep_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name, description FROM gestion_processstep_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "ProcessStep not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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

    def update(self, request, pk=None):
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

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_processstep(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                    return Response(data[0])
                    cursor.execute("SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id FROM gestion_materialmovement_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MaterialMovementViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            # Get user's area_id from request (passed from frontend filter)
            area_id = request.query_params.get('area_id')
            with connection.cursor() as cursor:
                if area_id:
                    cursor.execute("SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id FROM gestion_materialmovement_view WHERE to_area_id = %s OR from_area_id = %s", [area_id, area_id])
                else:
                    cursor.execute("SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id FROM gestion_materialmovement_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id FROM gestion_materialmovement_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "MaterialMovement not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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
                    cursor.execute(
                        "SELECT create_materialmovement(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        [batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, responsible_user_id]
                    )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
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
                    cursor.execute(
                        "SELECT update_materialmovement(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        [pk, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, responsible_user_id]
                    )
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_materialmovement(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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
class FormulaAPIView(APIView):
    """
    API endpoint for Formula objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all formulas or a single formula.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT * FROM gestion_formula_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "Formula not found"}, status=status.HTTP_404_NOT_FOUND)
                    return Response(data[0])
                    cursor.execute("SELECT * FROM gestion_formula_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FormulaViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_formula_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_formula_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "Formula not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        serializer = FormulaSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_formula(%s, %s)", [name, description])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        serializer = FormulaSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_formula(%s, %s, %s)", [pk, name, description])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_formula(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new formula.
        """
        serializer = FormulaSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_formula(%s, %s)", [name, description])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a formula.
        """
        serializer = FormulaSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            description = serializer.validated_data.get('description')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_formula(%s, %s, %s)", [pk, name, description])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a formula.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_formula(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FormulaChemicalAPIView(APIView):
    """
    API endpoint for FormulaChemical objects.
    """
    def get(self, request, pk=None):
        """
        Retrieve a list of all formula-chemical relationships or a single one.
        """
        try:
            with connection.cursor() as cursor:
                if pk:
                    cursor.execute("SELECT * FROM gestion_formulachemical_view WHERE id = %s", [pk])
                    data = dictfetchall(cursor)
                    if not data:
                        return Response({"error": "FormulaChemical not found"}, status=status.HTTP_404_NOT_FOUND)
                    return Response(data[0])
                    cursor.execute("SELECT * FROM gestion_formulachemical_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FormulaChemicalViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_formulachemical_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gestion_formulachemical_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "FormulaChemical not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        serializer = FormulaChemicalSerializer(data=request.data)
        if serializer.is_valid():
            formula_id = serializer.validated_data.get('formula').id
            chemical_id = serializer.validated_data.get('chemical').id
            quantity = serializer.validated_data.get('quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_formulachemical(%s, %s, %s, %s)", [formula_id, chemical_id, quantity, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        serializer = FormulaChemicalSerializer(data=request.data)
        if serializer.is_valid():
            formula_id = serializer.validated_data.get('formula').id
            chemical_id = serializer.validated_data.get('chemical').id
            quantity = serializer.validated_data.get('quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_formulachemical(%s, %s, %s, %s, %s)", [pk, formula_id, chemical_id, quantity, unit_of_measure])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_formulachemical(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Create a new formula-chemical relationship.
        """
        serializer = FormulaChemicalSerializer(data=request.data)
        if serializer.is_valid():
            formula_id = serializer.validated_data.get('formula').id
            chemical_id = serializer.validated_data.get('chemical').id
            quantity = serializer.validated_data.get('quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT create_formulachemical(%s, %s, %s, %s)", [formula_id, chemical_id, quantity, unit_of_measure])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a formula-chemical relationship.
        """
        serializer = FormulaChemicalSerializer(data=request.data)
        if serializer.is_valid():
            formula_id = serializer.validated_data.get('formula').id
            chemical_id = serializer.validated_data.get('chemical').id
            quantity = serializer.validated_data.get('quantity')
            unit_of_measure = serializer.validated_data.get('unit_of_measure')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT update_formulachemical(%s, %s, %s, %s, %s)", [pk, formula_id, chemical_id, quantity, unit_of_measure])
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a formula-chemical relationship.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_formulachemical(%s)", [pk])
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
                    return Response(data[0])
                    cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view")
                    data = dictfetchall(cursor)
                return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChemicalViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view")
                data = dictfetchall(cursor)
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, code, name, description, current_stock, unit_of_measure FROM gestion_chemical_view WHERE id = %s", [pk])
                data = dictfetchall(cursor)
            if not data:
                return Response({"error": "Chemical not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(data[0])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
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

    def update(self, request, pk=None):
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

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delete_chemical(%s)", [pk])
            return Response(status=status.HTTP_204_NO_CONTENT)
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