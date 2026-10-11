from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
	path('orders/', views.PaymentOrderView.as_view()),
	path('verify/', views.PaymentVerifyView.as_view()),
	path('webhooks/razorpay/', views.RazorpayWebhookView.as_view()),
	path('<int:payment_id>/', views.PaymentDetailView.as_view()),
]
