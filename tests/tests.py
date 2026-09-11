from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from buildings.models import Building, Resident, Unit
from charges.models import Charge, ChargeItem, ChargeRule
from charges.services import compute_unit_items, create_manual_charge, generate_charges, update_manual_charge
from expenses.services import delete_expense, record_expense, update_expense
from ledger.models import LedgerEntry
from ledger.services import building_summary
from payments.models import Allocation, Payment
from payments.services import record_payment, total_outstanding, unit_balance, void_payment


@pytest.fixture
def building(db):
    b = Building.objects.create(name="ساختمان تست")
    u1 = Unit.objects.create(building=b, number="101", area=Decimal("100"), parking_count=1)
    u2 = Unit.objects.create(building=b, number="102", area=Decimal("50"))
    Resident.objects.create(unit=u1, full_name="ساکن یک")
    ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.FIXED, title="شهریه ثابت", amount=Decimal("100000"))
    ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.AREA, title="متر", amount=Decimal("1000"))
    ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.PARKING, title="پارکینگ", amount=Decimal("50000"))
    return b


def test_compute_unit_items(building):
    unit = building.units.get(number="101")
    rules = list(building.charge_rules.filter(is_active=True))
    items = compute_unit_items(unit, rules, residents_count=1)
    total = sum(i["amount"] for i in items)
    assert total == Decimal("100000") + Decimal("1000") * 100 + Decimal("50000")


def test_generate_charges_snapshot_and_duplicate(building):
    generate_charges(building, 1403, 1)
    with pytest.raises(ValidationError):
        generate_charges(building, 1403, 1)
    charges = Charge.objects.filter(building=building)
    assert charges.count() == 2
    building.charge_rules.all().update(amount=Decimal("999999"))
    assert ChargeItem.objects.first().amount != Decimal("999999")


def test_duplicate_period_constraint(building):
    generate_charges(building, 1403, 1)
    unit = building.units.first()
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Charge.objects.create(building=building, unit=unit, year=1403, month=1, total_amount=Decimal("1"))


def test_payment_allocation_and_ledger(building):
    generate_charges(building, 1403, 1)
    unit = building.units.get(number="101")
    total = unit.charges.first().total_amount
    payment = record_payment(unit, total - Decimal("50000"), "2025-01-01", Payment.Method.CASH)
    charged, paid, outstanding = unit_balance(unit)
    assert paid == total - Decimal("50000")
    assert outstanding == Decimal("50000")
    assert Allocation.objects.filter(payment=payment).exists()
    assert building_summary(building)["fund_balance"] == total - Decimal("50000")
    with pytest.raises(ValidationError):
        record_payment(unit, Decimal("-1"), "2025-01-01", Payment.Method.CASH)


def test_void_payment_restores_ledger(building):
    generate_charges(building, 1403, 1)
    unit = building.units.get(number="101")
    charge = unit.charges.first()
    payment = record_payment(unit, charge.total_amount, "2025-01-01", Payment.Method.CASH)
    charge.refresh_from_db()
    assert charge.status == Charge.Status.PAID
    void_payment(payment)
    charge.refresh_from_db()
    assert charge.status == Charge.Status.UNPAID
    assert unit_balance(unit)[1] == Decimal("0")
    assert not LedgerEntry.objects.filter(kind=LedgerEntry.Kind.PAYMENT).exists()


def test_expense_ledger_edit_delete(building):
    e = record_expense(building, "other", "برق", Decimal("200000"), "2025-01-05")
    assert building_summary(building)["total_expense"] == Decimal("200000")
    update_expense(e, category="other", title="برق", amount=Decimal("300000"), when="2025-01-05")
    summary = building_summary(building)
    assert summary["total_expense"] == Decimal("300000")
    assert LedgerEntry.objects.filter(object_id=e.pk).count() == 1
    delete_expense(e)
    assert building_summary(building)["total_expense"] == Decimal("0")
    with pytest.raises(ValidationError):
        record_expense(building, "other", "منفی", Decimal("-5"), "2025-01-05")


def test_manual_charge_flow(building):
    unit = building.units.first()
    charge = create_manual_charge(unit, year=1403, month=2, title="نظافت سوله", amount=Decimal("150000"), date="2025-01-02")
    assert charge.total_amount == Decimal("150000")
    update_manual_charge(charge, title="نظافت سوله", amount=Decimal("180000"))
    charge.refresh_from_db()
    assert charge.total_amount == Decimal("180000")
    record_payment(unit, Decimal("180000"), "2025-01-03", Payment.Method.CASH)
    with pytest.raises(ValidationError):
        update_manual_charge(charge, title="x", amount=Decimal("1"))
