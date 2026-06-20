"""
Authentication views: registration, login, token refresh.
"""
from django.db.models import Count, Q
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import CustomUser
from .permissions import IsAdmin
from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    DoctorListSerializer,
    DoctorWriteSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.
    POST /api/auth/register/
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    JWT login endpoint with custom serializer.
    POST /api/auth/login/
    Returns: access token, refresh token, and user data.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    """
    Current user profile endpoint.
    GET /api/auth/me/
    Returns the authenticated doctor's profile including first_name and last_name.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class AdminDoctorListCreateView(generics.ListCreateAPIView):
    """
    Admin doctor roster + creation (Feature 047).

    GET  /api/admin/doctors/  — paginated list of doctor accounts, each
                                annotated with patient_count.
    POST /api/admin/doctors/  — create a new doctor account.

    Access Control: admin only.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = (
            CustomUser.objects.filter(role='doctor')
            .annotate(patient_count=Count('patient_assignments', distinct=True))
            .order_by('first_name', 'last_name', 'id')
        )
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DoctorWriteSerializer
        return DoctorListSerializer


class AdminDoctorDetailView(generics.RetrieveUpdateAPIView):
    """
    Admin doctor detail: update details or toggle active status (Feature 047).

    GET   /api/admin/doctors/<id>/  — retrieve a single doctor.
    PATCH /api/admin/doctors/<id>/  — update details and/or toggle is_active.

    No PUT/DELETE — accounts are never hard-deleted (status lifecycle only).
    Access Control: admin only.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        return (
            CustomUser.objects.filter(role='doctor')
            .annotate(patient_count=Count('patient_assignments', distinct=True))
        )

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return DoctorWriteSerializer
        return DoctorListSerializer
