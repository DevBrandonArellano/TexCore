from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status

class SedeAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_list_sedes_api_endpoint(self):
        """Test that the API endpoint for listing sedes is working."""
        # The name 'sede-list' is what we defined in gestion/urls.py
        url = reverse('sede-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)