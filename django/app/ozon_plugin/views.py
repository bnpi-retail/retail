import requests
import tempfile

from django.http import FileResponse
from django.shortcuts import render, redirect
from django.views import View
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .forms import FileUploadForm, ApiToken
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

        token = request.auth
        api_key = token.key
        key = f'all--{api_key}'
        data = cache.get(key)
        cache.set(api_key, None)
        cache.set(key, None)
        if data is None: data = []
        
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
        csv_list = []
        for element in data:
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

        email = {'email': request.user.email}
        response = requests.post(endpoint, headers=headers, files=files, data=email)
        if response.status_code != 200:
            return Response({'message': 'Bad Request'}, status=400)
        return Response({'message': str(response.status_code), 'data': data})


class OzonTakeRequests(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})
        endpoint = "http://odoo-web:8069/take_requests"
        headers = {"Cookie": f"session_id={session_id}"}
        response = requests.post(endpoint, headers=headers)

        if response.status_code != 200:
            return Response({'message': 'Bad Request'}, status=400)

        response_data = response.json()
        return Response(response_data)


class DownloadExtension(APIView):
    def get(self, request, *args, **kwargs):
        extension_path = "./extension.7z"

        response = FileResponse(open(extension_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="OzonExtension.zip"'
        return response


class FileUploadView(View):
    template_name = 'upload_file.html'
    extension_path = "./extension.7z"
    
    def get(self, request, *args, **kwargs):
        form = FileUploadForm()
        return render(request, APP_NAME + self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            self.handle_uploaded_file(request.FILES['file'])
            return redirect('home')
        return render(request, APP_NAME + self.template_name, {'form': form})

    def handle_uploaded_file(self, file):
        with open(self.extension_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)


class AdsUsers(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        token = request.auth
        api_key = token.key
        data = cache.get(api_key)
        # cache.set(api_key, None)
        return Response(data)

    def post(self, request, *args, **kwargs):
        token = request.auth
        api_key = token.key
        ad = request.data

        data = cache.get(api_key)
        if data is None: data = []
        data.append(ad)
        cache.set(api_key, data, 20000)

        return Response({'message': 'Объявление успешно сохранено'})


class AllAdsUsers(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        token = request.auth
        api_key = token.key
        ads = request.data

        key = f'all--{api_key}'
        data = cache.get(key)
        if data is None: data = []
        data.extend(ads)
        cache.set(key, data, 20000)
        cache.set(api_key, None)

        return Response({'message': 'Успешно сохранены все данные'})


class GetInfoAboutAds(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        token = request.auth
        api_key = token.key

        key = f'all--{api_key}'
        data = cache.get(key)
        if data is None:
            return Response({'product': 0, 'search': 0})
        
        all_searches = set()

        index = 0
        
        for index, product in enumerate(data):
            search = product.get('search')
            if not search: continue
            if search not in all_searches:
                all_searches.add(search)

        return Response({'product': index + 1, 'search': len(all_searches)})


class DeleteAds(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        token = request.auth
        api_key = token.key

        key = f'all--{api_key}'
        cache.set(key, None)
        cache.set(api_key, [])

        return Response({'status': 'success'})


class DownloadCsvFile(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})

        token = request.auth
        api_key = token.key
        key = f'all--{api_key}'
        data = cache.get(key)
        if data is None: data = []

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
        csv_list = []
        for element in data:
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

        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(csv_data.encode())
        temp_file.close()

        # Отправьте файл обратно клиенту
        response = FileResponse(open(temp_file.name, 'rb'))
        response['Content-Disposition'] = 'attachment; filename="output.csv"'
        return response