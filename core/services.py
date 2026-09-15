"""
Business-logic layer, kept separate from views on purpose so the
purchase/sale formula and the live-price lookup can be unit-tested
and reused (management command, API, admin action, etc.)
"""
from decimal import Decimal
from django.utils import timezone

from .models import LivePrice, Purchase, Sale, Expense


def get_or_create_today_price(default_manual_price: Decimal = None) -> LivePrice:
    """
    Requirement #1: get today's live price.

    Order of resolution:
      1. Already stored for today -> reuse it (keeps a day's rate consistent).
      2. Try the web scraper (fetch_live_price_from_web). If it fails/returns
         None (no internet, site changed, blocked, etc.) fall back to manual.
      3. If a manual price was supplied by the user, store & use that.
    """
    today = timezone.localdate()
    existing = LivePrice.objects.filter(date=today).first()
    if existing:
        return existing

    price = fetch_live_price_from_web()
    source = "AUTO"
    if price is None:
        price = default_manual_price
        source = "MANUAL"

    if price is None:
        return None  # caller must ask the user to enter a price manually

    return LivePrice.objects.create(date=today, price_per_quintal=price, source=source)


def fetch_live_price_from_web():
    """
    Placeholder scraper. Cotton price feeds are usually behind sites like
    NCDEX / MCX / local mandi (e-NAM) portals that change often and may
    require an API key. Wire your chosen source in here; return None on
    any failure so the app cleanly falls back to manual entry.

    Example (pseudo-code) using requests + BeautifulSoup:

        import requests
        from bs4 import BeautifulSoup
        try:
            resp = requests.get("https://example-mandi-price-source/cotton", timeout=5)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            price_text = soup.select_one(".cotton-price").text  # adjust selector
            return Decimal(price_text.replace(",", "").strip())
        except Exception:
            return None
    """
    return None


def daily_purchase_total(date):
    qs = Purchase.objects.filter(date=date)
    return {
        "date": date,
        "count": qs.count(),
        "total_quantity_kg": sum((p.net_quantity_kg for p in qs), Decimal("0")),
        "gross_amount": sum((p.gross_amount for p in qs), Decimal("0")),
        "deduction_amount": sum((p.deduction_amount for p in qs), Decimal("0")),
        "net_amount": sum((p.net_amount for p in qs), Decimal("0")),
        "purchases": qs,
    }


def daily_sale_total(date):
    qs = Sale.objects.filter(date=date)
    return {
        "date": date,
        "count": qs.count(),
        "total_amount": sum((s.total_amount for s in qs), Decimal("0")),
        "sales": qs,
    }


def totals_between(start_date, end_date):
    """Requirement #3: monthly / custom date-range totals for purchases, sales, expenses, profit."""
    purchases = Purchase.objects.filter(date__range=(start_date, end_date))
    sales = Sale.objects.filter(date__range=(start_date, end_date))
    expenses = Expense.objects.filter(date__range=(start_date, end_date))

    total_purchase_amount = sum((p.net_amount for p in purchases), Decimal("0"))
    total_sale_amount = sum((s.total_amount for s in sales), Decimal("0"))
    total_expenses = sum((e.amount for e in expenses), Decimal("0"))

    # Requirement #7: profit = sales - purchases - other operating expenses
    profit = total_sale_amount - total_purchase_amount - total_expenses

    return {
        "start_date": start_date,
        "end_date": end_date,
        "purchases": purchases,
        "sales": sales,
        "expenses": expenses,
        "total_purchase_amount": total_purchase_amount,
        "total_sale_amount": total_sale_amount,
        "total_expenses": total_expenses,
        "profit": profit,
    }
