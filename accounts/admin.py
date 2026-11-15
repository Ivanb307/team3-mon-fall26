from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied

User = get_user_model()

# Fields that decide what an account may do. Only superusers manage them (US-7.1 / #44).
ROLE_FIELDS = ('is_staff', 'is_superuser', 'groups', 'user_permissions')


class UserAdmin(BaseUserAdmin):
    """Django's user admin, limited for administrators who aren't superusers (#44).

    Administrators can view accounts and activate or deactivate participants. Everything else,
    including staff status, groups, permissions, passwords and other staff accounts, is
    superuser-only, so an administrator can't grant themselves or anyone else more access.
    """

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if request.user.is_superuser or obj is None:
            return readonly
        editable = {'is_active'}
        fields = {field for _, options in self.get_fieldsets(request, obj) for field in options['fields']}
        return tuple(readonly) + tuple(sorted((fields | set(ROLE_FIELDS)) - editable - {'password'}))

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser or obj is None:
            return fieldsets
        # The password field links to the password change form, which non-superusers can't use.
        return [
            (name, {**options, 'fields': tuple(f for f in options['fields'] if f != 'password')})
            for name, options in fieldsets
        ]

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None or request.user.is_superuser:
            return True
        # Other staff and superuser accounts are view-only for administrators.
        return obj.pk == request.user.pk or not (obj.is_staff or obj.is_superuser)

    def user_change_password(self, request, id, form_url=''):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().user_change_password(request, id, form_url)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
