from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    PortalUserMapping, UserCategoryGroupAssignment, UserRole, Role, UserPortalAssignment
)

@admin.register(PortalUserMapping)
class PortalUserMappingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'portal', 'portal_user_id', 'status']
    search_fields =['id', 'user', 'portal', 'portal_user_id', 'status']
    list_filter = ['id', 'user', 'portal', 'portal_user_id', 'status']


@admin.register(UserCategoryGroupAssignment)
class UserCategoryGroupAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'group', 'master_category']
    search_fields =['id', 'user', 'group', 'master_category']
    list_filter = ['id', 'user', 'group', 'master_category']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    ist_display = ['id', 'user', 'role']
    search_fields = ['id', 'user', 'role']
    list_filter = ['id', 'user', 'role']
    

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['id', 'name']
    list_filter = ['id', 'name']


admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("id",)
    
@admin.register(UserPortalAssignment)
class UserPortalAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'portal']
    search_fields = ['id', 'user', 'portal']
    list_filter =  ['id', 'user', 'portal']
