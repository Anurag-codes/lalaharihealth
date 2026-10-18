from django.urls import path

from .views import BlogDetailView, BlogListView

app_name = 'blogs'

urlpatterns = [
    path('', BlogListView.as_view(), name='list'),
    path('<slug:slug>/', BlogDetailView.as_view(), name='detail'),
]
