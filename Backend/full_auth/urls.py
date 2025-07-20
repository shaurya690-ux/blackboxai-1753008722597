

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views import ChemicalViewSet
from users.views import LoginView

router = DefaultRouter()
router.register(r'chemicals', ChemicalViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include(router.urls)),
    path("api/", include("djoser.urls")),
    path("api/", include("djoser.urls.jwt")),
    path("api/chatbot/", include("chatbot.urls")),
    path("login/", LoginView.as_view(), name="login"),
]
