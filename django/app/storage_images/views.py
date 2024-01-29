import io
import csv
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from os import getenv
from datetime import datetime, timedelta
from matplotlib.ticker import FuncFormatter
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from account.services import connect_to_odoo_api_with_auth
from .services import DrawGraphCategoriesInterest , DrawGraphCategoriesThisYear , DrawGraphCategoriesLastYear, DrawGraphSale


class DrawGraph(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        payload_file, payload = False, False
        model = request.data.get('model', None)
        
        if model == "sale":
            payload_file, payload = self.draw_graph_sale(request, model)

        elif model == "sale_by_week":
            payload_file, payload = self.draw_graph_sale_by_week(request, model)

        elif model == "competitors_products":
            payload_file, payload = self.draw_graph_competitors_products(request, model)

        elif model == "price_history":
            payload_file, payload = self.draw_graph_price_history(request, model)

        elif model == "stock":
            payload_file, payload = self.draw_graph_stock(request, model)

        elif model == "analysis_data":
            payload_file, payload = self.draw_graph_analysis_data(request, model)

        elif model == "categorie_analysis_data":
            graph = DrawGraphCategoriesInterest()
            data = request.data.get('data', None)
            categorie_id = request.data.get('categorie_id', None)

            if data is not None:
                payload_file, payload = graph.draw_graph(data, model, categorie_id)

        elif model == "categorie_sale_this_year":
            graph = DrawGraphCategoriesThisYear()
            data = request.data.get('data', None)
            categorie_id = request.data.get('categorie_id', None)

            if data is not None:
                payload_file, payload = graph.draw_graph(data, model, categorie_id)

        elif model == "categorie_sale_last_year":
            graph = DrawGraphCategoriesLastYear()
            data = request.data.get('data', None)
            categorie_id = request.data.get('categorie_id', None)
            
            if data is not None:
                payload_file, payload = graph.draw_graph(data, model, categorie_id)

        if payload_file is False: return Response({'status': 'payload file is empty'})

        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})
        headers = {"Cookie": f"session_id={session_id}"}

        endpoint = "http://odoo-web:8069/import/images"
        response = requests.post(endpoint, headers=headers, files=payload_file, data=payload)
    
        if response.status_code != 200:
            return Response({'message': response.text}, status=400)
        return Response({'message': f"Success!"})

    def draw_graph_sale(self, request, model):
        product_id = request.data.get('product_id', None)
        
        dict = {
            "data": request.data.get('current', None),
            "data_average":request.data.get('average_graph_this_year', None),
            "year": datetime.now().year,
        }

        graph = DrawGraphSale(dict)
        current_url = graph()

        dict = {
            "data": request.data.get('last', None),
            "data_average":request.data.get('average_graph_last_year', None),
            "year": datetime.now().year - 1,
        }

        graph = DrawGraphSale(dict)
        last_url = graph()
        
        data = [product_id, current_url, last_url]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}

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

        data = [product_id, two_week_url, six_week_url, twelve_week_url]
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

        data = [product_id, url]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}
    
    def draw_graph_price_history(self, request, model):
        product_id = request.data.get('product_id', None)
        data_current = request.data.get('current', None)

        year = datetime.now().year
        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        grouped_dates, grouped_num = self.data_group(data_current, zero_dates, mean=True)
        url = self.generate_url_image(
            label='График истории цен',
            product_id=product_id,
            dates=grouped_dates,
            num=grouped_num,
            step=100,
            name_images='График истории цен за текущий год',
            ylabel='Средняя цена за неделю, руб.',
        )

        data = [product_id, url]
        csv_file = self.get_csv_file(data)
        return {'file': ('output.csv', csv_file)}, {'model': model}
    
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

        data = [product_id, url]
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

        data = [product_id, url]
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
    
    def generate_url_image(self, label, product_id, dates, num, step, name_images, ylabel, month_xaxis=True, day_xaxis=False, average_graph=None):
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
            plt.gca().xaxis.set_major_formatter(FuncFormatter(lambda x, _: russian_month_names[mdates.num2date(x).strftime('%b')]))

        if day_xaxis == True:
            plt.gca().xaxis.set_major_locator(mdates.DayLocator())
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
            plt.xticks([dates[0], dates[-1]])

        # plt.xticks(rotation=45)

        max_ticks = 10
        # step = (max(num) - min(num)) / (max_ticks - 1)
        if num:
            if step == 0: step = 100
            plt.yticks(np.arange(min(num), max(num) + step, step=step))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'graph_{product_id}.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        plt.close()

        return f"{getenv('DJANGO_DOMAIN')}{file_url}"

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


    


