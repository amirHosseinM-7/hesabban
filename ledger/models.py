from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from buildings.models import Building


class LedgerEntry(models.Model):
    """Append-only building ledger.

    A charge posts a receivable (debit), a payment posts money in (credit),
    an expense posts money out (debit). The building fund balance is always
    recomputed as sum(credits) - sum(debits) over payment/expense entries.
    """

    class Kind(models.TextChoices):
        CHARGE = "charge", "شارژ"
        PAYMENT = "payment", "پرداخت"
        EXPENSE = "expense", "هزینه"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="ledger_entries")
    date = models.DateField("تاریخ")
    kind = models.CharField("نوع", max_length=10, choices=Kind.choices)
    debit = models.DecimalField("بدهکار", max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField("بستانکار", max_digits=14, decimal_places=2, default=0)
    description = models.CharField("شرح", max_length=300)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    ref = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["building", "date"]), models.Index(fields=["kind"])]
