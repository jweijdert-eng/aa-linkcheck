"""Admin — alleen de instellingen; Link Check bewaart verder niets."""

from django.contrib import admin

from .compliance import invalidate
from .models import Settings


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("required_imports",)}),
        ("Wie telt er mee", {"fields": ("member_states", "include_guests")}),
    )

    def has_add_permission(self, request):
        # Singleton: één rij, aangemaakt door Settings.load().
        return not Settings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        invalidate()  # anders zie je de nieuwe eisen pas na 10 minuten
