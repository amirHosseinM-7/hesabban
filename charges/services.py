"""Charge calculation and monthly billing services."""
from dataclasses import dataclass, field
from decimal import Decimal

from buildings.jalali import JALALI_MONTHS
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Charge, ChargeItem, ChargeRule


def period_label(year, month):
    return f"{JALALI_MONTHS[month - 1]} {year}"


@dataclass
class UnitBill:
    unit: object
    items: list = field(default_factory=list)

    @property
    def total(self):
        return sum((item["amount"] for item in self.items), Decimal("0"))


def compute_unit_items(unit, rules, residents_count):
    items = []
    for rule in rules:
        if rule.kind == ChargeRule.Kind.FIXED:
            quantity = Decimal("1")
        elif rule.kind == ChargeRule.Kind.AREA:
            quantity = unit.area
        elif rule.kind == ChargeRule.Kind.PER_RESIDENT:
            quantity = Decimal(residents_count)
        elif rule.kind == ChargeRule.Kind.PARKING:
            quantity = Decimal(unit.parking_count)
        elif rule.kind == ChargeRule.Kind.STORAGE:
            quantity = Decimal(unit.storage_count)
        elif rule.kind in (ChargeRule.Kind.EXTRA, ChargeRule.Kind.DISCOUNT):
            quantity = Decimal("1")
        else:
            continue
        if quantity == 0:
            continue
        sign = Decimal("-1") if rule.kind == ChargeRule.Kind.DISCOUNT else Decimal("1")
        amount = rule.amount * quantity * sign
        if amount == 0:
            continue
        items.append({
            "title": rule.title,
            "kind": rule.kind,
            "quantity": quantity,
            "unit_amount": rule.amount,
            "amount": amount,
        })
    return items


def preview_billing(building, year, month):
    """Compute the bills for a period without touching the database state."""
    rules = list(building.charge_rules.filter(is_active=True))
    bills = []
    for unit in building.units.all():
        residents_count = unit.residents.filter(is_active=True).count()
        bills.append(UnitBill(unit=unit, items=compute_unit_items(unit, rules, residents_count)))
    existing = Charge.objects.filter(building=building, year=year, month=month).exists()
    return {"bills": bills, "total": sum((b.total for b in bills), Decimal("0")), "already_generated": existing}


@transaction.atomic
def generate_charges(building, year, month):
    """Generate charges for all units of a building for one period, exactly once."""
    if not (1 <= month <= 12) or year < 1300 or year > 1500:
        raise ValidationError("دوره صورتحساب نامعتبر است.")
    if Charge.objects.filter(building=building, year=year, month=month).exists():
        raise ValidationError("برای این دوره قبلاً صورتحساب صادر شده است.")
    from ledger.services import post_entry

    rules = list(building.charge_rules.filter(is_active=True))
    charges = []
    for unit in building.units.all():
        residents_count = unit.residents.filter(is_active=True).count()
        items = compute_unit_items(unit, rules, residents_count)
        total = sum((item["amount"] for item in items), Decimal("0"))
        charge = Charge.objects.create(
            building=building,
            unit=unit,
            year=year,
            month=month,
            total_amount=total,
        )
        ChargeItem.objects.bulk_create([
            ChargeItem(charge=charge, **item) for item in items
        ])
        post_entry(
            building=building,
            date=None,
            kind="charge",
            debit=total,
            credit=Decimal("0"),
            description=f"شارژ {period_label(year, month)} — واحد {unit.number}",
            ref=charge,
        )
        charges.append(charge)
    return charges


@transaction.atomic
def cancel_charge(charge):
    if charge.status == Charge.Status.PAID:
        raise ValidationError("شارژ تسویه‌شده قابل ابطال نیست.")
    remaining = charge.total_amount - charge.paid_amount()
    if remaining != 0:
        raise ValidationError("ابتدا مبالغ پرداخت‌شده این شارژ را بازگردانید.")
    from ledger.services import remove_entries

    remove_entries(charge)
    charge.status = Charge.Status.CANCELLED
    charge.save(update_fields=["status"])


@transaction.atomic
def create_manual_charge(unit, *, year, month, title, amount, date=None):
    """Create a one-off charge for a single unit (e.g. special assessment).

    Uses the same snapshot + ledger posting flow as monthly billing, and
    is protected by the same unique (unit, year, month) constraint.
    """
    from ledger.services import post_entry

    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError("مبلغ شارژ باید بزرگ‌تر از صفر باشد.")
    if not (1 <= month <= 12) or year < 1300 or year > 1500:
        raise ValidationError("دوره صورتحساب نامعتبر است.")
    if Charge.objects.filter(unit=unit, year=year, month=month).exists():
        raise ValidationError("برای واحد و دوره انتخاب‌شده قبلاً صورتحساب صادر شده است.")
    charge = Charge.objects.create(
        building=unit.building,
        unit=unit,
        year=year,
        month=month,
        total_amount=amount,
    )
    ChargeItem.objects.create(
        charge=charge,
        title=title,
        kind="extra",
        quantity=Decimal("1"),
        unit_amount=amount,
        amount=amount,
    )
    post_entry(
        building=unit.building,
        date=date,
        kind="charge",
        debit=amount,
        credit=Decimal("0"),
        description=f"{title} — واحد {unit.number} ({period_label(year, month)})",
        ref=charge,
    )
    return charge


@transaction.atomic
def update_manual_charge(charge, *, title, amount, date=None):
    """Edit an unpaid charge's single line item and re-post its ledger entry.

    Blocked if any payment has been allocated to the charge.
    """
    from ledger.services import post_entry, remove_entries

    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError("مبلغ شارژ باید بزرگ‌تر از صفر باشد.")
    if charge.allocations.exists():
        raise ValidationError("این شارژ پرداخت دارد و قابل ویرایش نیست.")
    if charge.status == Charge.Status.CANCELLED:
        raise ValidationError("شارژ ابطال‌شده قابل ویرایش نیست.")
    remove_entries(charge)
    item = charge.items.first()
    if item:
        item.title = title
        item.unit_amount = amount
        item.amount = amount
        item.save(update_fields=["title", "unit_amount", "amount"])
    charge.total_amount = amount
    charge.save(update_fields=["total_amount"])
    post_entry(
        building=charge.building,
        date=date,
        kind="charge",
        debit=amount,
        credit=Decimal("0"),
        description=f"{title} — واحد {charge.unit.number} ({period_label(charge.year, charge.month)})",
        ref=charge,
    )
    return charge
