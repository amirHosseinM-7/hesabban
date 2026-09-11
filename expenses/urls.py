from django.urls import path

from . import views

urlpatterns = [
    path("buildings/<int:building_pk>/expenses/", views.expense_list, name="expense_list"),
    path("buildings/<int:building_pk>/expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
]
