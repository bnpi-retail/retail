from django.contrib.auth import views as auth_views
from django.urls import path
from .views import GetAPIView, GetTokenAPI

urlpatterns = [
    path('get_api/', GetAPIView.as_view(), name='get_api'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('get_api_token/', GetTokenAPI.as_view()),
]