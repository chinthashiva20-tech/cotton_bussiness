from django import forms
from .models import Purchase, Sale, Expense, LivePrice, Client, Buyer


class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


class LivePriceForm(forms.ModelForm):
    class Meta:
        model = LivePrice
        fields = ["date", "price_per_quintal"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class PurchaseForm(forms.ModelForm):
    client_name = forms.CharField(max_length=150, help_text="Type a new or existing client name.")

    class Meta:
        model = Purchase
        fields = ["date", "quantity", "unit", "num_bags", "live_price_per_quintal", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def save(self, commit=True):
        client, _ = Client.objects.get_or_create(name=self.cleaned_data["client_name"].strip())
        purchase = super().save(commit=False)
        purchase.client = client
        if commit:
            purchase.save()
        return purchase


class SaleForm(forms.ModelForm):
    buyer_name = forms.CharField(max_length=150, help_text="Type a new or existing buyer/industry name.")

    class Meta:
        model = Sale
        fields = ["date", "quantity", "unit", "price_per_quintal", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def save(self, commit=True):
        buyer, _ = Buyer.objects.get_or_create(name=self.cleaned_data["buyer_name"].strip())
        sale = super().save(commit=False)
        sale.buyer = buyer
        if commit:
            sale.save()
        return sale


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["date", "expense_type", "amount", "description"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
