from django.urls import path

from . import views

urlpatterns = [
    path("buildings/<int:building_pk>/payments/", views.payment_list, name="payment_list"),
    path("units/<int:unit_pk>/payments/new/", views.payment_create, name="payment_create"),
    path("units/<int:pk>/finance/", views.unit_finance, name="unit_finance"),
]
