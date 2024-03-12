import base64
import io
import csv
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from os import getenv
from datetime import datetime, timedelta
from matplotlib.ticker import FuncFormatter
from .drawing_graphs_services import (
    DrawGraphSale,
    InterestGraph,
    DrawGraphCategoriesInterest,
    DrawGraphCategoriesThisYear,
    DrawGraphCategoriesLastYear,
)

logger = logging.getLogger(__name__)


class DrawGraph:
    def post(self, payload: dict):
        payload_file = False
        model = payload.get('model', None)

        if model == "sale":
            res = self.draw_graph_sale(payload, model)
            return res
        #
        # elif model == "sale_by_week":
        #     payload_file, payload = self.draw_graph_sale_by_week(request, model)
        #
        # elif model == "competitors_products":
        #     payload_file, payload = self.draw_graph_competitors_products(request, model)
        #
        elif model == "price_history":
            bytes_plot, data_current = self.draw_graph_price_history(payload, model)
            return bytes_plot, data_current

        # elif model == "stock":
        #     payload_file, payload = self.draw_graph_stock(request, model)
        #
        # elif model == "analysis_data":
        #     data = {
        #         "model": model,
        #         "product_id": request.data.get('product_id', None),
        #         "hits_view": request.data.get('hits_view', None),
        #         "hits_tocart": request.data.get('hits_tocart', None),
        #         "average_data": request.data.get('average_data', None),
        #     }
        #     graph = InterestGraph(data)
        #     payload_file, payload = graph.main()
        #
        # elif model == "categorie_analysis_data":
        #     graph = DrawGraphCategoriesInterest()
        #     data = request.data.get('data', None)
        #     categorie_id = request.data.get('categorie_id', None)
        #
        #     if data is not None:
        #         payload_file, payload = graph.draw_graph(data, model, categorie_id)
        #
        # elif model == "categorie_sale_this_year":
        #     graph = DrawGraphCategoriesThisYear()
        #     data = request.data.get('data', None)
        #     categorie_id = request.data.get('categorie_id', None)
        #
        #     if data is not None:
        #         payload_file, payload = graph.draw_graph(data, model, categorie_id)
        #
        # elif model == "categorie_sale_last_year":
        #     graph = DrawGraphCategoriesLastYear()
        #     data = request.data.get('data', None)
        #     categorie_id = request.data.get('categorie_id', None)
        #
        #     if data is not None:
        #         payload_file, payload = graph.draw_graph(data, model, categorie_id)
        #
        if payload_file is False:
            return {'status': 'payload file is empty'}

        endpoint = "http://odoo-web:8069/import/images"
        # response = requests.post(endpoint, headers=headers, files=payload_file, data=payload)

    def draw_graph_sale(self, payload: dict, model):
        product_id = payload.get('product_id', None)

        data_graph_current = payload.get('current', None)

        dict = {
            "data": data_graph_current,
            "data_average": payload.get('average_graph_this_year', None),
            "year": datetime.now().year,
        }

        graph = DrawGraphSale(dict)
        current_bytes_plot = graph()

        data_graph_last = payload.get('last', None)

        dict = {
            "data": data_graph_last,
            "data_average": payload.get('average_graph_last_year', None),
            "year": datetime.now().year - 1,
        }

        graph = DrawGraphSale(dict)
        last_bytes_plot = graph()

        data_graph_current['dates'] = data_graph_current['dates'].strftime('%Y-%m-%d').tolist()
        data_graph_last['dates'] = data_graph_last['dates'].strftime('%Y-%m-%d').tolist()

        return current_bytes_plot, last_bytes_plot, data_graph_current, data_graph_last

    def draw_graph_sale_by_week(self, request, model):
        product_id = request.data.get('product_id', None)
        data_two_weeks = request.data.get('two_weeks', None)
        data_six_week = request.data.get('six_week', None)
        data_twelve_week = request.data.get('twelve_week', None)

        current_date = datetime.now()
        date_two_weeks_ago = current_date - timedelta(weeks=2)
        date_six_weeks_ago = current_date - timedelta(weeks=6)
        date_twelve_weeks_ago = current_date - timedelta(weeks=12)

        zero_dates_two_weeks_ago = pd.date_range(start=date_two_weeks_ago, end=current_date)
        zero_dates_six_weeks_ago = pd.date_range(start=date_six_weeks_ago, end=current_date)
        zero_dates_twelve_weeks_ago = pd.date_range(start=date_twelve_weeks_ago, end=current_date)

        grouped_dates, grouped_num = self.data_group(data_two_weeks, zero_dates_two_weeks_ago, sum_group=False)
        two_week_url = self.generate_url_image(
            label='График остатков',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=50,
            name_images='График продаж за 2 недели',
            ylabel='Проданный товар, кол.',
            month_xaxis=False,
            day_xaxis=True,
        )

        grouped_dates, grouped_num = self.data_group(data_six_week, zero_dates_six_weeks_ago, sum_group=False)
        six_week_url = self.generate_url_image(
            label='График остатков',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=50,
            name_images='График продаж за 6 недель',
            ylabel='Проданный товар, кол.',
            month_xaxis=False,
            day_xaxis=True,
        )

        grouped_dates, grouped_num = self.data_group(data_twelve_week, zero_dates_twelve_weeks_ago, sum_group=False)
        twelve_week_url = self.generate_url_image(
            label='График остатков',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=50,
            name_images='График продаж за 12 недель',
            ylabel='Проданный товар, кол.',
            month_xaxis=False,
            day_xaxis=True,
        )

        data = [product_id, two_week_url, six_week_url, twelve_week_url, str(data_two_weeks).replace(',', '|'),
                str(data_six_week).replace(',', '|'), str(data_twelve_week).replace(',', '|')]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def draw_graph_competitors_products(self, request, model):
        product_id = request.data.get('product_id', None)
        data_current = request.data.get('current', None)

        year = datetime.now().year
        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        grouped_dates, grouped_num = self.data_group(data_current, zero_dates, mean=True)
        url = self.generate_url_image(
            label='Текущий год',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=100,
            name_images='График истории цен конкурента за текущий год',
            ylabel='Средняя цена за неделю, руб.',
        )

        data = [product_id, url, str(data_current).replace(',', '|')]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def draw_graph_price_history(self, payload: dict, model):
        product_id = payload.get('product_id', None)
        data_current = payload.get('current', None)

        year = datetime.now().year
        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        grouped_dates, grouped_num = self.data_group(data_current, zero_dates, mean=True)
        bytes_plot = self.generate_url_image(
            label='График истории цен',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=100,
            name_images='График истории цен за текущий год',
            ylabel='Средняя цена за неделю, руб.',
        )
        return bytes_plot, data_current

    def draw_graph_stock(self, request, model):
        product_id = request.data.get('product_id', None)
        data_current = request.data.get('current', None)

        year = datetime.now().year
        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        grouped_dates, grouped_num = self.data_group(data_current, zero_dates, sum_group=True)
        url = self.generate_url_image(
            label='График остатков',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=50,
            name_images='График остатков за текущий год',
            ylabel='Остатки товара, кол.',
        )

        data = [product_id, url, str(data_current).replace(',', '|')]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def draw_graph_analysis_data(self, request, model):
        product_id = request.data.get('product_id', None)
        hits_view = request.data.get('hits_view', None)
        hits_tocart = request.data.get('hits_tocart', None)
        average_hits_view = request.data.get('average_hits_view', None)
        average_to_cart = request.data.get('average_to_cart', None)

        year = datetime.now().year
        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')

        grouped_dates_hits_view, grouped_num_hits_view = self.data_group(hits_view, zero_dates, sum_group=True)
        grouped_dates_hits_tocart, grouped_num_hits_tocart = self.data_group(hits_tocart, zero_dates, sum_group=True)

        url = self.generate_url_analysis_data(
            product_id=product_id,

            dates_hits_view=grouped_dates_hits_view,
            num_hits_view=grouped_num_hits_view,

            dates_hits_tocart=grouped_dates_hits_tocart,
            num_hits_tocart=grouped_num_hits_tocart,
        )

        data = [product_id, url, str(hits_view).replace(',', '|'), str(hits_tocart).replace(',', '|')]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

    def get_csv_file(self, data: list):
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(data)
        csv_data.seek(0)
        return csv_data

    def data_group(self, data_graph, zero_dates, mean=False, sum_group=False):
        if data_graph:
            dates = data_graph.get('dates', None)
            num = data_graph.get('num', None)
        else:
            dates = []
            num = []

        all_dates = zero_dates.strftime('%Y-%m-%d').tolist()
        all_nums = [0] * len(all_dates)

        dates.extend(all_dates)
        num.extend(all_nums)

        sorted_data = sorted(set(zip(dates, num)), key=lambda x: x[0])
        sorted_dates, sorted_num = zip(*sorted_data)

        df = pd.DataFrame({'date': pd.to_datetime(sorted_dates), 'num': sorted_num})
        df.set_index('date', inplace=True)

        if mean == True:
            grouped_data = df.resample('W-Mon').mean()
        elif sum_group == True:
            grouped_data = df.resample('W-Mon').sum()
        else:
            grouped_data = df.resample('D').sum()

        grouped_dates = grouped_data.index.strftime('%Y-%m-%d').tolist()
        grouped_num = grouped_data['num'].tolist()

        return grouped_dates, grouped_num

    def generate_url_image(self, label, product_id, dates, num, step, name_images, ylabel, month_xaxis=True,
                           day_xaxis=False, average_graph=None):
        plt.figure(figsize=(10, 5))

        dates = pd.to_datetime(dates, errors='coerce')

        plt.plot(dates, num, marker='o', label=label)

        if num:
            rolling_mean = pd.Series(num).rolling(window=3).mean()
            plt.plot(dates, rolling_mean, linestyle='--', color='red', label='Средняя скользящая')

        if average_graph is not None:
            pass

        plt.title(name_images)
        plt.ylabel(ylabel)
        plt.legend()

        if month_xaxis == True:
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

        if day_xaxis == True:
            plt.gca().xaxis.set_major_locator(mdates.DayLocator())
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
            plt.xticks([dates[0], dates[-1]])

        # plt.xticks(rotation=45)

        max_ticks = 10
        step = round((max(num) - min(num)) / (max_ticks - 1))
        if num:
            if step == 0: step = 10
            plt.yticks(np.arange(min(num), max(num) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        # filename = f'graph_{product_id}.png'
        # file_path = default_storage.save(filename, ContentFile(buffer.read()))
        # file_url = default_storage.url(file_path)

        plt.close()

        return base64.b64encode(buffer.read())

        # return f"{getenv('DJANGO_DOMAIN')}{file_url}"

    def generate_url_analysis_data(self, product_id, dates_hits_view, num_hits_view, dates_hits_tocart,
                                   num_hits_tocart):
        fig, ax1 = plt.subplots(figsize=(10, 5))

        dates_hits_view = pd.to_datetime(dates_hits_view, errors='coerce')
        ax1.plot(dates_hits_view, num_hits_view, marker='o', label="График показа товаров")
        ax1.set_ylabel('Показы, кол.')
        ax1.tick_params('y')
        ax1.legend(loc='upper left')

        dates_hits_tocart = pd.to_datetime(dates_hits_tocart, errors='coerce')
        ax2 = ax1.twinx()
        ax2.plot(dates_hits_tocart, num_hits_tocart, marker='o', label="График добавления в корзину", color='orange')
        ax2.set_ylabel('Добавление в корзину, кол')
        ax2.tick_params('y')
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
        plt.gca().xaxis.set_major_formatter(
            FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        if num_hits_view:
            plt.yticks(np.arange(min(min(num_hits_view), min(num_hits_tocart)),
                                 max(max(num_hits_view), max(num_hits_tocart)) + 1000, step=1000))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        # filename = f'graph_{product_id}.png'
        # file_path = default_storage.save(filename, ContentFile(buffer.read()))
        # file_url = default_storage.url(file_path)

        plt.close()

        # return f"{getenv('DJANGO_DOMAIN')}{file_url}"
