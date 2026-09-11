from django.db import models
from django.db.models import Sum

from buildings.models import Building, Unit


class ChargeRule(models.Model):
    class Kind(models.TextChoices):
        FIXED = "fixed", "مبلغ ثابت هر واحد"
        AREA = "area", "به ازای هر متر مربع"
        PER_RESIDENT = "per_resident", "به ازای هر نفر"
        PARKING = "parking", "به ازای هر پارکینگ"
        STORAGE = "storage", "به ازای هر انبار"
        EXTRA = "extra", "مبلغ اضافه ثابت"
        DISCOUNT = "discount", "تخفیف (کسور)"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="charge_rules")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["building", "id"]

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"


class Charge(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "پرداخت نشده"
        PARTIAL = "partial", "پرداخت جزئی"
        PAID = "paid", "پرداخت شده"
        CANCELLED = "cancelled", "ابطال شده"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="charges")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="charges")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "unit__number"]
        constraints = [
            models.UniqueConstraint(fields=["unit", "year", "month"], name="unique_billing_period_per_unit"),
        ]
        indexes = [
            models.Index(fields=["building", "year", "month"]),
            models.Index(fields=["unit", "status"]),
        ]

    def __str__(self):
        return f"{self.unit} - {self.year}/{self.month}"

    def paid_amount(self):
        return self.allocations.aggregate(total=Sum("amount"))["total"] or 0


class ChargeItem(models.Model):
    charge = models.ForeignKey(Charge, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_amount = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
