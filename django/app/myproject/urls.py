from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.authtoken.views import obtain_auth_token


urlpatterns = [
    path('', include('main.urls')),
    path('account/', include('account.urls')),
    path('admin/', admin.site.urls),
    path('', include('ozon_plugin.urls')),
    path('api/token/', obtain_auth_token, name='api_token_obtain'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)