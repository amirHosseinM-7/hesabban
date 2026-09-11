"""Payment recording and FIFO allocation to outstanding charges."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery, Sum

from .models import Allocation, Payment
from charges.models import Charge


def annotate_unit_balances(units):
    """Annotate a Unit queryset with charged/paid sums over valid charges."""
    charged = (Charge.objects.filter(unit=OuterRef("pk"))
               .exclude(status=Charge.Status.CANCELLED)
               .order_by().values("unit").annotate(t=Sum("total_amount")).values("t"))
    paid = (Charge.objects.filter(unit=OuterRef("pk"))
            .exclude(status=Charge.Status.CANCELLED)
            .order_by().values("unit").annotate(t=Sum("allocations__amount")).values("t"))
    return units.annotate(
        charged=Subquery(charged),
        paid=Subquery(paid),
    )


def outstanding_charges(unit):
    charges = []
    for charge in unit.charges.exclude(status=Charge.Status.CANCELLED).order_by("year", "month", "id"):
        paid = charge.allocations.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        due = charge.total_amount - paid
        if due > 0:
            charges.append((charge, due))
    return charges


def total_outstanding(unit):
    return sum((due for _, due in outstanding_charges(unit)), Decimal("0"))


@transaction.atomic
def record_payment(unit, amount, when, method, note=""):
    """Create a payment, allocate it FIFO to the unit's outstanding charges,
    update charge statuses and post ledger entries, atomically."""
    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError("مبلغ پرداخت باید بزرگ‌تر از صفر باشد.")
    outstanding = outstanding_charges(unit)
    total_due = sum((due for _, due in outstanding), Decimal("0"))
    if amount > total_due:
        raise ValidationError("مبلغ پرداخت بیش از کل بدهی واحد است.")

    from ledger.services import post_entry

    payment = Payment.objects.create(unit=unit, amount=amount, date=when, method=method, note=note)
    remaining = amount
    for charge, due in outstanding:
        if remaining <= 0:
            break
        allocated = min(due, remaining)
        Allocation.objects.create(payment=payment, charge=charge, amount=allocated)
        paid = charge.paid_amount()
        if paid >= charge.total_amount:
            charge.status = Charge.Status.PAID
        else:
            charge.status = Charge.Status.PARTIAL
        charge.save(update_fields=["status"])
        remaining -= allocated

    post_entry(
        building=unit.building,
        date=when,
        kind="payment",
        debit=Decimal("0"),
        credit=amount,
        description=f"پرداخت واحد {unit.number}",
        ref=payment,
    )
    return payment


def unit_balance(unit):
    """(charged, paid, outstanding) for one unit across all valid charges."""
    qs = unit.charges.exclude(status=Charge.Status.CANCELLED)
    charged = qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    paid = qs.aggregate(total=Sum("allocations__amount"))["total"] or Decimal("0")
    return charged, paid, charged - paid


@transaction.atomic
def void_payment(payment):
    """Void a payment: drop its allocations, recompute affected charge
    statuses and remove its ledger entry, atomically."""
    from ledger.services import remove_entries

    affected = Charge.objects.filter(allocations__payment=payment).distinct()
    payment.allocations.all().delete()
    remove_entries(payment)
    for charge in affected:
        paid = charge.paid_amount()
        if paid == 0:
            charge.status = Charge.Status.UNPAID
        elif paid >= charge.total_amount:
            charge.status = Charge.Status.PAID
        else:
            charge.status = Charge.Status.PARTIAL
        charge.save(update_fields=["status"])
    payment.delete()


@transaction.atomic
def update_payment(payment, *, amount, when, method, note=""):
    """Edit a payment by voiding and re-recording it atomically, so the
    allocations, charge statuses and ledger entry are always consistent."""
    building = payment.unit.building
    void_payment(payment)
    return record_payment(unit=payment.unit, amount=amount, when=when, method=method, note=note)
