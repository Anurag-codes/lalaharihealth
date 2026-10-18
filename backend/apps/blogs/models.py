from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .media import validate_public_url, validate_video_url


class BlogPost(models.Model):
    class Kind(models.TextChoices):
        EXTERNAL = 'external', 'External blog / video link'
        ARTICLE = 'article', 'Original article'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, help_text='Public URL name. Keep it unchanged after publishing.')
    description = models.TextField(max_length=1000, help_text='Short summary shown on cards and at the top of the post.')
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.ARTICLE)
    cover_image = models.ImageField(upload_to='blogs/covers/', blank=True)
    cover_alt = models.CharField(max_length=250, blank=True, help_text='Describe the cover image for readers using assistive technology.')
    source_url = models.URLField(max_length=1000, blank=True, validators=[validate_public_url], help_text='For external posts: original blog, YouTube video or other source. HTTP/HTTPS only.')
    author_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(default=timezone.now, help_text='Published posts become public at this time. Future dates schedule publication.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-id']
        indexes = [models.Index(fields=['status', 'published_at'])]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        errors = {}
        if self.kind == self.Kind.ARTICLE and self.source_url:
            errors['source_url'] = 'Original articles use content blocks. Clear the external source link.'
        if self.status == self.Status.PUBLISHED:
            if self.kind == self.Kind.EXTERNAL and not self.source_url:
                errors['source_url'] = 'An external post needs a source link before publishing.'
            if not self.cover_image:
                errors['cover_image'] = 'Upload a cover image before publishing.'
            if not self.cover_alt.strip():
                errors['cover_alt'] = 'Describe the cover image before publishing.'
        if errors:
            raise ValidationError(errors)


class BlogBlock(models.Model):
    class Kind(models.TextChoices):
        HEADING = 'heading', 'Heading'
        PARAGRAPH = 'paragraph', 'Paragraph'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video link'

    class HeadingLevel(models.TextChoices):
        H2 = 'h2', 'Main heading (H2)'
        H3 = 'h3', 'Subheading (H3)'

    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='blocks')
    position = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first; use 10, 20, 30 to leave room for inserts.')
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PARAGRAPH)
    heading_level = models.CharField(max_length=2, choices=HeadingLevel.choices, default=HeadingLevel.H2)
    text = models.TextField(blank=True, help_text='Heading or paragraph text. Plain text only; blank lines separate paragraphs.')
    image = models.ImageField(upload_to='blogs/content/', blank=True)
    image_alt = models.CharField(max_length=250, blank=True)
    video_url = models.URLField(max_length=1000, blank=True, validators=[validate_video_url])
    caption = models.CharField(max_length=500, blank=True, help_text='Optional caption for an image or video.')

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.position}: {self.get_kind_display()}'

    def clean(self):
        super().clean()
        errors = {}
        if self.kind in (self.Kind.HEADING, self.Kind.PARAGRAPH):
            if not self.text.strip():
                errors['text'] = 'Enter text for this heading or paragraph.'
            if self.image or self.video_url:
                errors['kind'] = 'Text blocks cannot contain an image or video. Add a separate block.'
        elif self.kind == self.Kind.IMAGE:
            if not self.image:
                errors['image'] = 'Upload an image for this block.'
            if not self.image_alt.strip():
                errors['image_alt'] = 'Describe the image for accessibility.'
            if self.text or self.video_url:
                errors['kind'] = 'Image blocks use an image and optional caption only.'
        elif self.kind == self.Kind.VIDEO:
            if not self.video_url:
                errors['video_url'] = 'Enter a supported video link.'
            if self.text or self.image:
                errors['kind'] = 'Video blocks use a video link and optional caption only.'
        if errors:
            raise ValidationError(errors)
