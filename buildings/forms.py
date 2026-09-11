import datetime
from decimal import Decimal

from django import forms

from buildings.jalali import (
    JALALI_MONTHS,
    format_jalali,
    parse_jalali,
    to_en_digits,
    to_fa_digits,
)
from .models import Building, Resident, Unit


class JalaliDateField(forms.Field):
    """Date field that accepts and displays Jalali dates as ۱۴۰۴/۰۵/۱۲."""

    def __init__(self, **kwargs):
        kwargs.setdefault("widget", forms.TextInput(
            attrs={"inputmode": "numeric", "placeholder": "۱۴۰۴/۰۵/۱۲", "dir": "ltr"}
        ))
        super().__init__(**kwargs)

    def to_python(self, value):
        if value in (None, ""):
            return None
        try:
            return parse_jalali(value)
        except ValueError:
            raise forms.ValidationError("تاریخ نامعتبر است. نمونه صحیح: ۱۴۰۴/۰۵/۱۲")

    def prepare_value(self, value):
        if isinstance(value, datetime.date):
            return to_fa_digits(format_jalali(value))
        return value


class MoneyField(forms.CharField):
    """Money field accepting Persian or Latin digits."""

    def to_python(self, value):
        value = to_en_digits(value or "").replace(",", "").replace("،", "").strip()
        if value == "":
            return None
        try:
            return Decimal(value)
        except Exception:
            raise forms.ValidationError("مبلغ نامعتبر است.")


def month_choices():
    return [(i + 1, name) for i, name in enumerate(JALALI_MONTHS)]


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ["name", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "مثلاً برج نگین"}),
            "address": forms.TextInput(attrs={"placeholder": "نشانی ساختمان"}),
        }


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["number", "area", "parking_count", "storage_count"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["number"].widget.attrs.update({"placeholder": "مثلاً ۴", "dir": "ltr"})


class ResidentForm(forms.ModelForm):
    moved_in = JalaliDateField(label="تاریخ سکونت", required=False)

    class Meta:
        model = Resident
        fields = ["full_name", "phone", "role", "is_active", "moved_in"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].widget.attrs["placeholder"] = "نام و نام خانوادگی"
        self.fields["phone"].widget.attrs["placeholder"] = "۰۹۱۲..."
