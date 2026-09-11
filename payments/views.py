from decimal import Decimal

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from buildings.htmx import htmx_success
from buildings.models import Building, Unit
from buildings.jalali import jalali_today
from charges.services import period_label
from payments.services import (outstanding_charges, record_payment, unit_balance,
                               update_payment, void_payment)
from .forms import PaymentForm
from .models import Payment


def payment_list(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    unit_filter = request.GET.get("unit") or ""
    payments = (Payment.objects.filter(unit__building=building)
                .select_related("unit").order_by("-date", "-id"))
    if unit_filter:
        payments = payments.filter(unit_id=unit_filter)
    paginator = Paginator(payments, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "payments/payment_list.html", {
        "building": building,
        "page": page,
        "payments": page.object_list,
        "units": building.units.all(),
        "unit_filter": unit_filter,
        "filter_query": f"unit={unit_filter}" if unit_filter else "",
    })


def payment_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    outstanding = unit_balance(unit)[2]
    form = PaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            record_payment(
                unit=unit,
                amount=form.cleaned_data["amount"],
                when=form.cleaned_data["date"],
                method=form.cleaned_data["method"],
                note=form.cleaned_data["note"],
            )
        except Exception as exc:
            message = getattr(exc, "messages", [str(exc)])[0]
            response = htmx_success(message)
            response["HX-Refresh"] = "false"
            return response
        return htmx_success("پرداخت ثبت شد")
    return render(request, "payments/payment_form.html", {
        "form": form,
        "unit": unit,
        "outstanding": outstanding,
    })


def unit_finance(request, pk):
    """Per-unit page: outstanding charges, payments, and balance."""
    unit = get_object_or_404(Unit.objects.select_related("building"), pk=pk)
    charged, paid, outstanding = unit_balance(unit)
    outstanding_items = [
        {
            "charge": charge,
            "remaining": due,
            "period_label_fa": f"{period_label(charge.year, charge.month)}",
        }
        for charge, due in outstanding_charges(unit)
    ]
    return render(request, "payments/unit_finance.html", {
        "unit": unit,
        "charged": charged,
        "paid": paid,
        "outstanding": outstanding,
        "outstanding_items": outstanding_items,
        "payments": unit.payments.all(),
        "today": jalali_today(),
    })




def payment_edit(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("unit"), pk=pk)
    unit = payment.unit
    form = PaymentForm(request.POST or None, initial={
        "amount": payment.amount, "date": payment.date,
        "method": payment.method, "note": payment.note,
    })
    if request.method == "POST" and form.is_valid():
        try:
            update_payment(
                payment,
                amount=form.cleaned_data["amount"],
                when=form.cleaned_data["date"],
                method=form.cleaned_data["method"],
                note=form.cleaned_data["note"],
            )
        except Exception as exc:
            message = getattr(exc, "messages", [str(exc)])[0]
            response = htmx_success(message)
            response["HX-Refresh"] = "false"
            return response
        return htmx_success("پرداخت ویرایش شد")
    return render(request, "payments/payment_edit.html", {
        "form": form,
        "unit": unit,
        "payment": payment,
    })


@require_POST
def payment_void(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("unit"), pk=pk)
    try:
        void_payment(payment)
    except Exception as exc:
        message = getattr(exc, "messages", [str(exc)])[0]
        return htmx_success(message)
    return htmx_success("پرداخت ابطال شد")
