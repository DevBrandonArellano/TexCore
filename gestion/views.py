from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser
from .serializers import SedeSerializer, AreaSerializer, CustomUserSerializer

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
                area=serializer.validated_data.get('area')
            )
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