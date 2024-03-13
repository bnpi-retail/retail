import ast
import base64
import io
import csv
import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from os import getenv
from datetime import datetime
from matplotlib.ticker import FuncFormatter

logger = logging.getLogger(__name__)


class GroupData:
    @staticmethod
    def __create_dataframe(data: dict) -> pd.DataFrame:
        """
        Создает DataFrame из словаря данных.
        """
        df = pd.DataFrame({'dates': pd.to_datetime(data["dates"]), 'values': data["values"]})
        df.set_index('dates', inplace=True)
        return df

    @staticmethod
    def __group_data(df: pd.DataFrame, mean: bool = False, sum_group: bool = False) -> pd.DataFrame:
        """
        Группирует данные по неделям или дням, суммирует или находит среднее.
        """
        if mean:
            grouped_data = df.resample('W-Mon').mean()
        elif sum_group:
            grouped_data = df.resample('W-Mon').sum()
        else:
            grouped_data = df.resample('D').sum()
        return grouped_data

    @staticmethod
    def __format_dates(grouped_data: pd.DataFrame) -> pd.DatetimeIndex:
        """
        Форматирует даты для возвращения в виде pd.DatetimeIndex.
        """
        return pd.to_datetime(grouped_data.index.strftime('%Y-%m-%d'), errors='coerce')

    @staticmethod
    def __format_values(grouped_data: pd.DataFrame) -> list:
        """
        Форматирует значения для возвращения в виде списка.
        """
        return grouped_data['values'].tolist()

    def data_group(self, data: dict, mean: bool = False, sum_group: bool = False) -> dict:
        """
        Группирует данные по неделям или дням и находит сумму или среднее.
        """
        df = self.__create_dataframe(data)
        grouped_data = self.__group_data(df, mean, sum_group)

        dates = self.__format_dates(grouped_data)
        values = self.__format_values(grouped_data)

        return {"dates": dates, "values": values}


class Fill_Data:
    @staticmethod
    def create_zero_dates(start_date: str, end_date: str) -> list:
        """
        Создаем пустые значения для всего промежутка данных
        """
        dates = pd.date_range(start=start_date, end=end_date)
        dates = dates.strftime('%Y-%m-%d').tolist()
        return dates

    @staticmethod
    def data_merge(dates: list, values: list, zero_dates: list) -> tuple:
        zero_values = [0] * len(zero_dates)

        dates.extend(zero_dates)
        values.extend(zero_values)

        sorted_data = sorted(set(zip(dates, values)), key=lambda x: x[0])
        sorted_dates, sorted_values = zip(*sorted_data)

        data = {
            "dates": sorted_dates,
            "values": sorted_values,
        }
        return data


