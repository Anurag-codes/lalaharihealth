"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.urls import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path(
        'api/v1/health/swagger-documentation/',
        SpectacularSwaggerView.as_view(url_name='api-schema'),
        name='swagger-documentation',
    ),
    path('api/v1/core/', include('apps.core.urls')),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/doctors/', include('apps.doctors.urls')),
    path('api/v1/patients/', include('apps.patients.urls')),
    path('api/v1/treatments/', include('apps.treatments.urls')),
    path('api/v1/hospitals/', include('apps.hospitals.urls')),
    path('api/v1/consultations/', include('apps.consultations.urls')),
    path('api/v1/appointments/', include('apps.appointments.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
