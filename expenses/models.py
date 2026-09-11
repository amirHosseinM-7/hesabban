from django.db import models

from buildings.models import Building


class Expense(models.Model):
    class Category(models.TextChoices):
        WATER = "water", "آب"
        ELECTRICITY = "electricity", "برق"
        GAS = "gas", "گاز"
        CLEANING = "cleaning", "نظافت"
        ELEVATOR = "elevator", "آسانسور"
        REPAIRS = "repairs", "تعمیرات"
        OTHER = "other", "سایر"

    class Method(models.TextChoices):
        CASH = "cash", "نقدی"
        CARD = "card", "کارت"
        TRANSFER = "transfer", "انتقال بانکی"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=150)
    vendor = models.CharField("پرداخت‌کننده / فروشنده", max_length=150, blank=True)
    payment_method = models.CharField("روش پرداخت", max_length=10, choices=Method.choices, default=Method.CASH)
    reference_number = models.CharField("شماره پیگیری", max_length=50, blank=True)
    attachment = models.FileField("پیوست", upload_to="expenses/", null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["building", "date"])]

    def __str__(self):
        return f"{self.title} - {self.amount}"
