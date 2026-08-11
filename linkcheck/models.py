"""
App Models

Link Check slaat zelf geen character-gegevens op — alles komt live uit CharLink
en django-esi. Er is dus alleen een permissie-model en één instellingen-rij.
"""

import re

from django.db import models
from django.utils.translation import gettext_lazy as _


class General(models.Model):
    """Meta model voor de app-permissies."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", _("Can access this app (eigen koppelstatus)")),
            ("auditor", _("Can view the link status of all members")),
        )


class Settings(models.Model):
    """Eén rij met plugin-instellingen, bewerkbaar via het admin-paneel."""

    required_imports = models.TextField(
        blank=True, default="", verbose_name=_("Verplichte koppelingen"),
        help_text=_(
            "Welke CharLink-koppelingen meetellen voor 'goed gekoppeld' — één id per "
            "regel, precies zoals op de pagina onder een kolomkop staat "
            "(bijv. memberaudit_default). Leeg = alles waar het lid recht op heeft."
        ),
    )
    member_states = models.TextField(
        blank=True, default="", verbose_name=_("Alleen deze states"),
        help_text=_(
            "Namen van AA-states die op het overzicht horen — één per regel of "
            "komma-gescheiden (bijv. Member). Leeg = elk account met een main, "
            "behalve Guest."
        ),
    )
    include_guests = models.BooleanField(
        default=False, verbose_name=_("Guests meetellen"),
        help_text=_("Aan: accounts in de state Guest ook op het overzicht zetten."),
    )

    class Meta:
        default_permissions = ()
        permissions = (("manage_settings", _("Can manage Link Check settings")),)
        verbose_name = _("instellingen")
        verbose_name_plural = _("instellingen")

    def __str__(self) -> str:
        return "Link Check instellingen"

    @staticmethod
    def _split(text):
        """Splitst op regel of komma — nooit op spatie, want zowel state- als
        koppelnamen bevatten spaties."""
        return [t.strip() for t in re.split(r"[\r\n,]+", text or "") if t.strip()]

    def required_list(self):
        return self._split(self.required_imports)

    def state_list(self):
        return self._split(self.member_states)

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "Settings":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
