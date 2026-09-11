from django import forms

from buildings.forms import MoneyField, month_choices
from buildings.models import Unit
from buildings.jalali import current_jalali
from .models import ChargeRule


class ChargeRuleForm(forms.ModelForm):
    class Meta:
        model = ChargeRule
        fields = ["title", "kind", "amount", "is_active"]
        widgets = {"title": forms.TextInput(attrs={"placeholder": "مثلاً هزینه آسانسور"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"] = MoneyField(label="مبلغ (تومان)", required=True)


class ManualChargeForm(forms.Form):
    unit = forms.ModelChoiceField(label="واحد", queryset=Unit.objects.none())
    year = forms.IntegerField(label="سال شمسی")
    month = forms.ChoiceField(label="ماه", choices=month_choices())
    title = forms.CharField(label="عنوان", widget=forms.TextInput(attrs={"placeholder": "مثلاً هزینه اضافه نوسازی"}))
    amount = MoneyField(label="مبلغ (تومان)")

    def __init__(self, *args, building=None, **kwargs):
        super().__init__(*args, **kwargs)
        jy, _, _ = current_jalali()
        self.fields["year"].initial = jy
        self.fields["unit"].queryset = Unit.objects.filter(building=building) if building else Unit.objects.none()

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("مبلغ باید بزرگ‌تر از صفر باشد.")
        return amount

    def clean_year(self):
        year = self.cleaned_data.get("year")
        if year is not None and not (1300 <= year <= 1500):
            raise forms.ValidationError("سال نامعتبر است.")
        return year


class ManualChargeEditForm(forms.Form):
    title = forms.CharField(label="عنوان", widget=forms.TextInput(attrs={"placeholder": "عنوان قلم شارژ"}))
    amount = MoneyField(label="مبلغ (تومان)")

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("مبلغ باید بزرگ‌تر از صفر باشد.")
        return amount
