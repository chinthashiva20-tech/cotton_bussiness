from django.contrib import admin
from .models import BusinessSettings, LivePrice, Client, Buyer, Purchase, Sale, Expense


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ("deduction_block_value", "deduction_amount_per_block", "tare_weight_per_bag_kg", "updated_at")

    def has_add_permission(self, request):
        # singleton row only
        return not BusinessSettings.objects.exists()


@admin.register(LivePrice)
class LivePriceAdmin(admin.ModelAdmin):
    list_display = ("date", "price_per_quintal", "source")
    list_filter = ("source",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    search_fields = ("name", "phone", "village")


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    search_fields = ("name", "phone", "location")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("date", "client", "quantity", "unit", "num_bags", "live_price_per_quintal", "net_quantity_kg", "gross_amount", "deduction_amount", "net_amount")
    list_filter = ("date", "unit")
    readonly_fields = ("tare_weight_used_kg", "net_quantity_kg", "gross_amount", "deduction_amount", "net_amount")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("date", "buyer", "quantity", "unit", "price_per_quintal", "total_amount")
    list_filter = ("date", "unit")
    readonly_fields = ("total_amount",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "expense_type", "amount", "description")
    list_filter = ("expense_type", "date")