class OnePlots:
    def __init__(self) -> None:
        self.figsize = (10, 5)

    @staticmethod
    def process_average_data(data) -> dict:
        data_fixed = data \
            .replace("'", "\"") \
            .replace("\r", "") \
            .replace("\n", "")
        data_object = json.loads(data_fixed)
        return data_object

    def setup_subplots(self, plt_instance) -> tuple:
        fig, ax1 = plt_instance.subplots(figsize=self.figsize)
        return fig, ax1

    @staticmethod
    def add_graph(ax, dates: pd.DatetimeIndex, values, label, y_label=None, color=None, step=10) -> None:
        ax.plot(dates, values, marker='o', label=label, color=color)
        if y_label:
            ax.set_ylabel(f'{y_label}, кол.')

        y_min = min(values)
        y_max = max(values)
        range_size = y_max - y_min
        step = max(1, round(range_size / 10, -1))

        ax.yaxis.set_major_locator(ticker.MultipleLocator(base=step))
        ax.set_yticks(np.arange(y_min, y_max + 1, step=step))

    @staticmethod
    def format_month_ticks(plt_instance) -> None:
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

        plt_instance.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt_instance.gca().xaxis.set_major_formatter(FuncFormatter(
            lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')])
        )

    @staticmethod
    def save_to_buffer(plt_instance):
        buffer = io.BytesIO()
        plt_instance.savefig(buffer, format='png')
        buffer.seek(0)
        return buffer

    @staticmethod
    def get_csv_file(data: list):
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(data)
        csv_data.seek(0)
        return csv_data


class TwoPlots(OnePlots):
    def setup_subplots(self, plt_instance) -> tuple:
        fig, ax1 = super().setup_subplots(plt_instance)
        ax2 = ax1.twinx()
        return fig, ax1, ax2


class InterestGraph(GroupData, Fill_Data, TwoPlots):
    def __init__(self, data) -> None:
        super().__init__()
        self.model = data['model']
        self.product_id = data['product_id']
        self.hits_view = data['hits_view']
        self.hits_tocart = data['hits_tocart']
        self.average_data = data['average_data']

    def main(self) -> tuple:
        data_views, data_tocart, average_data = self.process_data()
        bytes_plot = self.draw(data_views, data_tocart, average_data)

        return bytes_plot, self.hits_view, self.hits_tocart

    def process_data(self) -> tuple:
        year = datetime.now().year
        zero_dates = self.create_zero_dates(start_date=f"{year}-01-01", end_date=f"{year}-12-31")

        def process_data_for_category(dates, values) -> dict:
            return self.data_group(
                self.data_merge(dates, values, zero_dates),
                sum_group=True
            )

        data_views = process_data_for_category(
            self.hits_view["dates"], self.hits_view["num"]
        )
        data_tocart = process_data_for_category(
            self.hits_tocart["dates"], self.hits_tocart["num"]
        )
        average_data = None
        if self.average_data is not None:
            average_data = self.process_average_data(self.average_data)

        return data_views, data_tocart, average_data

    def draw(self, data_views, data_tocart, average_data):
        fig, ax1, ax2 = self.setup_subplots(plt)

        self.add_graph(
            ax1, data_views["dates"], data_views["values"],
            y_label="Показы товаров",
            label="График показа товаров", step=10
        )
        self.add_graph(
            ax2, data_tocart["dates"], data_tocart["values"],
            y_label="Добавления в корзину",
            label="График добавления в корзину", color='orange', step=10
        )

        if average_data is not None:
            dates = np.array(average_data["hits_tocart"]["dates"], dtype='datetime64')
            self.add_graph(
                ax2, dates, average_data["hits_tocart"]["values"],
                label="График добавления в корзину средний по категории",
                color='green', step=10
            )
            self.add_graph(
                ax1, dates, average_data["hits_view"]["values"],
                label="График показа товаров средний по категории",
                color='red', step=10
            )

        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        self.format_month_ticks(plt)

        plt.suptitle("График интереса")
        plt.tight_layout()

        buffer = self.save_to_buffer(plt)

        plt.close()

        return buffer.read()


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


class DrawGraphSale(DataFunction):
    def __init__(self, dict: dict) -> None:
        self.year = dict["year"]
        self.data = dict["data"]
        if dict["data_average"] is not None:
            self.data_average = ast.literal_eval(dict["data_average"])
        else:
            self.data_average = None
        self.title = "Всего проданного товара"
        self.ylabel = "Проданный товар, кол."
        self.label_moving_average = "Средняя скользящая"
        self.label_category_average = "Средняя по категории"

    def __call__(self) -> bytes:
        bytes_plot = self.main()
        return bytes_plot

    def main(self) -> bytes:
        dates, values = self.data_process(self.data)

        average_dates, average_values = None, None

        if self.data_average is not None:
            average_dates, average_values = self.data_process_average(self.data_average)

        bytes_plot = self.create_graph(dates, values, average_dates, average_values)

        return bytes_plot

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

        if "dates" not in self.data_average \
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
        plt.gca().xaxis.set_major_formatter(
            FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        plt.yticks(range(0, 100 + 10, 10))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        return base64.b64encode(buffer.read())


class DrawGraphCategoriesThisYear(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> tuple:
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

        bytes_plot = self.create_graph(data)

        data['dates'] = data['dates'].strftime('%Y-%m-%d').tolist()

        return bytes_plot, data

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
        plt.gca().xaxis.set_major_formatter(
            FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        max_ticks = 10
        step = round((max(values) - min(values)) / (max_ticks - 1))
        if values:
            if step == 0: step = 10
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        plt.close()

        return base64.b64encode(buffer.read())


class DrawGraphCategoriesLastYear(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> tuple:
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

        bytes_plot = self.create_graph(data)

        data['dates'] = data['dates'].strftime('%Y-%m-%d').tolist()

        return bytes_plot, data

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
        plt.gca().xaxis.set_major_formatter(
            FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        max_ticks = 10
        step = round((max(values) - min(values)) / (max_ticks - 1))
        if values:
            if step == 0: step = 10
            plt.yticks(np.arange(min(values), max(values) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        plt.close()

        return base64.b64encode(buffer.read())


class DrawGraphCategoriesInterest(DataFunction):
    def draw_graph(self, data: dict, model, categorie_id) -> tuple:
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

        bytes_plot = self.create_graph(data_views, data_tocart)

        data_views['dates'] = data_views['dates'].strftime('%Y-%m-%d').tolist()
        data_tocart['dates'] = data_tocart['dates'].strftime('%Y-%m-%d').tolist()

        return bytes_plot, data_views, data_tocart

    def create_graph(self, data_views, data_tocart):
        fig, ax1 = plt.subplots(figsize=(10, 5))

        ax1.plot(data_views["dates"], data_views["values"], marker='o', label="График показа товаров")
        ax1.set_ylabel('Показы, кол.')
        ax1.tick_params('y')
        ax1.set_yticks(range(0, max(data_views["values"]) + 1, 10))

        ax2 = ax1.twinx()
        ax2.plot(data_tocart["dates"], data_tocart["values"], marker='o', label="График добавления в корзину",
                 color='orange')
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
        ax1.xaxis.set_major_formatter(
            FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        plt.close()

        return base64.b64encode(buffer.read())
