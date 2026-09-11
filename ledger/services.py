from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Sum

from .models import LedgerEntry


@transaction.atomic
def remove_entries(ref):
    """Remove ledger entries posted for a ref (used only inside service-layer
    reversal flows: expense edit/delete, payment void, charge cancel)."""
    ct = ContentType.objects.get_for_model(ref)
    LedgerEntry.objects.filter(content_type=ct, object_id=ref.pk).delete()


@transaction.atomic
def post_entry(*, building, date, kind, debit, credit, description, ref=None):
    """Append one immutable entry to the building ledger."""
    if date is None:
        from django.utils.timezone import localdate
        date = localdate()
    return LedgerEntry.objects.create(
        building=building,
        date=date,
        kind=kind,
        debit=debit,
        credit=credit,
        description=description,
        content_type=ContentType.objects.get_for_model(ref) if ref is not None else None,
        object_id=ref.pk if ref is not None else None,
    )


def building_summary(building):
    """Recompute balances purely from the ledger.

    Returns fund balance (payments in minus expenses out) and the
    outstanding receivable (posted charges minus posted payments allocated
    against them, i.e. charge debits minus payment credits).
    """
    qs = building.ledger_entries
    fund_balance = (
        qs.filter(kind__in=[LedgerEntry.Kind.PAYMENT, LedgerEntry.Kind.EXPENSE])
        .aggregate(balance=Sum("credit") - Sum("debit"))["balance"]
    ) or Decimal("0")
    receivable = (
        qs.filter(kind__in=[LedgerEntry.Kind.CHARGE, LedgerEntry.Kind.PAYMENT])
        .aggregate(balance=Sum("debit") - Sum("credit"))["balance"]
    ) or Decimal("0")
    total_income = qs.filter(kind=LedgerEntry.Kind.PAYMENT).aggregate(t=Sum("credit"))["t"] or Decimal("0")
    total_expense = qs.filter(kind=LedgerEntry.Kind.EXPENSE).aggregate(t=Sum("debit"))["t"] or Decimal("0")
    return {
        "fund_balance": fund_balance,
        "receivable": receivable,
        "total_income": total_income,
        "total_expense": total_expense,
    }
