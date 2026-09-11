from django.urls import path

from . import views

urlpatterns = [
    path("buildings/<int:building_pk>/ledger/", views.ledger_list, name="ledger_list"),
]
