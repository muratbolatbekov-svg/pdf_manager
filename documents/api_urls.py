from rest_framework.routers import DefaultRouter

from .api import CategoryViewSet, DocumentViewSet

router = DefaultRouter()
router.register('documents', DocumentViewSet, basename='api-document')
router.register('categories', CategoryViewSet, basename='api-category')

urlpatterns = router.urls
