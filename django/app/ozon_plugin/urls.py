from django.urls import path
from . import views

urlpatterns = [
    path('take_ozon_data/', views.OzonPlugin.as_view()),
    path('take_requests/', views.OzonTakeRequests.as_view()),

    path('check_auth/', views.CheckAuth.as_view()),
    path('download-extension/', views.DownloadExtension.as_view(), name='download-extension'),
    path('upload/', views.FileUploadView.as_view(), name='upload_file'),
]
