from django import forms

from buildings.forms import JalaliDateField, MoneyField
from .models import Payment


class PaymentForm(forms.Form):
    amount = MoneyField(label="مبلغ (تومان)")
    date = JalaliDateField(label="تاریخ پرداخت")
    method = forms.ChoiceField(label="روش پرداخت", choices=Payment.Method.choices)
    note = forms.CharField(label="یادداشت", required=False, widget=forms.TextInput())
