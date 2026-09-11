from django.urls import path

from . import views

urlpatterns = [
    path("buildings/<int:building_pk>/maintenance/", views.maintenance_list, name="maintenance_list"),
    path("requests/<int:pk>/status/", views.maintenance_status, name="maintenance_status"),
]
