from django import forms

from buildings.models import Unit
from .models import MaintenanceRequest


class MaintenanceRequestForm(forms.ModelForm):
    unit = forms.ModelChoiceField(queryset=Unit.objects.none(), label="واحد")

    class Meta:
        model = MaintenanceRequest
        fields = ["title", "description", "photo"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "مثلاً نشتی آب در حمام"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "شرح مشکل"}),
        }

