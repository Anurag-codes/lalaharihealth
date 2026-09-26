from django.db import models


class Testimonial(models.Model):
    """Patient success stories shown on the promotional homepage."""

    patient_name = models.CharField(max_length=150)
    patient_city = models.CharField(max_length=100, blank=True)
    quote = models.TextField()
    photo = models.ImageField(upload_to='testimonials/photos/', blank=True, null=True)
    video_url = models.URLField(blank=True, help_text='Optional testimonial video link')
    money_saved = models.PositiveIntegerField(blank=True, null=True, help_text='Amount saved in INR, for display')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.patient_name


class FAQ(models.Model):
    """Frequently asked questions shown on the homepage."""

    question = models.CharField(max_length=255)
    answer = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ContactMessage(models.Model):
    """Messages submitted through the homepage contact / callback request form."""

    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    message = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.phone_number})'
