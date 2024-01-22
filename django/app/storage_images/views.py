import io
import csv
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from datetime import datetime
from matplotlib.ticker import FuncFormatter
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from account.services import connect_to_odoo_api_with_auth


class DrawGraph(APIView):
    permission_classes = (IsAuthenticated,)

    def generate_plot_image(self, product_id, dates, num, is_current=True):
        plt.figure(figsize=(10, 5))

        dates = pd.to_datetime(dates, errors='coerce')
        
        plt.plot(dates, num, marker='o', label='Текущий год' if is_current else 'Предыдущий год')

        if num:
            rolling_mean = pd.Series(num).rolling(window=3).mean()
            plt.plot(dates, rolling_mean, linestyle='--', color='red', label='Средняя скользящая')

        plt.title('График продаж')
        plt.xlabel('Дата')
        plt.ylabel('Проданных товаров, кол.')
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

        plt.xticks(rotation=45)

        if num:
            plt.yticks(np.arange(min(num), max(num) + 1, step=10))

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        filename = f'current_graph_{product_id}.png' if is_current else f'last_graph_{product_id}.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))
        file_url = default_storage.url(file_path)

        return f"https://retail-extension.bnpi.dev{file_url}"

    def group_by_week(self, data, year):
        dates = data.get('dates', [])
        num = data.get('num', [])

        zero_dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        all_dates = zero_dates.strftime('%Y-%m-%d').tolist()
        all_nums = [0] * len(all_dates)
        
        dates.extend(all_dates)
        num.extend(all_nums)

        if dates and num:
            sorted_data = sorted(set(zip(dates, num)), key=lambda x: x[0])
            sorted_dates, sorted_num = zip(*sorted_data)
        else:
            sorted_dates, sorted_num = [], []

        df = pd.DataFrame({'date': pd.to_datetime(sorted_dates), 'num': sorted_num})
        df.set_index('date', inplace=True)
        # full_date_range = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
        # df = df.reindex(full_date_range, fill_value=0)
        weekly_data = df.resample('W-Mon').sum()
        grouped_dates = weekly_data.index.strftime('%Y-%m-%d').tolist()
        grouped_num = weekly_data['num'].tolist()

        return grouped_dates, grouped_num

    def draw_graph_products(self, request):
        product_id = request.data.get('product_id', None)
        current_data = request.data.get('current', None)
        last_data = request.data.get('last', None)

        dates, num = self.group_by_week(current_data, datetime.now().year)
        current_url = self.generate_plot_image(product_id, dates, num, is_current=True)
        dates, num = self.group_by_week(last_data, datetime.now().year - 1)
        last_url = self.generate_plot_image(product_id, dates, num, is_current=False)

        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(['id', 'url_last_year', 'url_this_year'])
        csv_writer.writerow([product_id, current_url, last_url])
        csv_data.seek(0)

        endpoint = "http://odoo-web:8069/import/images/products"
        files = {'file': ('output.csv', csv_data)}
        return endpoint, files

    def draw_graph_competitors_products(self, request):
        product_id = request.data.get('product_id', None)
        current_data = request.data.get('current', None)

        dates, num = self.group_by_week(current_data, datetime.now().year)
        current_url = self.generate_plot_image(product_id, dates, num, is_current=True)

        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(['id', 'url_last_year'])
        csv_writer.writerow([product_id, current_url])
        csv_data.seek(0)

        endpoint = "http://odoo-web:8069/import/images/competitors_products"
        files = {'file': ('output.csv', csv_data)}
        return endpoint, files

    def post(self, request):
        model = request.data.get('model', None)

        if model == "products":
            endpoint, files = self.draw_graph_products(request)
            
        elif model == "competitors_products":
            endpoint, files = self.draw_graph_competitors_products(request)

        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})
        headers = {"Cookie": f"session_id={session_id}"}
        response = requests.post(endpoint, headers=headers, files=files)
    
        if response.status_code != 200:
            return Response({'message': response.text}, status=400)
        return Response({'message': f"Success!"})
