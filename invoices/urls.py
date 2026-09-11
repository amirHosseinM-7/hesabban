from django.urls import path

from . import views

urlpatterns = [
    path("charge/<int:pk>.pdf", views.charge_invoice_pdf, name="charge_invoice_pdf"),
    path("receipt/<int:pk>.pdf", views.payment_receipt_pdf, name="payment_receipt_pdf"),
    path("export/payments/<int:building_pk>.xlsx", views.payments_xlsx, name="payments_xlsx"),
    path("export/expenses/<int:building_pk>.xlsx", views.expenses_xlsx, name="expenses_xlsx"),
]
