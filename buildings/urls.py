from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("buildings/new/", views.building_create, name="building_create"),
    path("buildings/<int:pk>/", views.building_dashboard, name="building_dashboard"),
    path("buildings/<int:pk>/units/", views.unit_list, name="unit_list"),
    path("buildings/<int:building_pk>/units/new/", views.unit_create, name="unit_create"),
    path("units/<int:pk>/edit/", views.unit_edit, name="unit_edit"),
    path("units/<int:pk>/delete/", views.unit_delete, name="unit_delete"),
    path("units/<int:unit_pk>/residents/new/", views.resident_create, name="resident_create"),
    path("residents/<int:pk>/edit/", views.resident_edit, name="resident_edit"),
    path("residents/<int:pk>/delete/", views.resident_delete, name="resident_delete"),
]
