from django.core.paginator import Paginator
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
    paginator = Paginator(entries, 25)
    page = paginator.get_page(request.GET.get("page"))
    summary = building_summary(building)
    return render(request, "ledger/ledger.html", {
        "building": building,
        "page": page,
        "entries": page.object_list,
        "summary": summary,
        "kind": kind,
        "filter_query": f"kind={kind}" if kind else "",
    })
