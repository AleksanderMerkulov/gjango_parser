from django.db import models


class MarketInstrumentSnapshot(models.Model):
    instrument_code = models.CharField("КодИнструмента", max_length=64, db_index=True)
    instrument_name = models.CharField("НаименованиеИнструмента", max_length=511)

    delivery_basis = models.CharField("БазисПоставки", max_length=128, blank=True, null=True)

    contracts_volume_ei = models.DecimalField(
        "ОбъемДоговоровЕИ", max_digits=20, decimal_places=6, blank=True, null=True
    )
    contracts_volume_rub = models.DecimalField(
        "ОбъемДоговоровРуб", max_digits=20, decimal_places=2, blank=True, null=True
    )

    market_change_rub = models.DecimalField(
        "ИзмРынРуб", max_digits=20, decimal_places=2, blank=True, null=True
    )
    market_change_pct = models.DecimalField(
        "ИзмРынПроц", max_digits=8, decimal_places=4, blank=True, null=True
    )

    min_price = models.DecimalField("МинЦена", max_digits=20, decimal_places=6, blank=True, null=True)
    avg_price = models.DecimalField("СреднЦена", max_digits=20, decimal_places=6, blank=True, null=True)
    max_price = models.DecimalField("МаксЦена", max_digits=20, decimal_places=6, blank=True, null=True)
    market_price = models.DecimalField("РынЦена", max_digits=20, decimal_places=6, blank=True, null=True)

    best_offer = models.DecimalField("ЛучшПредложение", max_digits=20, decimal_places=6, blank=True, null=True)
    best_bid = models.DecimalField("ЛучшСпрос", max_digits=20, decimal_places=6, blank=True, null=True)

    contracts_count = models.PositiveIntegerField("КоличествоДоговоров", blank=True, null=True)

    date = models.DateField("Дата", db_index=True)

    product = models.CharField("Товар", max_length=255)

    class Meta:
        verbose_name = "Единица торгов"
        verbose_name_plural = "Данные торгов"
        constraints = [
            models.UniqueConstraint(
                fields=["instrument_code", "instrument_name", "date"],
                name="uq_instrument_date_product",
            )
        ]

    def __str__(self) -> str:
        return f"{self.instrument_code} ({self.date})"


class Products(models.Model):
    name = models.CharField(verbose_name='Ресурс', max_length=255)
