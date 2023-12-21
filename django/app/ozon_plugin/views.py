import os
import requests

from django.http import FileResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.views import View

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .forms import FileUploadForm
from account.services import connect_to_odoo_api_with_auth


APP_NAME = __package__ + '/'


class CheckAuth(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({'message': 'Authentication successful'}, status=200)

class OzonPlugin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})
        
        csv_data = ""
        csv_data += ','.join(['number',
                              'search',
                              'seller',
                              'sku',
                              'price',
                              'price_without_sale',
                              'price_with_card',
                              'href',
                              'name'
                              ]) + '\n'
        for item in request.data:
            elements = item.get('elements')
            csv_list = []
            for element in elements:
                row = [
                    str(element.get('number', '')),
                    str(element.get('search', '')),
                    str(element.get('seller', '')),
                    str(element.get('sku', '')),
                    str(element.get('price', '')),
                    str(element.get('price_without_sale', '')),
                    str(element.get('price_with_card', '')),
                    str(element.get('href', '')),
                    str(element.get('name', '')),
                ]
                csv_list.append(','.join(row))
            csv_data += '\n'.join(csv_list) + '\n'

        endpoint = "http://odoo-web:8069/take_ozon_data"
        headers = {"Cookie": f"session_id={session_id}"}
        files = {'file': ('output.csv', csv_data)}

        data = {'email': request.user.email}
        response = requests.post(endpoint, headers=headers, files=files, data=data)
        
        return Response({'message': str(response.status_code)})


class DownloadExtension(APIView):
    def get(self, request, *args, **kwargs):
        extension_path = "./extension.7z"

        response = FileResponse(open(extension_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="OzonExtension.zip"'
        return response


class FileUploadView(View):
    template_name = 'upload_file.html'

    def get(self, request, *args, **kwargs):
        form = FileUploadForm()
        return render(request, APP_NAME + self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            self.handle_uploaded_file(request.FILES['file'])
            return redirect('success')
        return render(request, APP_NAME + self.template_name, {'form': form})

    def handle_uploaded_file(self, file):
        with open(os.path.join(settings.MEDIA_ROOT, 'uploads', file.name), 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
