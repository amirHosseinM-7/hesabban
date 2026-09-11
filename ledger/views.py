from django.shortcuts import get_object_or_404, render

from buildings.models import Building
from ledger.services import building_summary
from .models import LedgerEntry


def ledger_list(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    kind = request.GET.get("kind") or ""
    entries = building.ledger_entries.select_related("content_type")
    if kind:
        entries = entries.filter(kind=kind)
    summary = building_summary(building)
    return render(request, "ledger/ledger.html", {
        "building": building,
        "entries": entries,
        "summary": summary,
        "kind": kind,
    })
