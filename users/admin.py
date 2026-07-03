from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Fieldsets define how the user editing page is grouped
    fieldsets = UserAdmin.fieldsets + (
        ('POS Extensions', {'fields': ('role', 'phone_number', 'facial_embedding', 'assigned_terminal_id')}),
    )
    list_display = ['username', 'email', 'role', 'is_staff']