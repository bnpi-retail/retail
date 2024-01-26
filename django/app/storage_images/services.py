import io
import csv
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from os import getenv
from datetime import datetime
from matplotlib.ticker import FuncFormatter
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class DataFunction:
    def __init__(self):
        pass

    def data_sorted(self, data: dict) -> None:
        sorted_data = sorted(set(zip(data["dates"], data["values"])), key=lambda x: x[0])
        sorted_dates, sorted_values = zip(*sorted_data)
        data["dates"] = sorted_dates
        data["values"] = sorted_values
    
    def data_merge(self, data: dict, zero_data: dict) -> None:
        data["dates"].extend(zero_data["dates"])
        data["values"].extend(zero_data["values"])

    def data_group(self, data, mean=False, sum_group=False) -> None:
        df = pd.DataFrame({'dates': pd.to_datetime(data["dates"]), 'values': data["values"]})
        df.set_index('dates', inplace=True)

        if mean == True:
            grouped_data = df.resample('W-Mon').mean()
        elif sum_group == True:
            grouped_data = df.resample('W-Mon').sum()
        else:
            grouped_data = df.resample('D').sum()
        
        dates = grouped_data.index.strftime('%Y-%m-%d').tolist()

        data["dates"] = pd.to_datetime(dates, errors='coerce')
        data["values"] = grouped_data['values'].tolist()

    def create_zero_data(self, year: str) -> dict:
        zero_dict = {
            "dates": [],
            "values": [],
        }

        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        dates = zero_dates.strftime('%Y-%m-%d').tolist()
        values = [0] * len(dates)

        zero_dict['dates'] = dates
        zero_dict['values'] = values

        return zero_dict

    def get_year(self) -> int:
        return datetime.now().year

    def get_csv_file(self, data: list):
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(data)
        csv_data.seek(0)
        return csv_data


class DrawGraphCategoriesThisYear(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> None:
        dates_all = []
        values = []

        for values in data.values():
            dates_all.extend(values["dates"])
            values.extend(values["values"])

        zero_data = self.create_zero_data(self.get_year())

        data = {
            "dates": dates_all,
            "values": values,
        }
        self.data_merge(data, zero_data)
        self.data_sorted(data)
        self.data_group(data, sum_group=True)

        url = self.create_graph(data)

        data = [model, categorie_id, url]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def create_graph(self, data_views):
        plt.figure(figsize=(10, 5))

        values = data_views["values"]
        dates = data_views["dates"]

        dates = pd.to_datetime(dates, errors='coerce')
        
        plt.plot(dates, values, marker='o', label="Текущий год")

        if values:
            rolling_mean = pd.Series(values).rolling(window=3).mean()
            plt.plot(dates, rolling_mean, linestyle='--', color='red', label='Средняя скользящая')
        
        plt.title("Всего проданного товара за текущий год")
        plt.ylabel("Проданный товар, кол.")
        plt.legend()

        russian_month_names = {
            'Jan': 'Янв',
            'Feb': 'Фев',
            'Mar': 'Мар',
            'Apr': 'Апр',
            'May': 'Май',
            'Jun': 'Июн',
            'Jul': 'Июл',
            'Aug': 'Авг',
            'Sep': 'Сен',
            'Oct': 'Окт',
            'Nov': 'Ноя',
            'Dec': 'Дек',
        }

        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.gca().xaxis.set_major_formatter(FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        max_ticks = 10
        step = (max(values) - min(values)) / (max_ticks - 1)
        if values:
            if step == 0: step = 100
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"


class DrawGraphCategoriesLastYear(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> None:
        dates_all = []
        values = []

        for values in data.values():
            dates_all.extend(values["dates"])
            values.extend(values["values"])

        zero_data = self.create_zero_data(self.get_year() - 1)

        data = {
            "dates": dates_all,
            "values": values,
        }
        self.data_merge(data, zero_data)
        self.data_sorted(data)
        self.data_group(data, sum_group=True)

        url = self.create_graph(data)

        data = [model, categorie_id, url]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def create_graph(self, data_views):
        plt.figure(figsize=(10, 5))

        values = data_views["values"]
        dates = data_views["dates"]

        dates = pd.to_datetime(dates, errors='coerce')
        
        plt.plot(dates, values, marker='o', label="Прошлый год")

        if values:
            rolling_mean = pd.Series(values).rolling(window=3).mean()
            plt.plot(dates, rolling_mean, linestyle='--', color='red', label='Средняя скользящая')

        plt.title("Всего проданного товара за прошлый год")
        plt.ylabel("Проданный товар, кол.")
        plt.legend()

        russian_month_names = {
            'Jan': 'Янв',
            'Feb': 'Фев',
            'Mar': 'Мар',
            'Apr': 'Апр',
            'May': 'Май',
            'Jun': 'Июн',
            'Jul': 'Июл',
            'Aug': 'Авг',
            'Sep': 'Сен',
            'Oct': 'Окт',
            'Nov': 'Ноя',
            'Dec': 'Дек',
        }

        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.gca().xaxis.set_major_formatter(FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        max_ticks = 10
        step = (max(values) - min(values)) / (max_ticks - 1)
        if values:
            if step == 0: step = 100
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"


class DrawGraphCategoriesInterest(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> None:
        dates_all = []
        hits_view_all = []
        hits_tocart_all = []

        for values in data.values():
            dates_all.extend(values["dates"])
            hits_view_all.extend(values["hits_view"])
            hits_tocart_all.extend(values["hits_tocart"])

        zero_data = self.create_zero_data(self.get_year())

        data_views = {
            "dates": dates_all,
            "values": hits_view_all,
        }
        self.data_merge(data_views, zero_data)
        self.data_sorted(data_views)
        self.data_group(data_views, sum_group=True)

        data_tocart = {
            "dates": dates_all,
            "values": hits_tocart_all,
        }

        self.data_merge(data_tocart, zero_data)
        self.data_sorted(data_tocart)
        self.data_group(data_tocart, sum_group=True)

        url = self.create_graph(data_views, data_tocart)

        data = [model, categorie_id, url]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def create_graph(self, data_views, data_tocart):
        fig, ax1 = plt.subplots(figsize=(10, 5))

        ax1.plot(data_views["dates"], data_views["values"], marker='o', label="График показа товаров")
        ax1.set_ylabel('Показы, кол.')
        ax1.tick_params('y')

        ax2 = ax1.twinx()
        ax2.plot(data_tocart["dates"], data_tocart["values"], marker='o', label="График добавления в корзину", color='orange')
        ax2.set_ylabel('Добавление в корзину, кол')
        ax2.tick_params('y')

        plt.title("Суммарный график интереса за текущий год")

        russian_month_names = {
            'Jan': 'Янв',
            'Feb': 'Фев',
            'Mar': 'Мар',
            'Apr': 'Апр',
            'May': 'Май',
            'Jun': 'Июн',
            'Jul': 'Июл',
            'Aug': 'Авг',
            'Sep': 'Сен',
            'Oct': 'Окт',
            'Nov': 'Ноя',
            'Dec': 'Дек',
        }
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph_.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        plt.close()

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"



