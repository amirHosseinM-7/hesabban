from django.contrib import admin

from .models import Allocation, Payment

admin.site.register([Payment, Allocation])