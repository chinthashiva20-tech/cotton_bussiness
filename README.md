# Cotton Trade Manager (Django)

A small-scale cotton purchase/sale management app.

## What's inside

| Requirement | Where it's implemented |
|---|---|
| 1. Live price | `core.LivePrice` model + `core/views.set_live_price` (manual) and `core.services.fetch_live_price_from_web()` (scraper stub — plug in requests/BeautifulSoup or an API) |
| 2. Daily purchase totals | `core.services.daily_purchase_total()`, shown on Dashboard and Purchase list (filter by date) |
| 3. Monthly / custom range totals | `/reports/` page — pick any start/end date |
| 4. Manual data entry with computed purchase price | `core/views.purchase_create` + `Purchase.compute()` |
| 5. Daily/monthly sales | `Sale` model, `/sales/` list (filter by date), included in `/reports/` |
| 6. Extra costs (shop rent, vehicle rent, labour, loading) | `Expense` model, `/expenses/` |
| 7. Profit calculation | `core.services.totals_between()`: `profit = sales − purchases(net) − expenses` |
| 8. KG or Quintal units | `unit` field on Purchase/Sale (`KG` / `QUINTAL`), conversion helpers `to_kg()` / `to_quintal()` in `core/models.py` |
| 9. Purchase formula (cash-cutting + bag tare) | `Purchase.compute()` in `core/models.py`, constants tunable in Django Admin → **Business Settings** |
| 10. End-to-end Django project | This repo |

## The purchase formula (requirement 9)

```
net_weight_kg = entered_quantity_kg - (num_bags * tare_weight_per_bag_kg)   # default tare = 0.5 kg/bag
net_quintals  = net_weight_kg / 100
gross_amount  = net_quintals * live_price_per_quintal
deduction     = floor(gross_amount / 1000) * 50      # Rs.50 cut per Rs.1000 of gross — both configurable
net_amount    = gross_amount - deduction              # <- amount actually paid to the client
```

All three constants (`1000`, `50`, `0.5 kg`) live in **Django Admin → Business Settings**, so you (the developer/owner) can retune the formula without touching code. Each saved `Purchase` snapshots the numbers it used, so changing settings later never rewrites historical records.

Each bag is entered as part of one `Purchase` row via `num_bags` — if a farmer brings 3 separate bags weighed one at a time, either:
- enter 3 separate `Purchase` rows (one per bag, `num_bags=1` each), or
- enter one row with the summed weight and `num_bags=3` (tare is multiplied by bag count either way).

## Setup

```bash
python -m venv venv
source venv/bin/activate         # venv\Scripts\activate on Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit:
- `http://127.0.0.1:8000/` — dashboard
- `http://127.0.0.1:8000/admin/` — admin (manage Business Settings, Clients, Buyers, all records)

First-time setup in Admin:
1. Go to **Business Settings** and confirm/edit the deduction and tare values.
2. Go to **Live Price** → add today's price (or use the "Live Price" nav link).
3. Start entering purchases/sales/expenses from the nav bar.

## Wiring a real live-price feed

`core/services.py::fetch_live_price_from_web()` is a stub that currently returns `None` (so the app always falls back to manual entry). Cotton price sources (NCDEX, MCX, e-NAM mandi portals) vary by state and usually need either an API key or HTML scraping that breaks when the site changes — so this is left as an integration point rather than hardcoded. Fill in the function body per the example in its docstring, add `requests`/`beautifulsoup4` to `requirements.txt`, and the rest of the app (dashboard, purchase form pre-fill) will pick it up automatically once a price is saved for the day.

## Suggested next steps

- Add login/auth (`django.contrib.auth`) if more than one person will use this.
- Add CSV/Excel export on the `/reports/` page (e.g. via `openpyxl`) for sharing with an accountant.
- Add a `Bag` model instead of a single `num_bags` count, if you need per-bag weight and moisture notes.
- Deploy with `DEBUG=False`, a real `SECRET_KEY` from an env var, and Postgres instead of SQLite for production use.
