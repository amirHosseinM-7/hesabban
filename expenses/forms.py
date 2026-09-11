from django import forms

from buildings.forms import JalaliDateField, MoneyField, month_choices
from .models import Expense


class ExpenseForm(forms.ModelForm):
    amount = MoneyField(label="مبلغ (تومان)")
    date = JalaliDateField(label="تاریخ")
    vendor = forms.CharField(label="پرداخت‌کننده / فروشنده", required=False)
    reference_number = forms.CharField(label="شماره پیگیری", required=False)
    attachment = forms.FileField(label="پیوست", required=False)

    class Meta:
        model = Expense
        fields = ["category", "title", "vendor", "amount", "date", "payment_method", "reference_number", "attachment", "note"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "مثلاً قبض برق مرداد"}),
            "note": forms.TextInput(attrs={"placeholder": "یادداشت"}),
        }

