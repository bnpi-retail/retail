from django.urls import path
from . import views

urlpatterns = [
    path('take_ozon_data/', views.OzonPlugin.as_view()),
    path('take_requests/', views.OzonTakeRequests.as_view()),

    path('check_auth/', views.CheckAuth.as_view()),
    path('download-extension/', views.DownloadExtension.as_view(), name='download-extension'),
    path('upload/', views.FileUploadView.as_view(), name='upload_file'),

    # Session
    path('ads_users/', views.AdsUsers.as_view(), name='ads_users'),
    path('ads_users/save_all', views.AllAdsUsers.as_view(), name='ads_users_save_alls'),
    path('ads_users/statistics', views.GetInfoAboutAds.as_view(), name='ads_users_statistics'),
    path('ads_users/delete', views.DeleteAds.as_view(), name='ads_users_delete'),
    path('ads_users/download', views.DownloadCsvFile.as_view(), name='ads_users_download'),
]
