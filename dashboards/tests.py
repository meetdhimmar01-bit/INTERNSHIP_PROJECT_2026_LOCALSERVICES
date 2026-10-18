from django.test import TestCase
from django.urls import reverse

from core.models import User


class ProviderApprovalTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_user(
			email='admin@example.com',
			name='Admin User',
			password='test-password',
			role='admin',
			is_approved=True,
		)
		self.provider = User.objects.create_user(
			email='provider@example.com',
			name='Provider User',
			password='test-password',
			role='owner',
			is_approved=False,
		)
		self.client.force_login(self.admin)

	def test_admin_can_approve_provider(self):
		response = self.client.post(
			reverse('dashboards:approve_provider', args=[self.provider.id])
		)

		self.provider.refresh_from_db()
		self.assertRedirects(response, reverse('dashboards:admin'))
		self.assertTrue(self.provider.is_approved)

	def test_admin_can_reject_provider(self):
		response = self.client.post(
			reverse('dashboards:reject_provider', args=[self.provider.id])
		)

		self.assertRedirects(response, reverse('dashboards:admin'))
		self.assertFalse(User.objects.filter(id=self.provider.id).exists())

	def test_provider_actions_reject_get_requests(self):
		response = self.client.get(
			reverse('dashboards:approve_provider', args=[self.provider.id])
		)

		self.assertEqual(response.status_code, 405)

	def test_admin_dashboard_shows_empty_provider_queue(self):
		self.provider.delete()

		response = self.client.get(reverse('dashboards:admin'))

		self.assertContains(response, 'Provider Applications')
		self.assertContains(response, 'No provider applications to review')
