import requests
from os import getenv
from openai import OpenAI

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from account.services import connect_to_odoo_api_with_auth


class TakeDescriptionFromOdoo(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})
        endpoint = "http://odoo-web:8069/get-descriptions-lots"
        headers = {"Cookie": f"session_id={session_id}"}
        response = requests.get(endpoint, headers=headers)

        if response.status_code != 200:
            return Response({'message': 'Bad Request'}, status=400)

        response_data = response.json()
        return Response(response_data)


class TakeRequestToGPT(APIView):
    def post(self, request):
        text_param = request.data.get('text')
        if not text_param is not None:
            response_data = {'status': False, 'message': 'Parameter "text" is missing'}
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        api_key = getenv('GPT_API_KEY')
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an ordinary shopper looking for information about a computer cooler."},
                {"role": "user", "content": f"какие запросы люди вводят в маркетплейсе, когда хотят купить следующий товар: {text_param}?"},
                {"role": "user", "content": "Запросы должны быть маленькими и короткими и не столь точными в количестве 10!"},
                {"role": "user", "content": "Ответь на русском!"},
                {"role": "user", "content": "Напиши только запросы и начиная каждый запрос с #, чтобы я мог просто разделить их, и закнчи запрос ;"},
            ]
        )
        answer = completion.choices[0].message
        
        response_data = {'status': True, 'answer': answer}
        return Response(response_data, status=status.HTTP_200_OK)
    

class SendToOdoo(APIView):
    def post(self, request):
        id_param = request.data.get('id')
        seaches_queries = request.data.get('message')
        if id_param is None or seaches_queries is None:
            response_data = {'status': False, 'message': 'Parameter "id" or "answer is missing'}
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: return Response({'status': False})
        endpoint = "http://odoo-web:8069/set-searches-queries"
        headers = {"Cookie": f"session_id={session_id}"}
        payload = {'id': id_param, 'message': seaches_queries}
        response = requests.post(endpoint, headers=headers, json=payload)

        if response.status_code != 200:
            return Response({'message': 'Bad Request'}, status=400)

        response_data = response.json()
        return Response(response_data)