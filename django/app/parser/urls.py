from django.urls import path
from . import views

urlpatterns = [
    path('parsing-ozon/', views.OzonParsing.as_view()),
]
