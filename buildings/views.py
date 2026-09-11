from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import localdate
from django.views.decorators.http import require_POST

import jdatetime

from buildings.forms import BuildingForm, ResidentForm, UnitForm
from buildings.htmx import htmx_success
from buildings.jalali import JALALI_MONTHS
from charges.models import Charge
from expenses.models import Expense
from ledger.services import building_summary
from payments.models import Allocation
from payments.models import Payment
from payments.services import annotate_unit_balances
from .models import Building, Unit, Resident


def unit_list(request, pk):
    building = get_object_or_404(Building, pk=pk)
    units = annotate_unit_balances(building.units.all())
    return render(request, "buildings/unit_list.html", {"building": building, "units": units})


def unit_create(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    form = UnitForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        unit = form.save(commit=False)
        unit.building = building
        unit.save()
        return htmx_success("واحد ثبت شد")
    return render(request, "buildings/unit_form.html", {"form": form, "building": building})


def unit_edit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    form = UnitForm(request.POST or None, instance=unit)
    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_success("واحد ویرایش شد")
    return render(request, "buildings/unit_form.html", {"form": form, "building": unit.building, "unit": unit})


@require_POST
def unit_delete(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    if unit.charges.exclude(status=Charge.Status.CANCELLED).exists() or unit.payments.exists():
        return htmx_success("واحدی که صورتحساب یا پرداخت دارد حذف نمی‌شود")
    unit.delete()
    return htmx_success("واحد حذف شد")


def resident_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    form = ResidentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        resident = form.save(commit=False)
        resident.unit = unit
        resident.save()
        return htmx_success("ساکن ثبت شد")
    return render(request, "buildings/resident_form.html", {"form": form, "unit": unit})


def resident_edit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    form = ResidentForm(request.POST or None, instance=resident)
    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_success("اطلاعات ساکن ویرایش شد")
    return render(request, "buildings/resident_form.html", {"form": form, "unit": resident.unit, "resident": resident})


@require_POST
def resident_delete(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    resident.delete()
    return htmx_success("ساکن حذف شد")


def home(request):
    buildings = Building.objects.all()
    if buildings.count() == 1:
        return redirect("building_dashboard", pk=buildings.first().pk)
    return render(request, "buildings/home.html", {"buildings": buildings})



def building_create(request):
    form = BuildingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        building = form.save()
        response = htmx_success("ساختمان ثبت شد")
        response["HX-Redirect"] = f"/buildings/{building.pk}/"
        return response
    return render(request, "buildings/building_form.html", {"form": form})


def building_dashboard(request, pk):
    building = get_object_or_404(Building, pk=pk)
    units = annotate_unit_balances(building.units.all())
    summary = building_summary(building)

    breakdown = {"paid": 0, "partial": 0, "unpaid": 0, "none": 0}
    for unit in units:
        charged = unit.charged or Decimal("0")
        paid = unit.paid or Decimal("0")
        if charged == 0:
            breakdown["none"] += 1
        elif paid >= charged:
            breakdown["paid"] += 1
        elif paid > 0:
            breakdown["partial"] += 1
        else:
            breakdown["unpaid"] += 1

    j_today = jdatetime.date.fromgregorian(date=localdate())
    overdue = Charge.objects.filter(
        building=building,
        status__in=[Charge.Status.UNPAID, Charge.Status.PARTIAL],
    ).filter(
        year__lt=j_today.year,
    ) | Charge.objects.filter(
        building=building,
        status__in=[Charge.Status.UNPAID, Charge.Status.PARTIAL],
        year=j_today.year,
        month__lt=j_today.month,
    )
    overdue_total = sum((c.total_amount - c.paid_amount() for c in overdue), Decimal("0"))

    chart, chart_max = chart_data(building)
    return render(request, "buildings/dashboard.html", {
        "building": building,
        "units": units,
        "summary": summary,
        "breakdown": breakdown,
        "overdue_count": overdue.count(),
        "overdue_total": overdue_total,
        "chart": chart,
        "chart_max": chart_max,
    })


def chart_data(building, months=6):
    """Income vs expenses for the last N Jalali months."""
    today = jdatetime.date.fromgregorian(date=localdate())
    stack = []
    y, m = today.year, today.month
    for _ in range(months):
        stack.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    series = []
    for y, m in reversed(stack):
        start = jdatetime.date(y, m, 1).togregorian()
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        end = jdatetime.date(ny, nm, 1).togregorian()
        income = Payment.objects.filter(unit__building=building, date__gte=start, date__lt=end).aggregate(
            t=Sum("amount"))["t"] or Decimal("0")
        expense = Expense.objects.filter(building=building, date__gte=start, date__lt=end).aggregate(
            t=Sum("amount"))["t"] or Decimal("0")
        series.append({"label": JALALI_MONTHS[m - 1], "income": income, "expense": expense})
    chart_max = max((max(p["income"], p["expense"]) for p in series), default=Decimal("0"))
    for point in series:
        denom = chart_max or Decimal("1")
        point["income_pct"] = int(point["income"] / denom * 100)
        point["expense_pct"] = int(point["expense"] / denom * 100)
    return series, chart_max
