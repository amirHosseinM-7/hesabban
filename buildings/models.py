from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Unit(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="units")
    number = models.CharField(max_length=10)
    area = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    parking_count = models.PositiveSmallIntegerField(default=0)
    storage_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["building", "number"]
        constraints = [
            models.UniqueConstraint(fields=["building", "number"], name="unique_unit_number_per_building"),
        ]
        indexes = [models.Index(fields=["building"])]

    def __str__(self):
        return f"واحد {self.number}"


class Resident(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "مالک"
        TENANT = "tenant", "مستأجر"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="residents")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.OWNER)
    is_active = models.BooleanField(default=True)
    moved_in = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["unit", "full_name"]
        indexes = [models.Index(fields=["unit", "is_active"])]

    def __str__(self):
        return self.full_name
