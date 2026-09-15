from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from .models import LivePrice, Purchase, Sale, Expense
from .forms import PurchaseForm, SaleForm, ExpenseForm, LivePriceForm, DateRangeForm
from . import services


def dashboard(request):
    today = timezone.localdate()
    day_purchases = services.daily_purchase_total(today)
    day_sales = services.daily_sale_total(today)
    today_price = LivePrice.objects.filter(date=today).first()
    context = {
        "today": today,
        "day_purchases": day_purchases,
        "day_sales": day_sales,
        "today_price": today_price,
    }
    return render(request, "core/dashboard.html", context)


# ---------------- Live Price (Requirement #1) ----------------

def set_live_price(request):
    today = timezone.localdate()
    instance = LivePrice.objects.filter(date=today).first()
    if request.method == "POST":
        form = LivePriceForm(request.POST, instance=instance)
        if form.is_valid():
            lp = form.save(commit=False)
            lp.source = "MANUAL"
            lp.save()
            messages.success(request, f"Live price for {lp.date} set to Rs.{lp.price_per_quintal}/quintal.")
            return redirect("dashboard")
    else:
        form = LivePriceForm(instance=instance, initial={"date": today})
    return render(request, "core/live_price_form.html", {"form": form})


# ---------------- Purchases (Requirements #2, #4, #8, #9) ----------------

def purchase_create(request):
    today = timezone.localdate()
    today_price = LivePrice.objects.filter(date=today).first()

    if request.method == "POST":
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save()  # compute() runs automatically inside model.save()
            messages.success(
                request,
                f"Purchase saved. Net amount payable to {purchase.client}: Rs.{purchase.net_amount} "
                f"(gross Rs.{purchase.gross_amount} minus deduction Rs.{purchase.deduction_amount})."
            )
            return redirect("purchase_list")
    else:
        initial = {"date": today}
        if today_price:
            initial["live_price_per_quintal"] = today_price.price_per_quintal
        form = PurchaseForm(initial=initial)

    return render(request, "core/purchase_form.html", {"form": form, "today_price": today_price})


def purchase_list(request):
    date_str = request.GET.get("date")
    if date_str:
        qs = Purchase.objects.filter(date=date_str)
        selected_date = date_str
    else:
        selected_date = timezone.localdate()
        qs = Purchase.objects.filter(date=selected_date)

    totals = {
        "gross_amount": sum((p.gross_amount for p in qs), Decimal("0")),
        "deduction_amount": sum((p.deduction_amount for p in qs), Decimal("0")),
        "net_amount": sum((p.net_amount for p in qs), Decimal("0")),
        "net_quantity_kg": sum((p.net_quantity_kg for p in qs), Decimal("0")),
    }
    return render(request, "core/purchase_list.html", {"purchases": qs, "totals": totals, "selected_date": selected_date})


# ---------------- Sales (Requirement #5) ----------------

def sale_create(request):
    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save()
            messages.success(request, f"Sale saved. Total amount: Rs.{sale.total_amount}")
            return redirect("sale_list")
    else:
        form = SaleForm(initial={"date": timezone.localdate()})
    return render(request, "core/sale_form.html", {"form": form})


def sale_list(request):
    date_str = request.GET.get("date")
    if date_str:
        qs = Sale.objects.filter(date=date_str)
        selected_date = date_str
    else:
        selected_date = timezone.localdate()
        qs = Sale.objects.filter(date=selected_date)

    total_amount = sum((s.total_amount for s in qs), Decimal("0"))
    return render(request, "core/sale_list.html", {"sales": qs, "total_amount": total_amount, "selected_date": selected_date})


# ---------------- Expenses (Requirement #6) ----------------

def expense_create(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense recorded.")
            return redirect("expense_list")
    else:
        form = ExpenseForm(initial={"date": timezone.localdate()})
    return render(request, "core/expense_form.html", {"form": form})


def expense_list(request):
    qs = Expense.objects.all()[:200]
    total = sum((e.amount for e in Expense.objects.all()), Decimal("0"))
    return render(request, "core/expense_list.html", {"expenses": qs, "total": total})


# ---------------- Reports: monthly / custom range + profit (Requirements #3, #7) ----------------

def report_range(request):
    today = timezone.localdate()
    start_date, end_date = today.replace(day=1), today

    if request.method == "GET" and request.GET.get("start_date"):
        form = DateRangeForm(request.GET)
        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
    else:
        form = DateRangeForm(initial={"start_date": start_date, "end_date": end_date})

    data = services.totals_between(start_date, end_date)
    return render(request, "core/report_range.html", {"form": form, "data": data})
