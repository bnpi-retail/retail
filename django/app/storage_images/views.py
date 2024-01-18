import io
import csv
import requests
import matplotlib.pyplot as plt

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.services import connect_to_odoo_api_with_auth


class DrawGraph(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        product_id = request.data.get('product_id', None)
        current_data = request.data.get('current', {})
        last_data = request.data.get('last', {})

        current_dates = current_data.get('dates', [])
        current_num = current_data.get('num', [])

        last_dates = last_data.get('dates', [])
        last_num = last_data.get('num', [])

        plt.figure(figsize=(10, 5))

        plt.plot(current_dates, current_num, marker='o', label='Текущий год')
        plt.plot(last_dates, last_num, marker='o', label='Предыдущий год')

        plt.title('График продаж')
        plt.xlabel('Дата')
        plt.ylabel('Проданных товаров, кол.')
        plt.legend()
        plt.xticks(rotation=45)

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        current_filename = 'current_graph.png'
        current_file_path = default_storage.save(current_filename, ContentFile(buffer.read()))
        current_file_url = default_storage.url(current_file_path)

        buffer.seek(0)
        buffer.truncate()

        plt.clf()
        plt.plot(last_dates, last_num, marker='o', label='Предыдущий год')

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        last_filename = 'last_graph.png'
        last_file_path = default_storage.save(last_filename, ContentFile(buffer.read()))
        last_file_url = default_storage.url(last_file_path)

        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})

        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(['id', 'url_last_year', 'url_this_year'])
        csv_writer.writerow([
            product_id, 
            f"https://retail-extension.bnpi.dev{last_file_url}",
            f"https://retail-extension.bnpi.dev{current_file_url}"
        ])
        csv_data.seek(0)

        endpoint = "http://odoo-web:8069/take_ozon_data"
        headers = {"Cookie": f"session_id={session_id}"}
        files = {'file': ('output.csv', csv_data)}

        response = requests.post(endpoint, headers=headers, files=files)

        if response.status_code != 200:
            return Response({'message': 'Bad Request'}, status=400)
        return Response({'message': f"{response.status_code}--{product_id}--{last_file_url}--{current_file_url}"})