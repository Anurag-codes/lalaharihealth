from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from .models import BlogPost
from .serializers import BlogDetailSerializer, BlogSummarySerializer


class BlogPagination(PageNumberPagination):
    page_size = 9
    page_size_query_param = 'page_size'
    max_page_size = 24


def published_posts():
    return BlogPost.objects.filter(status=BlogPost.Status.PUBLISHED, published_at__lte=timezone.now())


@extend_schema(tags=['Blogs'], summary='List published blogs, newest first')
class BlogListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BlogSummarySerializer
    pagination_class = BlogPagination

    def get_queryset(self):
        return published_posts()


@extend_schema(tags=['Blogs'], summary='Read a published blog')
class BlogDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = BlogDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return published_posts().prefetch_related('blocks')
