from django.urls import path
from .views import ChatbotAPIView, MSDSQueryView

urlpatterns = [
    path('', ChatbotAPIView.as_view(), name='chatbot-api'),
    path('msds/', MSDSQueryView.as_view(), name='msds-query'),
]
