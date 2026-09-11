from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from buildings.models import Building, Resident, Unit
from charges.models import Charge, ChargeItem, ChargeRule
from charges.services import (
    compute_unit_items,
    create_manual_charge,
    generate_charges,
    update_manual_charge,
)
from expenses.models import Expense
from expenses.services import delete_expense, record_expense, update_expense
import jdatetime
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


@pytest.fixture
def client():
    return Client()


def test_charge_list_and_manual_charge_pages_render(building, client):
    generate_charges(building, 1403, 1)
    url = reverse("charge_list", args=[building.pk])
    r = client.get(url)
    assert r.status_code == 200
    assert "واحد 101" in r.content.decode()
    # manual charge modal + billing templates must exist (previously 500)
    assert client.get(reverse("charge_create", args=[building.pk])).status_code == 200
    c = Charge.objects.get(unit__number="101")
    assert client.get(reverse("charge_edit", args=[c.pk])).status_code == 200


def test_charge_edit_blocked_after_payment(building, client):
    generate_charges(building, 1403, 3)
    unit = building.units.get(number="101")
    record_payment(unit, Decimal("100000"), "2025-01-01", Payment.Method.CASH)
    c = unit.charges.first()
    assert client.get(reverse("charge_edit", args=[c.pk])).status_code == 200


def test_billing_preview_lists_units(building, client):
    url = f"{reverse('billing', args=[building.pk])}?year=1404&month=1"
    r = client.get(url)
    assert r.status_code == 200
    # previously used an undefined `units` variable and never showed the preview
    assert "واحد 101" in r.content.decode()
    assert "صدور نهایی" in r.content.decode()


def test_expense_pages_render(building, client):
    record_expense(building, "electricity", "قبض برق", Decimal("200000"), "2025-01-05")
    assert client.get(reverse("expense_list", args=[building.pk])).status_code == 200
    assert client.get(reverse("expense_create", args=[building.pk])).status_code == 200
    e = Expense.objects.get(title="قبض برق")
    assert client.get(reverse("expense_edit", args=[e.pk])).status_code == 200


def test_payment_and_ledger_lists_render(building, client):
    assert client.get(reverse("payment_list", args=[building.pk])).status_code == 200
    assert client.get(reverse("ledger_list", args=[building.pk])).status_code == 200


def test_maintenance_list_has_status_options(building, client):
    r = client.get(reverse("maintenance_list", args=[building.pk]))
    assert r.status_code == 200
    assert "در انتظار بررسی" in r.content.decode()


def test_list_pagination_after_25_items(building, client):
    for i in range(30):
        record_expense(building, "other", f"هزینه {i}", Decimal("1000"), "2025-01-01")
    r = client.get(reverse("expense_list", args=[building.pk]))
    assert r.status_code == 200
    page = r.context["page"]
    assert len(page.object_list) == 25
    assert page.has_next()


def test_seed_demo_command_runs(db):
    from django.core.management import call_command

    call_command("seed_demo")
    b = Building.objects.get(name="ساختمان گلستان")
    assert b.units.count() == 6
    assert b.expenses.filter(category="repairs").exists()
    assert not b.expenses.filter(category__in=["repair", "utilities"]).exists()


def _workbook(tmp_path):
    """Build a small ledger mirroring the real 'ساختمان.xlsx' layout:
    month name sits on the same row as unit 1's charge; expenses are tied to
    the current month block."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "1404"
    rows = [
        ["ماه", "واحد ", "مبلغ شارژ", "هزینه", "شرح هزینه"],
        ["انتقال از سال 1403", None, 100000, None, None],
        ["فروردین", 1, 700000, 1000000, "نظافت"],   # unit1 charge + expense on month row
        [None, 2, 700000, 900000, None],         # expense with blank description must still import
        [None, 3, 1000000, None, None],
        [None, 4, 700000, 278000, "برق"],
        ["اردیبهشت", 1, 1000000, None, None],
        [None, 2, 0, None, None],                     # zero charge must be skipped
        [None, 3, 1000000, 1500000, "تعمیر سرامیک"],
        [None, 4, 1000000, None, None],
        ["جمع کل هزینه ها", None, 3400000, 2778000, None],
    ]
    for row in rows:
        ws.append(row)
    path = tmp_path / "test.xlsx"
    wb.save(path)
    return path


def test_import_sakhteman_command(db, tmp_path):
    from django.core.management import call_command

    path = _workbook(tmp_path)
    call_command("import_sakhteman", str(path))
    b = Building.objects.get(name="ساختمان من")
    assert [u.number for u in b.units.order_by("number")] == ["1", "2", "3", "4"]

    # مرحله در ردیف واحد 1 ثبت شد (month label row also carries unit 1)
    u1 = b.units.get(number="1")
    assert Charge.objects.filter(unit=u1, year=1404, month=1, total_amount=Decimal("700000")).exists()

    # شارژ صفر نادیده می‌شود
    u2 = b.units.get(number="2")
    assert Charge.objects.filter(unit=u2, year=1404, month=2).count() == 0

    # 4 واحد × 2 ماه = 8 منهای شارژ صفر واحد 2 در اردیبهشت = 7 شارژ
    assert b.charges.count() == 7

    # دسته‌بندی هزینه بر مبنای شرح
    cats = dict(b.expenses.values_list("title", "category"))
    assert cats["نظافت"] == "cleaning"
    assert cats["برق"] == "electricity"
    assert cats["تعمیر سرامیک"] == "repairs"
    # هزینه بدون شرح هنوز ثبت می‌شود
    assert cats["بدون شرح"] == "other"

    # اجرای دوباره باید به‌دلیل بلاک ایدم‌پتنت (ساختمان موجود است) بدون دوباره‌سازی بماند
    call_command("import_sakhteman", str(path))
    assert b.__class__.objects.filter(name="ساختمان من").count() == 1
    assert b.charges.count() == 7
    assert b.ledger_entries.filter(kind="charge").count() == 7
    assert b.ledger_entries.filter(kind="expense").count() == 4


def test_dashboard_year_selection(db):
    """Each year is shown separately; previous years don't leak into the
    selected year's figures."""
    from django.test import Client
    from django.urls import reverse

    b = Building.objects.create(name="ساختمان سال‌ها")
    u = Unit.objects.create(building=b, number="101", area=Decimal("50"))
    Charge.objects.create(building=b, unit=u, year=1401, month=1, total_amount=Decimal("1000000"))
    record_expense(b, "other", "هزینه", Decimal("300000"), jdatetime.date(1401, 1, 1).togregorian())
    Charge.objects.create(building=b, unit=u, year=1402, month=1, total_amount=Decimal("2000000"))
    record_expense(b, "other", "هزینه", Decimal("500000"), jdatetime.date(1402, 1, 1).togregorian())

    c = Client()
    url = reverse("building_dashboard", args=[b.pk])

    # default = the latest year that has data
    r = c.get(url)
    assert r.context["year"] == 1402
    assert r.context["summary"]["charge"] == Decimal("2000000")
    assert r.context["summary"]["expense"] == Decimal("500000")

    # a previous year is reachable but isolated from the others
    r = c.get(url + "?year=1401")
    assert r.context["year"] == 1401
    assert r.context["summary"]["charge"] == Decimal("1000000")
    assert r.context["summary"]["expense"] == Decimal("300000")
    assert r.context["summary"]["expense"] != Decimal("500000")

    # the year navigator lists both years, newest first
    assert r.context["years"] == [1402, 1401]
