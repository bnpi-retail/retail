from django.urls import path
from .views import TakeDescriptionFromOdoo, TakeRequestToGPT, SendToOdoo

urlpatterns = [
    path('take-description-from-odoo/', TakeDescriptionFromOdoo.as_view()),
    path('send-to-odoo/', SendToOdoo.as_view()),
    path('take-request-to-gpt/', TakeRequestToGPT.as_view()),
]
