from django.contrib import admin

from .models import Building, Unit, Resident

admin.site.register([Building, Unit, Resident])