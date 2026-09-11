from django.db import models

from buildings.models import Unit


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "نقدی"
        CARD = "card", "کارت"
        TRANSFER = "transfer", "انتقال بانکی"

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["date"]), models.Index(fields=["unit", "date"])]

    def __str__(self):
        return f"{self.unit} - {self.amount}"


class Allocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    charge = models.ForeignKey("charges.Charge", on_delete=models.CASCADE, related_name="allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["charge__year", "charge__month"]
