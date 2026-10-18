from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import inlineformset_factory
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .admin import BlogBlockFormSet
from .media import validate_public_url, validate_video_url, video_source
from .models import BlogBlock, BlogPost


class BlogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.article = BlogPost.objects.create(
            title='Understanding your appointment',
            slug='understanding-your-appointment',
            description='Questions to prepare.',
            kind=BlogPost.Kind.ARTICLE,
            status=BlogPost.Status.PUBLISHED,
            cover_image='blogs/covers/appointment.png',
            cover_alt='A notebook with questions',
        )
        BlogBlock.objects.create(post=cls.article, position=20, kind='paragraph', text='Ask about the fee.')
        BlogBlock.objects.create(post=cls.article, position=10, kind='heading', text='Prepare questions')
        BlogBlock.objects.create(post=cls.article, position=30, kind='video', video_url='https://youtu.be/jJO4-9VS2A0')
        cls.external = BlogPost.objects.create(
            title='A healthcare discussion',
            slug='a-healthcare-discussion',
            description='A third-party video.',
            kind=BlogPost.Kind.EXTERNAL,
            source_url='https://www.youtube.com/shorts/jJO4-9VS2A0',
            status=BlogPost.Status.PUBLISHED,
            cover_image='blogs/covers/discussion.png',
            cover_alt='Discussion',
        )
        cls.draft = BlogPost.objects.create(title='Draft', slug='draft', description='Not public.')
        cls.scheduled = BlogPost.objects.create(
            title='Future', slug='future', description='Not yet public.',
            status=BlogPost.Status.PUBLISHED, published_at=timezone.now() + timedelta(days=1),
        )

    def setUp(self):
        self.client = APIClient()

    def test_list_is_paginated_and_hides_drafts_and_scheduled_posts(self):
        response = self.client.get(reverse('blogs:list'), {'page_size': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], self.external.slug)
        self.assertIsNotNone(response.data['next'])
        second = self.client.get(reverse('blogs:list'), {'page_size': 1, 'page': 2})
        self.assertEqual(second.data['results'][0]['slug'], self.article.slug)
        self.assertIsNone(second.data['next'])
        self.assertNotIn('blocks', second.data['results'][0])
        self.assertEqual(self.client.get(reverse('blogs:list'), {'page': 3}).status_code, 404)

    def test_detail_has_ordered_blocks_and_absolute_images(self):
        response = self.client.get(reverse('blogs:detail', args=[self.article.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([block['position'] for block in response.data['blocks']], [10, 20, 30])
        self.assertTrue(response.data['cover_image'].startswith('http://testserver/'))
        self.assertEqual(response.data['blocks'][2]['video']['kind'], 'embed')
        self.assertIn('youtube-nocookie.com/embed/jJO4-9VS2A0', response.data['blocks'][2]['video']['url'])

    def test_external_detail_keeps_source_and_optional_video(self):
        response = self.client.get(reverse('blogs:detail', args=[self.external.slug]))
        self.assertEqual(response.data['source_url'], self.external.source_url)
        self.assertEqual(response.data['blocks'], [])
        self.assertEqual(response.data['source_video']['kind'], 'embed')
        self.external.source_url = 'https://example.com/health-article'
        self.external.save()
        response = self.client.get(reverse('blogs:detail', args=[self.external.slug]))
        self.assertIsNone(response.data['source_video'])

    def test_unpublished_or_missing_detail_is_404(self):
        for slug in ['draft', 'future', 'missing']:
            with self.subTest(slug=slug):
                self.assertEqual(self.client.get(reverse('blogs:detail', args=[slug])).status_code, 404)

    def test_public_api_is_read_only_even_for_staff(self):
        for user in [None, get_user_model().objects.create_user('editor', is_staff=True)]:
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.post(reverse('blogs:list'), {}, format='json').status_code, 405)
            detail = reverse('blogs:detail', args=[self.article.slug])
            self.assertEqual(self.client.patch(detail, {'title': 'Changed'}, format='json').status_code, 405)
            self.assertEqual(self.client.delete(detail).status_code, 405)

    def test_publication_requires_cover_alt_and_external_source(self):
        post = BlogPost(title='Example', slug='example', description='Summary', kind='external', status='published')
        with self.assertRaises(ValidationError) as context:
            post.full_clean()
        self.assertTrue({'cover_image', 'cover_alt', 'source_url'} <= context.exception.message_dict.keys())
        self.article.source_url = 'https://example.com/'
        with self.assertRaises(ValidationError):
            self.article.full_clean()

    def test_blocks_validate_required_fields_and_reject_mixed_content(self):
        for kwargs in [
            {'kind': 'heading', 'text': ' '},
            {'kind': 'paragraph', 'text': 'Text', 'video_url': 'https://youtu.be/jJO4-9VS2A0'},
            {'kind': 'image', 'image_alt': 'Description'},
            {'kind': 'image', 'image': 'blogs/content/a.png'},
            {'kind': 'video'},
            {'kind': 'video', 'video_url': 'https://example.com/watch'},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                BlogBlock(post=self.article, **kwargs).full_clean()

    def test_supported_videos_and_unsafe_links(self):
        supported = [
            ('https://youtu.be/jJO4-9VS2A0', 'embed'),
            ('https://www.youtube.com/watch?v=jJO4-9VS2A0&t=20', 'embed'),
            ('https://www.youtube.com/shorts/jJO4-9VS2A0', 'embed'),
            ('https://vimeo.com/12345678', 'embed'),
            ('https://example.com/video.mp4?token=public', 'file'),
        ]
        for url, kind in supported:
            with self.subTest(url=url):
                validate_video_url(url)
                self.assertEqual(video_source(url)['kind'], kind)
        for url in ['javascript:alert(1)', 'https://user:pass@example.com/video.mp4', 'https://youtube.com.evil.example/watch?v=jJO4-9VS2A0']:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                validate_video_url(url)
        with self.assertRaises(ValidationError):
            validate_public_url('data:text/html,hello')

    def block_formset(self, post, blocks):
        formset_class = inlineformset_factory(
            BlogPost, BlogBlock, formset=BlogBlockFormSet,
            fields=['position', 'kind', 'heading_level', 'text', 'image', 'image_alt', 'video_url', 'caption'],
            extra=0,
        )
        data = {'blocks-TOTAL_FORMS': str(len(blocks)), 'blocks-INITIAL_FORMS': '0'}
        for index, block in enumerate(blocks):
            for key, value in {'heading_level': 'h2', **block}.items():
                data[f'blocks-{index}-{key}'] = value
        return formset_class(data=data, instance=post, prefix='blocks')

    def test_admin_enforces_article_blocks_external_type_and_unique_order(self):
        post = BlogPost(title='New', slug='new', description='Summary', status='published')
        self.assertFalse(self.block_formset(post, []).is_valid())
        paragraph = {'position': 10, 'kind': 'paragraph', 'text': 'Content'}
        self.assertTrue(self.block_formset(post, [paragraph]).is_valid())
        self.assertFalse(self.block_formset(post, [paragraph, paragraph]).is_valid())
        post.kind = 'external'
        self.assertFalse(self.block_formset(post, [paragraph]).is_valid())
        post.kind = 'article'
        post.status = 'draft'
        self.assertTrue(self.block_formset(post, []).is_valid())

    def test_admin_restricts_authoring_and_saves_original_article(self):
        url = reverse('admin:blogs_blogpost_add')
        self.assertEqual(self.client.get(url).status_code, 302)
        editor = get_user_model().objects.create_superuser('publisher', 'publisher@example.com', 'test-password')
        self.client.force_login(editor)
        self.assertEqual(self.client.get(url).status_code, 200)
        image = SimpleUploadedFile(
            'cover.gif',
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;',
            content_type='image/gif',
        )
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post(url, {
                'title': 'Admin article', 'slug': 'admin-article', 'description': 'An original article.',
                'kind': 'article', 'status': 'published', 'cover_image': image, 'cover_alt': 'Cover',
                'published_at_0': '2026-01-01', 'published_at_1': '12:00:00',
                'blocks-TOTAL_FORMS': '1', 'blocks-INITIAL_FORMS': '0',
                'blocks-0-position': '10', 'blocks-0-kind': 'paragraph',
                'blocks-0-heading_level': 'h2', 'blocks-0-text': 'Article body.',
                '_save': 'Save',
            })
            self.assertEqual(response.status_code, 302)
            post = BlogPost.objects.get(slug='admin-article')
            self.assertEqual(post.blocks.get().text, 'Article body.')
            self.assertEqual(self.client.get(reverse('blogs:detail', args=[post.slug])).status_code, 200)
