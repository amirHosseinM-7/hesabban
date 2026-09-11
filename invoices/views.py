import urllib.parse

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from buildings.models import Building
from charges.models import Charge
from expenses.models import Expense
from payments.models import Payment
from . import excel, pdf


def _pdf_response(name):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{urllib.parse.quote(name)}.pdf"'
    return response


def charge_invoice_pdf(request, pk):
    charge = get_object_or_404(
        Charge.objects.select_related("building", "unit").prefetch_related("items"), pk=pk
    )
    response = _pdf_response(f"invoice-{charge.pk}")
    pdf.charge_invoice(charge, response)
    return response


def payment_receipt_pdf(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("unit", "unit__building").prefetch_related("allocations__charge"),
        pk=pk,
    )
    response = _pdf_response(f"receipt-{payment.pk}")
    pdf.payment_receipt(payment, response)
    return response


def payments_xlsx(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="payments-{building.pk}.xlsx"'
    return excel.export_payments(building, response)


def expenses_xlsx(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="expenses-{building.pk}.xlsx"'
    return excel.export_expenses(building, response)
