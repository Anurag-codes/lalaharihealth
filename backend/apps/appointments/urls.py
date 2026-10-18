from django.urls import path

from . import views

app_name = 'appointments'

urlpatterns = [
	path('slots/', views.SlotsView.as_view()),
	path('slot-dates/', views.SlotDatesView.as_view()),
	path('', views.AppointmentListCreateView.as_view()),
	path('<int:appointment_id>/', views.AppointmentDetailView.as_view()),
	path('<int:appointment_id>/assign-doctor/', views.AssignDoctorView.as_view()),
]
