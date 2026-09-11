from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("buildings.urls")),
    path("billing/", include("charges.urls")),
    path("payments/", include("payments.urls")),
    path("expenses/", include("expenses.urls")),
    path("ledger/", include("ledger.urls")),
    path("maintenance/", include("maintenance.urls")),
    path("invoices/", include("invoices.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
