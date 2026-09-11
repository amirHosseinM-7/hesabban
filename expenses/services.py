from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Expense
from ledger.services import post_entry, remove_entries


def _validate_amount(amount):
    if amount is None or amount <= 0:
        raise ValidationError("مبلغ هزینه باید بزرگ‌تر از صفر باشد.")


@transaction.atomic
def record_expense(building, category, title, amount, when, note="", vendor="", payment_method="cash", reference_number="", attachment=None):
    _validate_amount(amount)
    expense = Expense.objects.create(
        building=building,
        category=category,
        title=title,
        vendor=vendor,
        payment_method=payment_method,
        reference_number=reference_number,
        attachment=attachment,
        amount=amount,
        date=when,
        note=note,
    )
    post_entry(
        building=building,
        date=when,
        kind="expense",
        debit=amount,
        credit=0,
        description=title,
        ref=expense,
    )
    return expense


@transaction.atomic
def update_expense(expense, *, category, title, amount, when, note="", vendor="", payment_method="cash", reference_number="", attachment=None):
    """Edit a posted expense and re-post its ledger entry from scratch."""
    _validate_amount(amount)
    remove_entries(expense)
    expense.category = category
    expense.title = title
    expense.vendor = vendor
    expense.payment_method = payment_method
    expense.reference_number = reference_number
    if attachment is not None:
        expense.attachment = attachment
    expense.amount = amount
    expense.date = when
    expense.note = note
    expense.save()
    post_entry(
        building=expense.building,
        date=when,
        kind="expense",
        debit=amount,
        credit=0,
        description=title,
        ref=expense,
    )
    return expense


@transaction.atomic
def delete_expense(expense):
    """Delete a posted expense and remove its ledger entry."""
    remove_entries(expense)
    expense.delete()

