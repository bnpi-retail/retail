from django.urls import path
from . import views

urlpatterns = [
    path('take_ozon_data/', views.OzonPlugin.as_view()),
    path('check_auth/', views.CheckAuth.as_view()),
    path('download-extension/', views.DownloadExtension.as_view()),
    path('upload-extension/', views.UploadExtension.as_view()),
]