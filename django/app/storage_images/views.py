import io
import matplotlib.pyplot as plt

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class DrawGraph(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
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

        filename = 'graph.png'
        file_path = default_storage.save(filename, ContentFile(buffer.read()))

        file_url = default_storage.url(file_path)

        data = {'current_data': current_data, 'last_data': last_data, 'graph_url': file_url}
        return Response(data, status=200)
