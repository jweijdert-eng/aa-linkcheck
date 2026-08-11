"""App Views"""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from . import __version__
from .compliance import account_detail, build_rows, invalidate

SCOPES = [
    {"key": "incomplete", "label": "Niet compleet", "color": "warning"},
    {"key": "revoked", "label": "Ingetrokken tokens", "color": "danger"},
    {"key": "all", "label": "Alle accounts", "color": "secondary"},
]


def _base(request, **extra):
    """Gedeelde context. `versie` hangt achter de CSS-URL, zodat de browser na
    een update niet op de oude stylesheet blijft zitten."""
    return {"versie": __version__, **extra}


@login_required
@permission_required("linkcheck.basic_access")
def index(request):
    """Het overzicht — voor auditors. Wie dat recht niet heeft ziet z'n eigen account."""
    if not request.user.has_perm("linkcheck.auditor"):
        return redirect("linkcheck:detail", user_id=request.user.pk)

    if request.GET.get("refresh"):
        invalidate()

    data = build_rows(force=bool(request.GET.get("refresh")))
    rows = data["rows"]

    corp_id = request.GET.get("corp") or ""
    if corp_id.isdigit():
        rows = [r for r in rows if r["corp_id"] == int(corp_id)]

    scope = request.GET.get("scope", "incomplete")
    if scope == "incomplete":
        rows = [r for r in rows if not r["complete"]]
    elif scope == "revoked":
        rows = [r for r in rows if r["revoked"]]

    # Corp-filter uit de data zelf, zodat er nooit een lege corp in de lijst staat.
    corps = sorted(
        {(r["corp_id"], r["corp_name"]) for r in data["rows"]},
        key=lambda c: c[1].lower(),
    )

    return render(request, "linkcheck/index.html", _base(
        request,
        charlink=data["charlink"],
        rows=rows,
        columns=data["columns"],
        n_total=len(data["rows"]),
        n_incomplete=data["n_incomplete"],
        n_revoked=data.get("n_revoked", 0),
        scope=scope,
        scopes=SCOPES,
        corps=corps,
        corp_id=corp_id,
        is_auditor=True,
    ))


@login_required
@permission_required("linkcheck.basic_access")
def detail(request, user_id: int):
    """Per character welke koppelingen er staan."""
    if user_id != request.user.pk and not request.user.has_perm("linkcheck.auditor"):
        raise PermissionDenied("Je mag alleen je eigen koppelstatus bekijken.")

    user = get_object_or_404(get_user_model(), pk=user_id)
    data = account_detail(user)

    return render(request, "linkcheck/detail.html", _base(
        request,
        charlink=data is not None,
        account=data,
        is_self=user_id == request.user.pk,
        is_auditor=request.user.has_perm("linkcheck.auditor"),
    ))
