from django.contrib import admin
from django.urls import path, include

from documents.views import permission_denied

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('documents.api_urls')),
    path('', include('documents.urls')),
]

handler403 = permission_denied
