import os
from decimal import Decimal, InvalidOperation
from itertools import product

import requests
from django.db import transaction
from django.shortcuts import render, redirect
import pandas as pd
from datetime import date, timedelta
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Products
from .forms import ProductCreateForm,SnapshotFilterForm
from django.views.generic import ListView


from django_parser.models import MarketInstrumentSnapshot


def generate_dates(days: int = 10, direction: str = "past", start: date | None = None):
    """
    Генерирует даты, начиная со start (по умолчанию сегодня), включая start и days.
    """

    start = date.today()

    step = -1 if direction == "past" else 1
    for i in range(days + 1):
        yield start + timedelta(days=step * i)

def build_ts(d) -> str:
    return f"{d:%Y%m%d}"


def find_row_index_by_marker_xls(
    xls_path: str,
    marker: str = "Единица измерения: Метрическая тонна".lower(),
    sheet: int | str = 0,
    column: str = "B",
    start_index: int = 0,
    contains: bool = False,
) -> int | None:

    col_idx = ord(column.upper()) - ord("A")

    df = pd.read_excel(xls_path, sheet_name=sheet, header=None, engine="xlrd")

    # Берём нужную колонку, приводим к строке и lower()
    s = (
        df.iloc[start_index:, col_idx]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    m = marker.strip().lower()
    matches = s.str.contains(m, na=False) if contains else (s == m)
    if matches.any():
        return int(matches.idxmax())  # индекс первой найденной строки
    return None

def dash_to_none(v: any):
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if s in {"-", ""}:
            return None
        return s
    return v


def to_decimal(v: any):
    v = dash_to_none(v)
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))

    s = str(v).strip()
    s = s.replace(" ", "").replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Некорректное decimal значение: {v!r}") from e


def to_int(v: any):
    v = dash_to_none(v)
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip().replace(" ", "")
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(f"Некорректное int значение: {v!r}") from e



@transaction.atomic
def upsert_snapshot(row: dict[str, any], date_create):
    row = row[1]
    instrument_code = row[1]
    instrument_name = row[2]
    dt = date_create

    if not instrument_code or not instrument_name or dt is None:
        raise ValueError(
            "Обязательные поля instrument_code, instrument_name, date должны быть заданы"
        )

    product_name = row[2].split(",")[0]

    defaults = {
        "delivery_basis": dash_to_none(row[3]),
        "contracts_volume_ei": to_decimal(row[4]),
        "contracts_volume_rub": to_decimal(row[5]),
        "market_change_rub": to_decimal(row[6]),
        "market_change_pct": to_decimal(row[7]),
        "min_price": to_decimal(row[8]),
        "avg_price": to_decimal(row[9]),
        "max_price": to_decimal(row[10]),
        "market_price": to_decimal(row[11]),
        "best_offer": to_decimal(row[12]),
        "best_bid": to_decimal(row[13]),
        "contracts_count": to_int(row[14]),
        "product": product_name,
    }

    obj, created = MarketInstrumentSnapshot.objects.update_or_create(
        instrument_code=instrument_code,
        instrument_name=instrument_name,
        date=dt,
        defaults=defaults,
    )
    return obj, created


def parser(request):

    dates = generate_dates(10)
    for d in dates:
        date_formated = build_ts(d)
        r = requests.get(f'https://spimex.com/files/trades/result/upload/reports/oil_xls/oil_xls_{date_formated}162000.xls')
        if r.status_code == 200:
            print(f'{r.status_code}: {d}: файл получен')
            os.makedirs('download', exist_ok=True)
            filename = f"oil_xls_{date_formated}162000.xls"
            out_path = os.path.join('download', filename)

            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

            start_parse_index = find_row_index_by_marker_xls(out_path) + 4
            end_parse_index = find_row_index_by_marker_xls(out_path,
                                                           marker='Итого:'.lower(),
                                                           start_index=start_parse_index)
            print(f'{start_parse_index} {end_parse_index}')


            df = pd.read_excel(out_path, sheet_name=0, header=None, engine="xlrd")
            selected_data = df.iloc[start_parse_index:end_parse_index]

            for row in selected_data.iterrows():
                snapshot, created = upsert_snapshot(row, d)
        else:
            print(f'{r.status_code}: {d}')
    return redirect(reverse_lazy('home'))
    # return render(request, 'parser_page.html')

