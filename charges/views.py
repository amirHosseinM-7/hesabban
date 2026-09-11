from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from buildings.forms import month_choices
from buildings.htmx import htmx_success
from buildings.jalali import current_jalali, to_en_digits
from buildings.models import Building
from .forms import ChargeRuleForm, ManualChargeEditForm, ManualChargeForm
from .models import Charge, ChargeRule
from .services import (
    cancel_charge,
    create_manual_charge,
    generate_charges,
    period_label,
    preview_billing,
    update_manual_charge,
)


def rule_list(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    return render(request, "charges/rule_list.html", {"building": building, "rules": building.charge_rules.all()})


def rule_create(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    form = ChargeRuleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rule = form.save(commit=False)
        rule.building = building
        rule.save()
        return htmx_success("قانون شارژ ثبت شد")
    return render(request, "charges/rule_form.html", {"form": form, "building": building})


def rule_edit(request, pk):
    rule = get_object_or_404(ChargeRule, pk=pk)
    form = ChargeRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_success("قانون شارژ ویرایش شد")
    return render(request, "charges/rule_form.html", {"form": form, "building": rule.building, "rule": rule})


@require_POST
def rule_delete(request, pk):
    rule = get_object_or_404(ChargeRule, pk=pk)
    rule.delete()
    return htmx_success("قانون شارژ حذف شد")


def billing(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    year = to_en_digits(request.GET.get("year") or "")
    month = to_en_digits(request.GET.get("month") or "")
    jy, jm, _ = current_jalali()
    context = {
        "building": building,
        "months": month_choices(),
        "years": [jy + 1, jy, jy - 1, jy - 2],
        "year": jy,
        "month": jm,
    }
    if year and month:
        year, month = int(year), int(month)
        result = preview_billing(building, year, month)
        context.update({
            "year": year,
            "month": month,
            "preview": [
                {"unit": bill.unit, "area": bill.unit.area, "total": bill.total}
                for bill in result["bills"]
            ],
            "preview_total": result["total"],
            "already": result["already_generated"],
        })
    return render(request, "charges/billing.html", context)


@require_POST
def billing_generate(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    year = int(to_en_digits(request.POST.get("year") or "0"))
    month = int(to_en_digits(request.POST.get("month") or "0"))
    try:
        charges = generate_charges(building, year, month)
    except Exception as exc:
        message = getattr(exc, "messages", [str(exc)])[0]
        response = htmx_success(message)
        response["HX-Refresh"] = "false"
        return response
    response = htmx_success(f"صورتحساب {len(charges)} واحد صادر شد")
    response["HX-Redirect"] = f"/buildings/{building.pk}/charges/"
    return response


def charge_list(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    status = request.GET.get("status") or ""
    charges = Charge.objects.filter(building=building).select_related("unit")
    if status:
        charges = charges.filter(status=status)
    charges = charges.annotate(paid=Sum("allocations__amount")).order_by("-year", "-month", "unit__number")
    paginator = Paginator(charges, 25)
    page = paginator.get_page(request.GET.get("page"))
    badge_by_status = {
        Charge.Status.UNPAID: ("unpaid", "پرداخت نشده"),
        Charge.Status.PARTIAL: ("partial", "پرداخت جزئی"),
        Charge.Status.PAID: ("paid", "پرداخت شده"),
        Charge.Status.CANCELLED: ("cancelled", "ابطال شده"),
    }
    for charge in page.object_list:
        paid = charge.paid or 0
        charge.remaining = charge.total_amount - paid
        charge.status_display = badge_by_status[charge.status]
        charge.period_label_fa = period_label(charge.year, charge.month)
        charge.editable = not charge.allocations.exists() and charge.status != Charge.Status.CANCELLED
    return render(request, "charges/charge_list.html", {
        "building": building,
        "page": page,
        "charges": page.object_list,
        "status": status,
        "statuses": Charge.Status.choices,
        "filter_query": f"status={status}" if status else "",
    })


def charge_create(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    form = ManualChargeForm(request.POST or None, building=building)
    if request.method == "POST" and form.is_valid():
        try:
            create_manual_charge(
                form.cleaned_data["unit"],
                year=form.cleaned_data["year"],
                month=form.cleaned_data["month"],
                title=form.cleaned_data["title"],
                amount=form.cleaned_data["amount"],
            )
            return htmx_success("شارژ ثبت شد")
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
    return render(request, "charges/charge_form.html", {"form": form, "building": building})


def charge_edit(request, pk):
    charge = get_object_or_404(Charge.objects.select_related("unit", "building"), pk=pk)
    form = ManualChargeEditForm(request.POST or None, initial={
        "title": charge.items.first().title if charge.items.first() else "شارژ اضافه",
        "amount": charge.total_amount,
    })
    if request.method == "POST" and form.is_valid():
        try:
            update_manual_charge(
                charge,
                title=form.cleaned_data["title"],
                amount=form.cleaned_data["amount"],
            )
            return htmx_success("شارژ ویرایش شد")
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
    return render(request, "charges/charge_edit.html", {
        "form": form,
        "charge": charge,
        "editable": not charge.allocations.exists() and charge.status != Charge.Status.CANCELLED,
    })


@require_POST
def charge_cancel(request, pk):
    charge = get_object_or_404(Charge.objects.select_related("unit"), pk=pk)
    try:
        cancel_charge(charge)
        return htmx_success("شارژ ابطال شد")
    except ValidationError as exc:
        return htmx_success(exc.messages[0])
