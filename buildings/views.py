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
from payments.models import Payment
from payments.services import annotate_unit_balances
from .models import Building, Unit, Resident


def probe(request):
    """TEMPORARY debug aid: render a target path in an iframe and measure
    horizontal overflow at the current viewport width."""
    from django.http import HttpResponse
    import html as _html
    target = _html.escape(request.GET.get("u", "/buildings/4/"))
    return HttpResponse(f"""<!doctype html><html lang="fa"><meta charset="utf-8">
<body style="margin:0;background:#fff;font-family:monospace">
<div id="out"></div>
<iframe id="f" src="{target}" style="width:100%;height:1000px;border:0"></iframe>
<script>
const out=document.getElementById('out');const f=document.getElementById('f');
function measure(){{try{{const d=f.contentDocument;const de=d.documentElement;
const sw=de.scrollWidth,iw=de.clientWidth;
out.textContent='path='+JSON.stringify({chr(34)}{chr(34)})+
' viewport='+iw+' scrollWidth='+sw+' OVERFLOW_X='+(sw>iw+1);
let bad=[];for(const el of ['.app','.topbar','.content','.tabbar','.stat-grid','.chart','.table-wrap']){{
const e=d.querySelector(el);if(e){{const r=e.getBoundingClientRect();if(r.right>iw+1||r.left< -1)bad.push(el+' r='+Math.round(r.right));}}}}
out.textContent+=(' wide_els='+JSON.stringify(bad));
}}catch(e){{out.textContent+=' ERR '+e;}}}}
f.addEventListener('load',()=>setTimeout(measure,1500));
</script></body></html>""")


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


def building_years(building):
    """All Jalali years that have charges or expenses, newest first."""
    years = set(
        building.charges.exclude(status=Charge.Status.CANCELLED).values_list("year", flat=True)
    )
    for date in building.expenses.values_list("date", flat=True):
        years.add(jdatetime.date.fromgregorian(date=date).year)
    for date in Payment.objects.filter(unit__building=building).values_list("date", flat=True):
        years.add(jdatetime.date.fromgregorian(date=date).year)
    return sorted(years, reverse=True)


def _jalali_year_range(year):
    start = jdatetime.date(year, 1, 1).togregorian()
    end = jdatetime.date(year + 1, 1, 1).togregorian()
    return start, end


def annual_summary(building, year):
    """The selected Jalali year's totals, mirroring the yearly Excel figures:
    total charge, total expense, balance (charge - expense) and the outstanding
    receivable (charge minus payments made towards those charges)."""
    charges = building.charges.exclude(status=Charge.Status.CANCELLED).filter(year=year)
    charge_total = charges.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
    paid_total = charges.aggregate(t=Sum("allocations__amount"))["t"] or Decimal("0")
    start, end = _jalali_year_range(year)
    expense_total = (
        Expense.objects.filter(building=building, date__gte=start, date__lt=end)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0")
    )
    income_total = (
        Payment.objects.filter(unit__building=building, date__gte=start, date__lt=end)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0")
    )
    return {
        "charge": charge_total,
        "paid": paid_total,
        "receivable": charge_total - paid_total,
        "expense": expense_total,
        "income": income_total,
        "balance": charge_total - expense_total,
    }


def annual_chart(building, year):
    """Monthly charge vs expense series for one whole Jalali year."""
    series = []
    for month in range(1, 13):
        start = jdatetime.date(year, month, 1).togregorian()
        ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
        end = jdatetime.date(ny, nm, 1).togregorian()
        charge = (
            Charge.objects.filter(building=building, year=year, month=month)
            .exclude(status=Charge.Status.CANCELLED)
            .aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        )
        expense = (
            Expense.objects.filter(building=building, date__gte=start, date__lt=end)
            .aggregate(t=Sum("amount"))["t"] or Decimal("0")
        )
        series.append({"label": JALALI_MONTHS[month - 1], "charge": charge, "expense": expense})
    chart_max = max((max(p["charge"], p["expense"]) for p in series), default=Decimal("0"))
    denom = chart_max or Decimal("1")
    for point in series:
        point["charge_pct"] = int(point["charge"] / denom * 100)
        point["expense_pct"] = int(point["expense"] / denom * 100)
    return series, chart_max


def building_dashboard(request, pk):
    building = get_object_or_404(Building, pk=pk)
    years = building_years(building)
    current_year = jdatetime.date.fromgregorian(date=localdate()).year

    # Default to the current Jalali year when it has data, else the latest one.
    selected = current_year if current_year in years else (years[0] if years else None)
    raw = request.GET.get("year")
    if raw:
        try:
            value = int(raw)
        except ValueError:
            value = None
        if value in years:
            selected = value

    if selected is None:
        return render(request, "buildings/dashboard.html", {
            "building": building, "years": years, "year": None, "summary": None,
            "chart": [], "chart_max": Decimal("0"), "units": building.units.all(),
            "breakdown": {"none": building.units.count()},
            "current_year": current_year, "is_current_year": False,
        })

    units = []
    breakdown = {"paid": 0, "partial": 0, "unpaid": 0, "none": 0}
    for unit in building.units.all():
        qs = unit.charges.exclude(status=Charge.Status.CANCELLED).filter(year=selected)
        charged = qs.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        paid = qs.aggregate(t=Sum("allocations__amount"))["t"] or Decimal("0")
        units.append({"unit": unit, "charged": charged, "paid": paid})
        if charged == 0:
            breakdown["none"] += 1
        elif paid >= charged:
            breakdown["paid"] += 1
        elif paid > 0:
            breakdown["partial"] += 1
        else:
            breakdown["unpaid"] += 1

    summary = annual_summary(building, selected)
    chart, chart_max = annual_chart(building, selected)
    return render(request, "buildings/dashboard.html", {
        "building": building,
        "years": years,
        "year": selected,
        "current_year": current_year,
        "is_current_year": selected == current_year,
        "summary": summary,
        "chart": chart,
        "chart_max": chart_max,
        "units": units,
        "breakdown": breakdown,
    })
