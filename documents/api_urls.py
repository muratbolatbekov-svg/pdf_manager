from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import CategoryViewSet, DocumentViewSet, StatsAPIView

router = DefaultRouter()
router.register('documents', DocumentViewSet, basename='api-document')
router.register('categories', CategoryViewSet, basename='api-category')

urlpatterns = router.urls + [
    path('stats/', StatsAPIView.as_view(), name='api-stats'),
]
