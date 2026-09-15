from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("live-price/", views.set_live_price, name="set_live_price"),

    path("purchases/new/", views.purchase_create, name="purchase_create"),
    path("purchases/", views.purchase_list, name="purchase_list"),

    path("sales/new/", views.sale_create, name="sale_create"),
    path("sales/", views.sale_list, name="sale_list"),

    path("expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/", views.expense_list, name="expense_list"),

    path("reports/", views.report_range, name="report_range"),
]
