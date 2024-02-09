from django.urls import path
from .views import DrawGraph

urlpatterns = [
    path('draw_graph', DrawGraph.as_view()),
]
