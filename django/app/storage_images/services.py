import io
import csv
import ast
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from os import getenv
from typing import Any
from datetime import datetime
from multiprocessing import Value, process
from matplotlib.ticker import FuncFormatter
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class DataFunction:
    def data_sorted(self, data: dict) -> None:
        sorted_data = sorted(set(zip(data["dates"], data["values"])), key=lambda x: x[0])
        sorted_dates, sorted_values = zip(*sorted_data)
        data["dates"] = sorted_dates
        data["values"] = sorted_values
        return data
    
    def data_merge(self, data: dict, zero_data: dict) -> None:
        data["dates"].extend(zero_data["dates"])
        data["values"].extend(zero_data["values"])
        return data
    
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
        return data
    
    def create_zero_data(self, year: str) -> dict:
        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        dates = zero_dates.strftime('%Y-%m-%d').tolist()
        items = [0] * len(dates)

        zero_dict = {
            "dates": dates,
            "values": items,
        }

        return zero_dict

    def get_year(self) -> int:
        return datetime.now().year

    def get_csv_file(self, data: list):
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(data)
        csv_data.seek(0)
        return csv_data


class AnalysisData(DataFunction):
    def __init__(self, dict: dict) -> None:
        self.data = dict["data"]
        if dict["data_average"] is not None:
            self.data_average = json.loads(dict["data_average"].replace("'", "\""))
        else:
            self.data_average = None
        self.title = "График интереса"
        self.ylabel = "Проданный товар, кол."
        self.label_moving_average = "Средняя скользящая"
        self.label_category_average = "Средняя по категории"

    def generate_url_analysis_data(self, product_id, dates_hits_view, num_hits_view, dates_hits_tocart, num_hits_tocart):
        fig, ax1 = plt.subplots(figsize=(10, 5))

        dates_hits_view = pd.to_datetime(dates_hits_view, errors='coerce')
        dates_hits_tocart = pd.to_datetime(dates_hits_tocart, errors='coerce')
        
        ax1.plot(dates_hits_view, num_hits_view, marker='o', label="График показа товаров")
        ax1.set_ylabel('Показы, кол.')
        ax1.tick_params('y')
        
        ax2 = ax1.twinx()
        ax2.plot(dates_hits_tocart, num_hits_tocart, marker='o', label="График добавления в корзину", color='orange')
        ax2.set_ylabel('Добавление в корзину, кол')
        ax2.tick_params('y')

        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        plt.title("График интереса")
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

        if num_hits_view:
            plt.yticks(np.arange(min(min(num_hits_view), min(num_hits_tocart)), max(max(num_hits_view), max(num_hits_tocart)) + 1000, step=1000))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph_{product_id}.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        plt.close()

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"



