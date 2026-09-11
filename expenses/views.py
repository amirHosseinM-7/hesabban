from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from buildings.htmx import htmx_success
from buildings.models import Building
from .forms import ExpenseForm
from .models import Expense
from .services import delete_expense, record_expense, update_expense


def _save(form, building=None, expense=None):
    data = {
        "category": form.cleaned_data["category"],
        "title": form.cleaned_data["title"],
        "amount": form.cleaned_data["amount"],
        "when": form.cleaned_data["date"],
        "note": form.cleaned_data["note"],
        "vendor": form.cleaned_data["vendor"],
        "payment_method": form.cleaned_data["payment_method"],
        "reference_number": form.cleaned_data["reference_number"],
        "attachment": form.cleaned_data.get("attachment"),
    }
    if expense is None:
        return record_expense(building=building, **data)
    return update_expense(expense, **data)


def _expense_form_response(request, form, building, expense=None):
    template = "expenses/expense_form.html"
    return render(request, template, {"form": form, "building": building, "expense": expense})


def expense_list(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    expenses = building.expenses.all()
    paginator = Paginator(expenses, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "expenses/expense_list.html", {
        "building": building,
        "page": page,
        "expenses": page.object_list,
    })


def expense_create(request, building_pk):
    building = get_object_or_404(Building, pk=building_pk)
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            _save(form, building=building)
            return htmx_success("هزینه ثبت شد")
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
    return _expense_form_response(request, form, building)


def expense_edit(request, pk):
    expense = get_object_or_404(Expense.objects.select_related("building"), pk=pk)
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=expense)
    if request.method == "POST" and form.is_valid():
        try:
            _save(form, expense=expense)
            return htmx_success("هزینه ویرایش شد")
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
    return _expense_form_response(request, form, expense.building, expense)


@require_POST
def expense_delete(request, pk):
    expense = get_object_or_404(Expense.objects.select_related("building"), pk=pk)
    delete_expense(expense)
    return htmx_success("هزینه حذف شد")
