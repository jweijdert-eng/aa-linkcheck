"""
Is elk account netjes met het systeem gekoppeld?

CharLink houdt al bij wélke apps een ESI-token nodig hebben en of een character
daar in zit: elke `LoginImport` levert een `is_character_added_annotation`
(een Django `Exists`) die je op een EveCharacter-queryset kunt hangen. Die
registratie hergebruiken we hier — één kruistabel met een rij per AA-account en
een kolom per koppeling. CharLink zelf heeft alleen een ledenlijst per corp en
een pagina per account; het corp-brede overzicht ontbreekt daar.

Alles is soft: staat CharLink niet geïnstalleerd, dan geeft `available_imports()`
None terug en toont de pagina een uitleg in plaats van te klappen.

Twee dingen die een koppeling stuk maken en die we apart tellen:

* **niet gekoppeld** — het character zit niet in de app (geen token met de juiste
  scopes)
* **ingetrokken** — er ligt nog een tokenrij, maar zonder `refresh_token`. Dat
  gebeurt als iemand z'n toestemming op de EVE-site intrekt. De app denkt dan
  dat het character gekoppeld is terwijl er niets meer op te halen valt; zonder
  deze check ziet zo'n account er groen uit.
"""

from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.cache import cache

from allianceauth.eveonline.models import EveCharacter

from .models import Settings

# Achtervoegsel meebumpen zodra de vorm van een rij verandert, anders blijft er
# na een update tot 10 minuten een oude rij in de cache zitten zonder de nieuwe
# velden.
CACHE_KEY = "linkcheck_rows_v2"
CACHE_SECONDS = 600  # 10 min; de "Ververs"-knop omzeilt dit


# ── CharLink-registratie ─────────────────────────────────────────────────────
def available_imports():
    """Alle zichtbare CharLink-koppelingen, of None als CharLink ontbreekt.

    Koppelingen die een beheerder in CharLink op "verborgen" heeft gezet laten
    we weg — die tellen daar ook niet mee bij het koppelen.
    """
    try:
        from charlink.app_imports import import_apps
    except Exception:  # noqa: BLE001 — CharLink niet geïnstalleerd
        return None

    try:
        apps = import_apps()
    except Exception:  # noqa: BLE001 — kapotte registratie mag ons niet slopen
        return None

    imports = []
    for app_import in apps.values():
        for imp in app_import.imports:
            try:
                if imp.is_ignored:
                    continue
            except Exception:  # noqa: BLE001 — geen AppSettings-rij: gewoon tonen
                pass
            imports.append(imp)

    # AA's eigen login eerst (dat is de basis), daarna alfabetisch.
    imports.sort(key=lambda i: (
        i.app_label != "allianceauth.authentication", str(i.field_label).lower()
    ))
    return imports


def columns(imports, required_keys):
    """Kolomkoppen voor de tabel."""
    return [
        {
            "key": imp.get_query_id(),
            "label": str(imp.field_label),
            "app": imp.app_label,
            "scopes": list(imp.scopes),
            "n_scopes": len(imp.scopes),
            "required": (not required_keys) or imp.get_query_id() in required_keys,
        }
        for imp in imports
    ]


def _may(imp, user):
    """Geldt deze koppeling voor dit account? (Corp Audit e.d. alleen voor directors.)"""
    try:
        return bool(imp.check_permissions(user))
    except Exception:  # noqa: BLE001 — een kapotte check telt als 'niet van toepassing'
        return False


# ── Tokens ───────────────────────────────────────────────────────────────────
def _token_state(character_ids):
    """(characters met een token, characters waarvan élk token ingetrokken is)."""
    try:
        from esi.models import Token
    except Exception:  # noqa: BLE001 — django-esi hoort er te zijn
        return set(), set()

    with_token, alive = set(), set()
    if character_ids:
        rows = Token.objects.filter(character_id__in=character_ids).values_list(
            "character_id", "refresh_token"
        )
        for cid, refresh in rows:
            with_token.add(cid)
            if refresh:
                alive.add(cid)

    return with_token, with_token - alive


# ── Accounts ─────────────────────────────────────────────────────────────────
def _member_users(conf):
    """Elk account met een main character, gefilterd op state."""
    users = (
        get_user_model().objects
        .filter(profile__main_character__isnull=False)
        .select_related("profile__main_character", "profile__state")
    )

    wanted = [s.lower() for s in conf.state_list()]
    result = []
    for user in users:
        state = getattr(getattr(user, "profile", None), "state", None)
        name = (getattr(state, "name", "") or "").lower()
        if wanted:
            if name not in wanted:
                continue
        elif name == "guest" and not conf.include_guests:
            continue
        result.append(user)
    return result


def _state_kind(name: str) -> str:
    """Kleurgroep voor de state-kolom.

    Alleen Guest en Member krijgen een kleur; een eigen state (Blue, Corporation,
    …) blijft neutraal in plaats van een willekeurige kleur te pakken.
    """
    lowered = (name or "").strip().lower()
    if lowered == "guest":
        return "guest"
    if lowered == "member":
        return "member"
    return "other"


def _cell(key, label, linked, total, unlinked, required, na=False):
    return {
        "key": key,
        "label": label,
        "linked": linked,
        "total": total,
        "unlinked": unlinked,
        "ok": (not na) and total > 0 and linked == total,
        "partial": (not na) and 0 < linked < total,
        "na": na,
        "required": required,
    }


