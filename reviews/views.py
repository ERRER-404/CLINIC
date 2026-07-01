from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer
from accounts.permissions import ReadOnly, IsPatient


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filterset_fields = ['doctor', 'treatment', 'rating']
    ordering_fields = ['created_at', 'rating']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action == 'create':
            return [IsPatient()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        qs = Review.objects.select_related(
            'patient__user', 'doctor__user', 'treatment'
        )
        
        if user.role == 'PATIENT' and hasattr(user, 'patient_profile'):
            return qs.filter(patient=user.patient_profile)
        
        return qs.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, 'patient_profile'):
            return Response({'error': 'Seuls les patients peuvent laisser un avis'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)
