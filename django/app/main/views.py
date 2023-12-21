from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.authtoken.models import Token

APP_NAME = __package__ + '/'

@login_required(login_url='/account/login/')
def home(request):
    token, created = Token.objects.get_or_create(user=request.user)

    context = {
        'user': request.user,
        'api_token': token.key,
    }

    return render(request, APP_NAME + 'home.html', context)
