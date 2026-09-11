from django.contrib import admin

from .models import Charge, ChargeItem, ChargeRule

admin.site.register([Charge, ChargeItem, ChargeRule])