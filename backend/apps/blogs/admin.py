from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import BlogBlock, BlogPost


class BlogBlockFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        blocks = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
        ]
        if self.instance.kind == BlogPost.Kind.EXTERNAL and blocks:
            raise ValidationError('External posts use the source link. Remove the content blocks or select Original article.')
        if self.instance.kind == BlogPost.Kind.ARTICLE and self.instance.status == BlogPost.Status.PUBLISHED and not blocks:
            raise ValidationError('Add at least one content block before publishing an original article.')
        positions = [form.cleaned_data['position'] for form in blocks]
        if len(positions) != len(set(positions)):
            raise ValidationError('Give each content block a different position to define its order.')


class BlogBlockInline(admin.StackedInline):
    model = BlogBlock
    formset = BlogBlockFormSet
    extra = 0
    fields = ['position', 'kind', 'heading_level', 'text', 'image', 'image_alt', 'video_url', 'caption']


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'status', 'published_at', 'author_name']
    list_filter = ['kind', 'status']
    search_fields = ['title', 'description', 'author_name']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    inlines = [BlogBlockInline]
    fieldsets = [
        ('Post', {'fields': ['title', 'slug', 'description', 'kind', 'author_name']}),
        ('Cover image', {'fields': ['cover_image', 'cover_alt']}),
        ('External source', {
            'fields': ['source_url'],
            'description': 'External posts link to another blog or video. Original articles use the ordered content blocks below.',
        }),
        ('Publication', {'fields': ['status', 'published_at', 'created_at', 'updated_at']}),
    ]
