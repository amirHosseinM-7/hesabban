from django.urls import path

from . import views

urlpatterns = [
    path("buildings/<int:building_pk>/payments/", views.payment_list, name="payment_list"),
    path("units/<int:unit_pk>/payments/new/", views.payment_create, name="payment_create"),
    path("<int:pk>/edit/", views.payment_edit, name="payment_edit"),
    path("<int:pk>/void/", views.payment_void, name="payment_void"),
    path("units/<int:pk>/finance/", views.unit_finance, name="unit_finance"),
]