def build_rows(force=False):
    """De kruistabel: kolommen + één rij per account.

    Het resultaat hangt niet af van wie er kijkt (alleen van de accounts zelf),
    dus het is één keer per 10 minuten berekenen en voor iedereen hergebruiken.
    """
    if not force:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached

    imports = available_imports()
    if imports is None:
        return {"charlink": False, "rows": [], "columns": [], "n_incomplete": 0}

    from charlink.utils import chars_annotate_linked_apps

    conf = Settings.load()
    required_keys = set(conf.required_list())
    # Heeft een beheerder koppelingen aangevinkt, dan tonen we alléén die —
    # de rest is ruis in een tabel die toch al breed is. Zonder selectie telt
    # alles mee en staat dus ook alles in beeld.
    cols = [c for c in columns(imports, required_keys) if c["required"]]
    users = _member_users(conf)
    user_ids = [u.pk for u in users]

    # Eén query met per koppeling een Exists-subquery erbij.
    chars = list(chars_annotate_linked_apps(
        EveCharacter.objects
        .filter(character_ownership__user__in=user_ids)
        .select_related("character_ownership"),
        imports,
    ))

    per_user = defaultdict(list)
    for char in chars:
        per_user[char.character_ownership.user_id].append(char)

    _with_token, revoked_ids = _token_state([c.character_id for c in chars])

    rows = []
    for user in users:
        user_chars = sorted(per_user.get(user.pk, []), key=lambda c: c.character_name)
        total = len(user_chars)
        applicable = {imp.get_query_id() for imp in imports if _may(imp, user)}

        cells, missing, done, counted = [], [], 0, 0
        for col in cols:
            key = col["key"]
            if key not in applicable:
                cells.append(_cell(key, col["label"], 0, total, [], col["required"], na=True))
                continue

            unlinked = [c.character_name for c in user_chars if not getattr(c, key, False)]
            linked = total - len(unlinked)
            cell = _cell(key, col["label"], linked, total, unlinked, col["required"])
            cells.append(cell)

            if cell["required"]:
                counted += 1
                if cell["ok"]:
                    done += 1
                else:
                    missing.append(col["label"])

        revoked = sorted(c.character_name for c in user_chars if c.character_id in revoked_ids)
        main = user.profile.main_character
        rows.append({
            "user_id": user.pk,
            "username": user.username,
            "main_id": main.character_id,
            "main_name": main.character_name,
            "corp_id": main.corporation_id,
            "corp_name": main.corporation_name or "",
            "alliance_name": main.alliance_name or "",
            "state": getattr(getattr(user.profile, "state", None), "name", "") or "",
            "state_kind": _state_kind(
                getattr(getattr(user.profile, "state", None), "name", "")),
            "n_chars": total,
            "cells": cells,
            "revoked": revoked,
            "missing": missing,
            "done": done,
            "total_checks": counted,
            "pct": int(round(done / counted * 100)) if counted else 0,
            "complete": counted > 0 and done == counted and not revoked,
        })

    # Wie iets open heeft staan bovenaan, daarna de slechtste score eerst.
    rows.sort(key=lambda r: (r["complete"], r["pct"], r["main_name"].lower()))

    result = {
        "charlink": True,
        "rows": rows,
        "columns": cols,
        "n_incomplete": sum(1 for r in rows if not r["complete"]),
        "n_revoked": sum(1 for r in rows if r["revoked"]),
    }
    cache.set(CACHE_KEY, result, CACHE_SECONDS)
    return result


def account_detail(user):
    """Per character welke koppelingen er staan — voor de detailpagina."""
    imports = available_imports()
    if imports is None:
        return None

    from charlink.utils import chars_annotate_linked_apps

    conf = Settings.load()
    required_keys = set(conf.required_list())
    mag = {i.get_query_id() for i in imports if _may(i, user)}
    cols = [c for c in columns(imports, required_keys)
            if c["required"] and c["key"] in mag]

    chars = list(chars_annotate_linked_apps(
        EveCharacter.objects.filter(character_ownership__user=user), imports
    ))
    chars.sort(key=lambda c: c.character_name)

    _with_token, revoked_ids = _token_state([c.character_id for c in chars])

    main = getattr(getattr(user, "profile", None), "main_character", None)
    rows = []
    for char in chars:
        cells = [{
            "key": c["key"],
            "label": c["label"],
            "linked": bool(getattr(char, c["key"], False)),
            "required": c["required"],
        } for c in cols]
        rows.append({
            "character_id": char.character_id,
            "name": char.character_name,
            "corp_name": char.corporation_name or "",
            "alliance_name": char.alliance_name or "",
            "is_main": bool(main) and char.character_id == main.character_id,
            "revoked": char.character_id in revoked_ids,
            "cells": cells,
            "n_linked": sum(1 for c in cells if c["linked"]),
            "n_total": len(cells),
        })

    return {
        "user_id": user.pk,
        "username": user.username,
        "main_name": main.character_name if main else user.username,
        "main_id": main.character_id if main else None,
        "state": getattr(getattr(user, "profile", None), "state", None),
        "columns": cols,
        "characters": rows,
    }


def invalidate():
    """Gooi de gecachte tabel weg (Ververs-knop, of na een instellingswijziging)."""
    cache.delete(CACHE_KEY)
