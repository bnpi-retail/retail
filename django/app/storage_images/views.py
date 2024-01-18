from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class DrawGraph(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        current_data = request.data.get('current', [])
        last_data = request.data.get('last', [])
        
        data = {'current_data': current_data, 'last_data': last_data}
        return Response(data, status=200)
