from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('email', 'name', 'role', 'is_active', 'is_admin', 'date_joined')
    list_filter   = ('role', 'is_active', 'is_admin')
    search_fields = ('email', 'name')
    ordering      = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        ('Account',     {'fields': ('email', 'password')}),
        ('Personal',    {'fields': ('name',)}),
        ('Role',        {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_admin')}),
        ('Timestamps',  {'fields': ('date_joined', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields' : ('email', 'name', 'role', 'password1', 'password2', 'is_active', 'is_admin'),
        }),
    )

    # Required by BaseUserAdmin
    filter_horizontal = ()

