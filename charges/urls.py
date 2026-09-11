from django.urls import path

from . import views

urlpatterns = [
    path("buildings/<int:building_pk>/rules/", views.rule_list, name="rule_list"),
    path("buildings/<int:building_pk>/rules/new/", views.rule_create, name="rule_create"),
    path("rules/<int:pk>/edit/", views.rule_edit, name="rule_edit"),
    path("rules/<int:pk>/delete/", views.rule_delete, name="rule_delete"),
    path("buildings/<int:building_pk>/billing/", views.billing, name="billing"),
    path("buildings/<int:building_pk>/billing/generate/", views.billing_generate, name="billing_generate"),
    path("buildings/<int:building_pk>/charges/", views.charge_list, name="charge_list"),
    path("buildings/<int:building_pk>/charges/new/", views.charge_create, name="charge_create"),
    path("charges/<int:pk>/edit/", views.charge_edit, name="charge_edit"),
    path("charges/<int:pk>/cancel/", views.charge_cancel, name="charge_cancel"),
]
