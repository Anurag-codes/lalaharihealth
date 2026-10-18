from django.urls import path

from . import views
from .conditions import ConditionChoicesView

app_name = 'consultations'

urlpatterns = [
	path('conditions/', ConditionChoicesView.as_view()),
	path('', views.ConsultationListCreateView.as_view()),
	path('<int:consultation_id>/', views.ConsultationDetailView.as_view()),
	path('<int:consultation_id>/history/', views.ConsultationHistoryView.as_view()),
	path('<int:consultation_id>/preview/', views.CasePreviewView.as_view()),
	path('<int:consultation_id>/documents/', views.ConsultationDocumentsView.as_view()),
	path('<int:consultation_id>/documents/<int:document_id>/', views.ConsultationDocumentDetailView.as_view()),
	path('<int:consultation_id>/documents/<int:document_id>/download/', views.ConsultationDocumentDownloadView.as_view()),
]
