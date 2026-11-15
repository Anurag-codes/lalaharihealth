from django.urls import path

from . import views
from .video_calls import PatientVideoJoinView
from .offers import FreeConsultationOfferView

app_name = 'appointments'

urlpatterns = [
	path('free-consultation-offer/', FreeConsultationOfferView.as_view()),
	path('slots/', views.SlotsView.as_view()),
	path('slot-dates/', views.SlotDatesView.as_view()),
	path('', views.AppointmentListCreateView.as_view()),
	path('<int:appointment_id>/', views.AppointmentDetailView.as_view()),
	path('<int:appointment_id>/video/join/', PatientVideoJoinView.as_view(), name='patient-video-join'),
	path('<int:appointment_id>/assign-doctor/', views.AssignDoctorView.as_view()),
	path('<int:appointment_id>/confirm-completion/', views.ConfirmCompletionView.as_view()),
]
