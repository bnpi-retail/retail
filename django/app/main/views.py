from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.authtoken.models import Token

APP_NAME = __package__ + '/'

def home(request):
    if request.user.is_authenticated:
        token, created = Token.objects.get_or_create(user=request.user)

        context = {
            'user': request.user,
            'api_token': token.key,
        }

        return render(request, 'main/home.html', context)
    else:
        return render(request, 'main/home.html')