class SnapshotListView(ListView):
    model = MarketInstrumentSnapshot
    template_name = "main_page.html"
    context_object_name = "rows"
    paginate_by = 50

    ALLOWS_TO_FILTER = [
        "КодИнструмента", "НаименованиеИнструмента", "БазисПоставки"
    ]

    def get_attr_name_by_rus_name(self, sort_name_rus, prefix):
        """
         Возвращает английское название атрибута для фильтра
         """
        if sort_name_rus == "БазисПоставки":
            return f"{prefix}delivery_basis"
        elif sort_name_rus == "КодИнструмента":
            return f"{prefix}instrument_code"
        elif sort_name_rus == "НаименованиеИнструмента":
            return f"{prefix}instrument_name"
        elif sort_name_rus == "ОбъемДоговоровЕИ":
            return f"{prefix}contracts_volume_ei"
        elif sort_name_rus == "ОбъемДоговоровРуб":
            return f"{prefix}contracts_volume_rub"
        elif sort_name_rus == "ИзмРынРуб":
            return f"{prefix}market_change_rub"
        elif sort_name_rus == "ИзмРынПроц":
            return f"{prefix}market_change_pct"
        elif sort_name_rus == "МинЦена":
            return f"{prefix}min_price"
        elif sort_name_rus == "СреднЦена":
            return f"{prefix}avg_price"
        elif sort_name_rus == "МаксЦена":
            return f"{prefix}max_price"
        elif sort_name_rus == "РынЦена":
            return f"{prefix}market_price"
        elif sort_name_rus == "КоличествоДоговоров":
            return f"{prefix}contracts_count"
        else:
            return f"date"

    def get_queryset(self):
        qs = MarketInstrumentSnapshot.objects.all()

        self.filter_form = SnapshotFilterForm(self.request.GET or None)
        if self.filter_form.is_valid():
            cd = self.filter_form.cleaned_data

            if cd.get("date_from"):
                qs = qs.filter(date__gte=cd["date_from"])
            if cd.get("date_to"):
                qs = qs.filter(date__lte=cd["date_to"])

            if cd.get("instrument_codes"):
                qs = qs.filter(instrument_code__in=cd["instrument_codes"])

            if cd.get("product"):
                qs = qs.filter(product__contains=cd["product"])

            # Диапазон по рыночной цене (market_price)
            # Если задан диапазон — отсекаем NULL, чтобы фильтр был предсказуемым
            if cd.get("price_from") is not None:
                qs = qs.filter(market_price__isnull=False, market_price__gte=cd["price_from"])
            if cd.get("price_to") is not None:
                qs = qs.filter(market_price__isnull=False, market_price__lte=cd["price_to"])

        # Сортировка
        sort = self.request.GET.get("sort") or "date"
        direction = self.request.GET.get("dir") or "max"



        prefix = "-" if direction == "max" else ""
        sort_name = self.get_attr_name_by_rus_name(sort, prefix)
        qs = qs.order_by(sort_name, "instrument_code")

        self.current_sort = sort
        self.current_dir = direction
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["labels"] = ["КодИнструмента", "НаименованиеИнструмента", "БазисПоставки", "ОбъемДоговоровЕИ",
                         "ОбъемДоговоровРуб", "ИзмРынРуб", "ИзмРынПроц", "МинЦена", "СреднЦена", "МаксЦена",
                         "РынЦена", "ЛучшПредложение", "ЛучшСпрос", "КоличествоДоговоров", "Дата", "Товар"]
        ctx["filter_form"] = self.filter_form
        ctx["current_sort"] = getattr(self, "current_sort", "date")
        ctx["current_dir"] = getattr(self, "current_dir", "desc")
        return ctx



class ProductCreateView(CreateView):
    model = Products
    form_class = ProductCreateForm
    template_name = "add_product.html"
    success_url = reverse_lazy("add_product")



