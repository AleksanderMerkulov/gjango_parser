from decimal import Decimal
from django import forms
from .models import MarketInstrumentSnapshot, Products


class SnapshotFilterForm(forms.Form):
    date_from = forms.DateField(
        label="Дата с",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label="Дата по",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    instrument_codes = forms.MultipleChoiceField(
        label="Инструменты",
        required=False,
        widget=forms.SelectMultiple(attrs={"size": "8", "class":"form-control"}),
        choices=(),
    )

    price_from = forms.DecimalField(
        label="РынЦена от",
        required=False,
        max_digits=20,
        decimal_places=6,
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={"step": "10000.00"}),
    )
    price_to = forms.DecimalField(
        label="РынЦена до",
        required=False,
        max_digits=20,
        decimal_places=6,
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={"step": "10000.00"}),
    )

    product = forms.ChoiceField(
        label="Товар",
        required=False,
        choices=(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instruments = (
            MarketInstrumentSnapshot.objects
            .values_list("instrument_code", "instrument_name")
            .distinct()
            .order_by("instrument_code")
        )
        self.fields["instrument_codes"].choices = [
            (code, f"{code} — {name}") for code, name in instruments
        ]

        products = (
            Products.objects
            .values_list("name", flat=True)
            .distinct()
            .order_by("name")
        )
        self.fields["product"].choices = [("", "любой")] + [(p, p) for p in products]

    def clean(self):
        cleaned = super().clean()
        d1, d2 = cleaned.get("date_from"), cleaned.get("date_to")
        p1, p2 = cleaned.get("price_from"), cleaned.get("price_to")

        if d1 and d2 and d1 > d2:
            self.add_error("date_to", "Дата по должна быть не раньше даты с.")

        if p1 is not None and p2 is not None and p1 > p2:
            self.add_error("price_to", "Цена до должна быть не меньше цены от.")

        return cleaned


class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Products
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": ""})
        }
