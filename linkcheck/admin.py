"""Admin — alleen de instellingen; Link Check bewaart verder niets."""

from django import forms
from django.contrib import admin

from .compliance import available_imports, invalidate
from .models import Settings


class SettingsForm(forms.ModelForm):
    """De verplichte koppelingen als aankruislijst.

    De keuzes komen uit CharLink en staan dus niet vast: ze worden **in
    `__init__` opgebouwd**, niet op importtijd — op het moment dat dit bestand
    geladen wordt zijn de apps nog niet klaar en is de registratie leeg.

    Opslag blijft een tekstveld met komma-gescheiden ids, zodat er geen
    migratie of extra tabel nodig is.
    """

    required_imports = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=Settings._meta.get_field("required_imports").verbose_name,
        help_text=(
            "Vink aan welke koppelingen meetellen voor 'goed gekoppeld'. "
            "Niets aangevinkt = alles waar het lid recht op heeft telt mee."
        ),
    )

    class Meta:
        model = Settings
        fields = "__all__"

    class Media:
        css = {"all": ("linkcheck/admin.css",)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        gekozen = self.instance.required_list() if self.instance and self.instance.pk else []

        keuzes, bekend = [], set()
        for imp in available_imports() or []:
            key = imp.get_query_id()
            bekend.add(key)
            # Twee apps mogen dezelfde weergavenaam hebben (op deze installatie
            # heten er twee "Bedrijfsstatistieken"), dus zet het id erachter —
            # anders staan er twee identieke vinkjes.
            keuzes.append((key, f"{imp.field_label} ({key})"))

        # Een aangevinkte koppeling waarvan de app verdwenen is blijft staan,
        # met een label dat dat zegt. Stil weglaten zou de eis ongemerkt slopen.
        for key in gekozen:
            if key not in bekend:
                keuzes.append((key, f"{key} (niet meer geïnstalleerd)"))

        self.fields["required_imports"].choices = keuzes
        self.initial["required_imports"] = gekozen

        if not keuzes:
            self.fields["required_imports"].help_text = (
                "Geen koppelingen gevonden — draait CharLink wel?"
            )

    def clean_required_imports(self):
        return ",".join(self.cleaned_data["required_imports"])


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    form = SettingsForm
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
