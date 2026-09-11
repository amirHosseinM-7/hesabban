import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from buildings.models import Building, Resident, Unit
from charges.services import generate_charges
from expenses.services import record_expense
from maintenance.models import MaintenanceRequest
from payments.services import record_payment


class Command(BaseCommand):
    help = "Populate the database with one realistic demo building."

    @transaction.atomic
    def handle(self, *args, **options):
        if Building.objects.filter(name="ساختمان گلستان").exists():
            self.stdout.write("داده‌های نمونه قبلاً ساخته شده است.")
            return
        from charges.models import ChargeRule

        b = Building.objects.create(name="ساختمان گلستان", address="تهران، خیابان ولیعصر، کوچه صدوقی، پلاک ۱۲")
        area = [85, 105, 120, 95, 130, 75]
        for i, a in enumerate(area, start=1):
            Unit.objects.create(building=b, number=str(100 + i), area=a,
                                parking_count=1 if i % 2 else 0, storage_count=0 if i % 3 else 1)
        names = ["علی رضایی", "مریم کاظمی", "حسین موسوی", "زهرا احمدی", "رضا صادقی", "نرگس مرادی",
                 "امیر جعفری", "سمانه حسینی", "بهرام نوری", "لیلا شریفی"]
        for unit, name in zip(Unit.objects.order_by("number"), names[: max(1, len(Unit.objects.all()))]):
            Resident.objects.create(unit=unit, full_name=name, phone=f"0912{random.randint(1000000, 9999999)}")
            if random.random() < 0.5 and len(names) > 1:
                second = random.choice([n for n in names if n != name])
                Resident.objects.create(unit=unit, full_name=second, phone="")

        ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.FIXED, title="شهریه ماهانه", amount=500000)
        ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.AREA, title="شارژ بر مبنای متراژ", amount=5000)
        ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.PARKING, title="پارکینگ", amount=150000)
        ChargeRule.objects.create(building=b, kind=ChargeRule.Kind.PER_RESIDENT, title="سرانه ساکن", amount=100000)

        today = date.today()
        import jdatetime

        jt = jdatetime.date.fromgregorian(date=today)
        for back in range(3):
            m = jt.month - back
            y = jt.year
            while m <= 0:
                m += 12
                y -= 1
            generate_charges(b, y, m)

        units = list(Unit.objects.order_by("number"))
        for unit in units[:4]:
            for charge in unit.charges.order_by("year", "month"):
                if random.random() < 0.8:
                    record_payment(unit, charge.total_amount, charge.created_at.date(), "card", "")
        partial = [c for c in units[4].charges.order_by("year", "month")][0]
        record_payment(units[4], partial.total_amount // 2, partial.created_at.date(), "cash", "")

        for title, amount, when in [
            ("قبض برق مشترک", 1450000, today - timedelta(days=20)),
            ("هزینه نگهبان", 4200000, today - timedelta(days=15)),
            ("تعمیر پمپ آب", 980000, today - timedelta(days=8)),
            ("قبض آب", 760000, today - timedelta(days=3)),
        ]:
            if "تعمیر" in title:
                category = "repairs"
            elif "برق" in title:
                category = "electricity"
            elif "آب" in title:
                category = "water"
            else:
                category = "other"
            record_expense(b, category, title, amount, when)

        MaintenanceRequest.objects.create(unit=units[0], title="نشت آب زیر سینک", description="...",
                                          status=MaintenanceRequest.Status.PENDING)
        MaintenanceRequest.objects.create(unit=units[2], title="خرابی آسانسور", description="...",
                                          status=MaintenanceRequest.Status.IN_PROGRESS)
        self.stdout.write(self.style.SUCCESS(f"داده‌های نمونه ساخته شد: {b.name}"))
