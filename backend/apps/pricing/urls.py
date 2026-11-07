from django.urls import path

from .views import ConsultationFeeView, PricingView

app_name = 'pricing'

urlpatterns = [
    path('', PricingView.as_view(), name='pricing'),
    path('consultation-fee/', ConsultationFeeView.as_view(), name='consultation-fee'),
]
