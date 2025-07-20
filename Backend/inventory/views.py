from django.shortcuts import render
from rest_framework import viewsets, permissions
from users.models import Chemical
from users.serializers import ChemicalSerializer
from full_auth.permissions import IsTeacherOrAssistant

# Create your views here.

class ChemicalViewSet(viewsets.ModelViewSet):
    queryset = Chemical.objects.all()
    serializer_class = ChemicalSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]  # All logged-in users can view
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacherOrAssistant()]  # Only teachers/assistants can modify
        return super().get_permissions()
