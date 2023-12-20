import os
import requests

from django.http import FileResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

username = os.getenv('username_odoo')
password = os.getenv('password_odoo')
db_odoo = os.getenv('db_odoo')
 
def connect_to_odoo_api_with_auth(url: str):
    session_url = f"{url}/web/session/authenticate"
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": db_odoo,
            "login": username,
            "password": password,
        },
    }
    session_response = requests.post(session_url, json=data)
    session_data = session_response.json()

    if session_data.get("result") and session_response.cookies.get("session_id"):
        session_id = session_response.cookies["session_id"]
        return session_id
    else:
        print(f'Error: Failed to authenticate - {session_data.get("error")}')
        return False

class CheckAuth(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({'message': 'Authentication successful'}, status=200)

class OzonPlugin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        url = "http://odoo-web:8069/"
        path_odoo = "take_ozon_data"

        session_id = connect_to_odoo_api_with_auth(url)
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

        endpoint = f"{url}{path_odoo}"
        headers = {"Cookie": f"session_id={session_id}"}
        files = {'file': ('output.csv', csv_data)}
        response = requests.post(endpoint, headers=headers, files=files)

        return Response({'message': str(response.status_code)})


class DownloadExtension(APIView):
    def get(self, request, *args, **kwargs):
        extension_path = "./extension.7z"

        response = FileResponse(open(extension_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="OzonExtension.zip"'
        return response
    
class UploadExtension(APIView):
    def post(self, request, *args, **kwargs):
        extension_path = "./extension.7z"

        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            with open(extension_path, 'wb') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            return Response({"message": "File uploaded successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