class DrawGraphSale(DataFunction):
    def __init__(self, dict: dict) -> None:
        self.year = dict["year"]
        self.data = dict["data"]
        if dict["data_average"] is not None:
            self.data_average = json.loads(dict["data_average"].replace("'", "\""))
        else:
            self.data_average = None
        self.title = "Всего проданного товара"
        self.ylabel = "Проданный товар, кол."
        self.label_moving_average = "Средняя скользящая"
        self.label_category_average = "Средняя по категории"

    def __call__(self) -> str:
        url = self.main() 
        return url
    
    def main(self) -> str:
        dates, values = self.data_process(self.data)

        average_dates, average_values = None, None

        if self.data_average is not None:
            average_dates, average_values = self.data_process_average(self.data_average)

        url = self.create_graph(dates, values, average_dates, average_values)

        return url

    def data_process_average(self, data: dict) -> tuple:
        return np.array(data["dates"], dtype='datetime64'), data["values"]
    
    def data_process(self, data: dict) -> tuple:
        zero_data = self.create_zero_data(self.year)

        data = self.data_merge(data, zero_data)
        data = self.data_sorted(data)
        data = self.data_group(data, mean=True)

        return data["dates"], data["values"]
    
    def data_unite(self) -> dict:
        data = {
            "dates": [],
            "values": []
        }

        if  "dates" not in self.data_average \
        or "values" not in self.data_average: 
            return data

        for item in self.data_average.values():
            data["dates"].extend(item["dates"])
            data["values"].extend(item["values"])

        return data

    def create_graph(self, dates: list, values: list, average_dates=None, average_values=None):
        plt.figure(figsize=(10, 5))

        dates = pd.to_datetime(dates, errors='coerce')
        
        plt.plot(dates, values, marker='o', label="График продаж")

        if values:
            rolling_mean = pd.Series(values).rolling(window=3).mean()
            plt.plot(dates, rolling_mean, linestyle='--', color='red', label=self.label_moving_average)
        
        if average_dates is not None and average_values is not None:
            plt.plot(average_dates, average_values, color='green', label=self.label_category_average)
        
        plt.title(self.title)
        plt.ylabel(self.ylabel)
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

        # max_ticks = 10
        # if values or average_values:
            # min_value = min(values) if values else min(average_values)
            # max_value = max(values) if values else max(average_values)

            # step = (max_value - min_value) / (max_ticks - 1) if (max_ticks - 1) != 0 else 1

        # plt.yticks(np.arange(0, 1000, step=100), bottom=0)
        max_ticks = 10
        step = round((max(values) - min(values)) / (max_ticks - 1))
        if values:
            if step == 0: step = 10
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)
        
        plt.close()

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"
    

class DrawGraphCategoriesThisYear(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> None:
        dates_all = []
        values = []

        for dict_values in data.values():
            dates_all.extend(dict_values["dates"])
            values.extend(dict_values["values"])

        zero_data = self.create_zero_data(self.get_year())

        data = {
            "dates": dates_all,
            "values": values,
        }
        self.data_merge(data, zero_data)
        self.data_sorted(data)
        self.data_group(data, sum_group=True)

        url = self.create_graph(data)

        data['dates'] = data['dates'].strftime('%Y-%m-%d').tolist()
        csv_content = [model, categorie_id, url, str(data).replace(',', '|')]
        csv_file = self.get_csv_file(csv_content)
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
        step = round((max(values) - min(values)) / (max_ticks - 1))
        if values:
            if step == 0: step = 10
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        plt.close()

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"


class DrawGraphCategoriesLastYear(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> None:
        dates_all = []
        values = []

        for dict_values in data.values():
            dates_all.extend(dict_values["dates"])
            values.extend(dict_values["values"])

        zero_data = self.create_zero_data(self.get_year() - 1)

        data = {
            "dates": dates_all,
            "values": values,
        }

        self.data_merge(data, zero_data)
        self.data_sorted(data)
        self.data_group(data, mean=True)

        url = self.create_graph(data)

        data['dates'] = data['dates'].strftime('%Y-%m-%d').tolist()
        data = [model, categorie_id, url, str(data).replace(',', '|')]
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
        step = round((max(values) - min(values)) / (max_ticks - 1))
        if values:
            if step == 0: step = 10
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        plt.close()

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
        
        data = [model, categorie_id, url, str(data_views).replace(',', '|'), str(data_tocart).replace(',', '|')]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def create_graph(self, data_views, data_tocart):
        fig, ax1 = plt.subplots(figsize=(10, 5))

        ax1.plot(data_views["dates"], data_views["values"], marker='o', label="График показа товаров")
        ax1.set_ylabel('Показы, кол.')
        ax1.tick_params('y')
        ax1.set_yticks(range(0, max(data_views["values"]) + 1, 10))

        ax2 = ax1.twinx()
        ax2.plot(data_tocart["dates"], data_tocart["values"], marker='o', label="График добавления в корзину", color='orange')
        ax2.set_ylabel('Добавление в корзину, кол')
        ax2.tick_params('y')
        ax2.set_yticks(range(0, max(data_tocart["values"]) + 1, 10))

        plt.title("График интереса за текущий год")

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



