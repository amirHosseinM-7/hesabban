"""Import the residential building ledger from an Excel workbook.

The workbook 'ساختمان.xlsx' holds one sheet per Jalali year (1401-1405).
Each sheet lists the monthly charge for units 1-4 and the building-level
expenses with a description for each month. This command reads that file
and stores it as a building named 'ساختمان من'.

It is idempotent: if the building already exists it exits early.

Warning: the file has no explicit payment records, so imported charges are
left with the default 'unpaid' status. Carry-over balances (انتقال از سال)
and the yearly totals are reconciliation figures only and are not imported
into the transaction models.
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path

import jdatetime
import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from buildings.jalali import JALALI_MONTHS
from buildings.models import Building, Unit
from charges.models import Charge, ChargeItem
from expenses.services import record_expense
from ledger.services import post_entry


BUILDING_NAME = "ساختمان من"
UNITS = ["1", "2", "3", "4"]


def _amount(value):
    """Coerce an Excel cell to a positive Decimal, or None when absent."""
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("1"))  # strip decimals
    except (InvalidOperation, ValueError):
        return None
    return amount if amount > 0 else None


def infer_category(title):
    """Map an expense description to an Expense.Category choice."""
    t = (title or "").strip()
    mappings = [
        ("electricity", ("برق", "لامپ", "روشنایی")),
        ("water", ("آب",)),
        ("gas", ("گاز",)),
        ("cleaning", ("نظافت", "تاید", "وایتکس", "کیسه", "شوینده", "پادری",
                      "دسته تی", "شیشه شوی", "زباله")),
        ("elevator", ("آسانسور", "اسانسور")),
        ("repairs", ("تعمیر", "چسب", "توری", "لوله", "سرامیک", "سنسور",
                     "حفاظ", "درب", "دوربین", "کارتک", "فوری")),
    ]
    for category, keywords in mappings:
        if any(k in t for k in keywords):
            return category
    return "other"


def _gregorian(year, month):
    return jdatetime.date(year, month, 15).togregorian()


class Command(BaseCommand):
    help = f"Read an Excel ledger and store it as the '{BUILDING_NAME}' building."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(settings.BASE_DIR / "ساختمان.xlsx"))

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"فایل پیدا نشد: {path}")

        if Building.objects.filter(name=BUILDING_NAME).exists():
            self.stdout.write("ساختمان 'ساختمان من' قبلاً ساخته شده است.")
            return

        wb = openpyxl.load_workbook(path, data_only=True)
        with transaction.atomic():
            building = Building.objects.create(name=BUILDING_NAME)
            units = {num: Unit.objects.create(building=building, number=num) for num in UNITS}

            total_charges = 0
            total_expenses = 0
            for sheet in wb.worksheets:
                charges, expenses = self._import_year(building, units, sheet)
                if charges or expenses:
                    self.stdout.write(f"{sheet.title}: {charges} شارژ، {expenses} هزینه")
                total_charges += charges
                total_expenses += expenses

        self.stdout.write(self.style.SUCCESS(
            f"داده‌ها ثبت شد: {BUILDING_NAME} — {len(units)} واحد، "
            f"{total_charges} شارژ، {total_expenses} هزینه"))

    def _import_year(self, building, units, sheet):
        """Import one sheet; returns (charge_count, expense_count)."""
        try:
            year = int(sheet.title)
        except ValueError:
            self.stderr.write(f"برگه با نام سال خوانا «{sheet.title}» رد شد.")
            return 0, 0

        current_month = None
        charges = 0
        expenses = 0
        seen = set()  # (unit_key, month) already charged this year

        for row in sheet.iter_rows(values_only=True):
            month_name, unit_number, charge_val, expense_val, description = (list(row) + [None] * 5)[:5]

            label = (month_name or "").strip()
            if label == "ماه":  # header
                continue
            if label.startswith("انتقال"):
                # carry-over balance — reconciliation only, not a transaction
                continue
            if label.startswith("جمع کل"):
                # yearly totals row ends the data
                break
            if label in JALALI_MONTHS:
                # A month block begins on the very row that also carries unit
                # 1's charge, so set the month and fall through on purpose.
                current_month = JALALI_MONTHS.index(label) + 1
            if current_month is None:
                continue  # data row outside a known month block

            # ---- expenses (building-level, tied to the current month) ----
            expense_amt = _amount(expense_val)
            if expense_amt is not None and description:
                record_expense(
                    building,
                    infer_category(description),
                    str(description).strip(),
                    expense_amt,
                    _gregorian(year, current_month),
                )
                expenses += 1

            # ---- charges (per unit per month) ----
            charge_amt = _amount(charge_val)
            if charge_amt is None or unit_number is None:
                continue
            unit_key = str(int(unit_number))
            unit = units.get(unit_key)
            key = (unit_key, current_month)
            if unit is None or key in seen:
                continue  # unknown/duplicate charge row
            seen.add(key)

            charge = Charge.objects.create(
                building=building, unit=unit, year=year,
                month=current_month, total_amount=charge_amt,
            )
            ChargeItem.objects.create(
                charge=charge, title="شارژ ماهانه", kind="fixed",
                quantity=1, unit_amount=charge_amt, amount=charge_amt,
            )
            post_entry(
                building=building, date=_gregorian(year, current_month),
                kind="charge", debit=charge_amt, credit=Decimal("0"),
                description=f"شارژ {JALALI_MONTHS[current_month - 1]} {year} — واحد {unit.number}",
                ref=charge,
            )
            charges += 1

        return charges, expenses