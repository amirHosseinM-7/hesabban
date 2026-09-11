from django.db import models

from buildings.models import Unit


class MaintenanceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار بررسی"
        IN_PROGRESS = "in_progress", "در حال انجام"
        COMPLETED = "completed", "انجام‌شده"
        REJECTED = "rejected", "رد‌شده"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="maintenance_requests")
    title = models.CharField("عنوان", max_length=200)
    description = models.TextField("شرح", blank=True)
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.PENDING)
    photo = models.ImageField("عکس", upload_to="maintenance/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return self.title
