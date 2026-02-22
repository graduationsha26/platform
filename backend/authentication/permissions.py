"""
Custom DRF permission classes for role-based access control.
"""
from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    """Permission class that only allows doctors."""
    message = "Only doctors can perform this action."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'doctor'
        )


class IsDoctorOrAdmin(permissions.BasePermission):
    """Permission class that allows doctors or admins."""
    message = "Only doctors or admins can perform this action."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('doctor', 'admin')
        )


class IsOwnerOrDoctor(permissions.BasePermission):
    """Permission class that allows patients to access own data or doctors to access any."""
    message = "You can only access your own data or you must be a doctor."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'doctor':
            return True
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if obj == request.user:
            return True
        return False
