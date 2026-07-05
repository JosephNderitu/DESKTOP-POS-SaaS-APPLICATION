from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from tenants.admin_site import tenant_admin_site
from .models import User


class PlatformUserAdmin(UserAdmin):
    """Full-access user admin for platform-level accounts (public schema only)."""
    fieldsets = UserAdmin.fieldsets + (
        ('POS Extensions', {'fields': ('role', 'phone_number', 'facial_embedding', 'assigned_terminal_id')}),
    )
    list_display = ['username', 'email', 'role', 'is_staff', 'is_superuser']


class StoreUserAdmin(UserAdmin):
    """
    Restricted user admin for store owners/managers adding cashiers.
    Deliberately excludes is_superuser and the raw permissions/groups
    fieldsets — a store admin can manage their own staff, but can't grant
    themselves or anyone else platform-level privileges from inside their
    own schema.
    """
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('POS Extensions', {'fields': ('role', 'phone_number', 'assigned_terminal_id')}),
        ('Access', {'fields': ('is_active', 'is_staff')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'is_staff', 'is_active'),
        }),
    )
    list_display = ['username', 'email', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email']


admin.site.register(User, PlatformUserAdmin)
tenant_admin_site.register(User, StoreUserAdmin)