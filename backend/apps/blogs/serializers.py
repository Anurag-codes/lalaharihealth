from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .media import video_source
from .models import BlogBlock, BlogPost


class VideoSourceSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=['embed', 'file'])
    url = serializers.URLField()


class BlogBlockSerializer(serializers.ModelSerializer):
    video = serializers.SerializerMethodField()

    class Meta:
        model = BlogBlock
        fields = ['id', 'position', 'kind', 'heading_level', 'text', 'image', 'image_alt', 'caption', 'video']

    @extend_schema_field(VideoSourceSerializer(allow_null=True))
    def get_video(self, obj) -> dict[str, str] | None:
        return video_source(obj.video_url)


class BlogSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'slug', 'description', 'kind', 'cover_image', 'cover_alt', 'author_name', 'published_at']


class BlogDetailSerializer(BlogSummarySerializer):
    blocks = BlogBlockSerializer(many=True, read_only=True)
    source_video = serializers.SerializerMethodField()

    class Meta(BlogSummarySerializer.Meta):
        fields = BlogSummarySerializer.Meta.fields + ['source_url', 'source_video', 'blocks']

    @extend_schema_field(VideoSourceSerializer(allow_null=True))
    def get_source_video(self, obj) -> dict[str, str] | None:
        return video_source(obj.source_url) if obj.kind == BlogPost.Kind.EXTERNAL else None
