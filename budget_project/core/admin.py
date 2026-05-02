"""Admin configuration for all models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Transaction, Budget, Goal, Notification, Report, Category


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("full_name",)}),
    )
    list_display = ["email", "full_name", "is_staff"]


admin.site.register(Transaction)
admin.site.register(Budget)
admin.site.register(Goal)
admin.site.register(Notification)
admin.site.register(Report)
admin.site.register(Category)
