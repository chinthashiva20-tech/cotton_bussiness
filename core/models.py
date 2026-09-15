from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


UNIT_CHOICES = [
    ("KG", "Kilogram"),
    ("QUINTAL", "Quintal (100 KG)"),
]

EXPENSE_TYPE_CHOICES = [
    ("SHOP_RENT", "Shop Rent"),
    ("VEHICLE_RENT", "Vehicle Rent"),
    ("LABOUR", "Labour Cost"),
    ("LOADING", "Loading/Unloading"),
    ("OTHER", "Other"),
]

KG_PER_QUINTAL = Decimal("100")


def to_quintal(quantity: Decimal, unit: str) -> Decimal:
    """Normalize any entered quantity to Quintals (the unit the live price is quoted in)."""
    if unit == "KG":
        return quantity / KG_PER_QUINTAL
    return quantity


def to_kg(quantity: Decimal, unit: str) -> Decimal:
    if unit == "QUINTAL":
        return quantity * KG_PER_QUINTAL
    return quantity


class BusinessSettings(models.Model):
    """
    Singleton table holding the tunable formula constants so the
    deduction/bag-tare logic can be changed without touching code.
    """
    # Cash-cutting logic: for every `deduction_block_value` rupees of gross
    # amount, cut `deduction_amount_per_block` rupees. Example from spec: per 1000 -> 50.
    deduction_block_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1000.00"))
    deduction_amount_per_block = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("50.00"))

    # Bag tare weight: subtracted per bag from the gross quantity before pricing.
    tare_weight_per_bag_kg = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("0.500"))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Setting"
        verbose_name_plural = "Business Settings"

    def __str__(self):
        return "Business Settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class LivePrice(models.Model):
    """
    One cotton price per day, quoted per Quintal.
    Can be set manually from admin/UI, or fetched by a scraper (see services.py)
    and stored here so every purchase/sale that day reuses the same figure.
    """
    date = models.DateField(unique=True, default=timezone.localdate)
    price_per_quintal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    source = models.CharField(
        max_length=20,
        choices=[("MANUAL", "Manual Entry"), ("AUTO", "Fetched Automatically")],
        default="MANUAL",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} - Rs.{self.price_per_quintal}/quintal ({self.source})"


class Client(models.Model):
    """The farmer/seller we buy cotton from."""
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, blank=True)
    village = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name


class Buyer(models.Model):
    """The industry/mill we sell cotton to."""
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name


class Purchase(models.Model):
    """
    A single purchase transaction (one client, possibly multiple bags,
    entered on a given date). Implements requirement #9's formula:

        net_weight     = entered_quantity - (num_bags * tare_weight_per_bag)
        net_quintals   = net_weight converted to quintals
        gross_amount   = net_quintals * live_price_per_quintal
        deduction      = floor(gross_amount / deduction_block_value) * deduction_amount_per_block
        net_amount     = gross_amount - deduction   <-- what is actually paid to the client
    """
    date = models.DateField(default=timezone.localdate)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="purchases")

    quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Quantity as weighed, before bag-tare deduction.")
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="KG")
    num_bags = models.PositiveIntegerField(default=1)

    live_price_per_quintal = models.DecimalField(max_digits=10, decimal_places=2)

    # Snapshot fields — computed once at save() and stored, so historical
    # records never change even if BusinessSettings is edited later.
    tare_weight_used_kg = models.DecimalField(max_digits=6, decimal_places=3, editable=False, default=0)
    net_quantity_kg = models.DecimalField(max_digits=10, decimal_places=3, editable=False, default=0)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)

    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def compute(self, settings_obj: "BusinessSettings" = None):
        """Runs the requirement-#9 formula and fills the snapshot fields."""
        settings_obj = settings_obj or BusinessSettings.load()

        qty_kg = to_kg(Decimal(self.quantity), self.unit)
        tare = Decimal(self.num_bags) * settings_obj.tare_weight_per_bag_kg
        net_kg = qty_kg - tare
        if net_kg < 0:
            net_kg = Decimal("0")

        net_quintals = net_kg / KG_PER_QUINTAL
        gross = (net_quintals * self.live_price_per_quintal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        blocks = int(gross // settings_obj.deduction_block_value) if settings_obj.deduction_block_value else 0
        deduction = (Decimal(blocks) * settings_obj.deduction_amount_per_block).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        net_amount = gross - deduction

        self.tare_weight_used_kg = tare
        self.net_quantity_kg = net_kg
        self.gross_amount = gross
        self.deduction_amount = deduction
        self.net_amount = net_amount

    def save(self, *args, **kwargs):
        self.compute()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} | {self.client} | {self.quantity}{self.unit} -> Rs.{self.net_amount}"


class Sale(models.Model):
    """A sale of cotton to a buyer/industry."""
    date = models.DateField(default=timezone.localdate)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, related_name="sales")

    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="QUINTAL")
    price_per_quintal = models.DecimalField(max_digits=10, decimal_places=2)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)

    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def compute(self):
        quintals = to_quintal(Decimal(self.quantity), self.unit)
        self.total_amount = (quintals * self.price_per_quintal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.compute()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} | {self.buyer} | {self.quantity}{self.unit} -> Rs.{self.total_amount}"


class Expense(models.Model):
    """
    Requirement #6: shop rent, vehicle rent, labour, loading charges,
    and any other 'extra' cost while procuring/supplying goods.
    """
    date = models.DateField(default=timezone.localdate)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)

    # optional link so an expense can be tied to a specific purchase/sale
    related_purchase = models.ForeignKey(Purchase, null=True, blank=True, on_delete=models.SET_NULL, related_name="expenses")
    related_sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL, related_name="expenses")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} | {self.get_expense_type_display()} | Rs.{self.amount}"
