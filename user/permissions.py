from rest_framework.permissions import BasePermission
from user.models import UserRole


class IsAdmin(BasePermission):
    """
    Custom permission to check if user has admin role
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            user_role = UserRole.objects.get(user=request.user)
            return user_role.role.name.lower() == 'admin'
        except UserRole.DoesNotExist:
            return False


class IsReporter(BasePermission):
    """
    Custom permission to check if user has reporter role
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            user_role = UserRole.objects.get(user=request.user)
            return user_role.role.name.lower() == 'reporter'
        except UserRole.DoesNotExist:
            return False


class IsReporterOwner(BasePermission):
    """
    Custom permission to check if user is the owner of the reporter profile
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
