from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from buildings.htmx import htmx_success
from buildings.models import Building, Unit
from .forms import MaintenanceRequestForm
from .models import MaintenanceRequest


def maintenance_list(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    status = request.GET.get("status") or ""
    requests = MaintenanceRequest.objects.filter(unit__building=building).select_related("unit")
    if status:
        requests = requests.filter(status=status)
    form = MaintenanceRequestForm(request.POST or None)
    form.fields["unit"].queryset = Unit.objects.filter(building=building)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.unit = form.cleaned_data["unit"]
        obj.save()
        return htmx_success("درخواست ثبت شد")
    return render(request, "maintenance/maintenance_list.html", {
        "building": building,
        "requests": requests,
        "form": form,
        "status": status,
    })


@require_POST
def maintenance_status(request, pk):
    obj = get_object_or_404(MaintenanceRequest, pk=pk)
    new_status = request.POST.get("status")
    if new_status in MaintenanceRequest.Status.values:
        obj.status = new_status
        obj.save(update_fields=["status", "updated_at"])
        return htmx_success("وضعیت به‌روزرسانی شد")
    return htmx_success("وضعیت نامعتبر است")
