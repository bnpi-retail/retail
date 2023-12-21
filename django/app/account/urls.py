from django.contrib.auth import views as auth_views
# from django.urls import path
# from . import views

# urlpatterns = [
#     path('registration/', views.registration, name='register'),
#     path('login/', auth_views.LoginView.as_view(), name='login'),

# ]

from django.urls import path
from .views import GetAPIView

urlpatterns = [
    path('get_api/', GetAPIView.as_view(), name='get_api'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]