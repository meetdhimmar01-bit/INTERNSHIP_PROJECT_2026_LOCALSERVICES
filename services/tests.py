from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from core.models import User
from services.models import Category, ProviderProfile, Service


class PublicServiceTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Plumbing')
		self.approved_provider = User.objects.create_user(
			email='approved@example.com',
			name='Approved Provider',
			password='test-password',
			role='owner',
			is_approved=True,
		)
		self.pending_provider = User.objects.create_user(
			email='pending@example.com',
			name='Pending Provider',
			password='test-password',
			role='owner',
			is_approved=False,
		)
		self.approved_service = Service.objects.create(
			category=self.category,
			owner=self.approved_provider,
			name='Approved plumbing',
			base_price=Decimal('50.00'),
		)
		self.pending_service = Service.objects.create(
			category=self.category,
			owner=self.pending_provider,
			name='Pending plumbing',
			base_price=Decimal('40.00'),
		)
		self.unowned_service = Service.objects.create(
			category=self.category,
			name='Community plumbing',
			base_price=Decimal('30.00'),
		)

	def test_unapproved_provider_services_are_not_public(self):
		response = self.client.get(reverse('services:list'))

		self.assertContains(response, 'Approved plumbing')
		self.assertContains(response, 'Community plumbing')
		self.assertNotContains(response, 'Pending plumbing')
		self.assertEqual(
			self.client.get(
				reverse('services:detail', args=[self.pending_service.id])
			).status_code,
			404,
		)
		self.assertNotContains(self.client.get(reverse('services:map')), 'Pending plumbing')

	def test_approved_provider_profile_is_shown_on_service_detail(self):
		ProviderProfile.objects.create(
			user=self.approved_provider,
			experience_years=7,
			service_locations='Ahmedabad',
		)

		response = self.client.get(
			reverse('services:detail', args=[self.approved_service.id])
		)

		self.assertContains(response, 'Approved provider')
		self.assertContains(response, '7 years of experience')
		self.assertContains(response, 'Serving Ahmedabad')

	def test_homepage_only_shows_public_services(self):
		response = self.client.get(reverse('home'))

		self.assertContains(response, 'Approved plumbing')
		self.assertNotContains(response, 'Pending plumbing')

	def test_health_endpoint_checks_database(self):
		response = self.client.get(reverse('health'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.content, b'ok')
