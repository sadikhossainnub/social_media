import frappe
import unittest
from unittest.mock import patch, MagicMock
from social_media.facebook.graph_client import FacebookGraphClient


class TestFacebookGraphClient(unittest.TestCase):
	def setUp(self):
		# Setup mock settings and page
		self.mock_settings = frappe.get_doc({
			"doctype": "Facebook Settings",
			"graph_api_version": "v21.0",
			"ai_provider": "primellm"
		})
		self.mock_settings.save(ignore_permissions=True)

		self.mock_page = frappe.get_doc({
			"doctype": "Facebook Page",
			"page_id": "12345",
			"page_name": "Test Page",
			"access_token": "secret_token",
			"status": "Active"
		})
		self.mock_page.save(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Facebook Page", {"page_id": "12345"})
		frappe.db.delete("Facebook Settings", "Facebook Settings")
		frappe.db.commit()

	@patch("social_media.facebook.graph_client.requests.get")
	def test_get_page_posts(self, mock_get):
		# Mock response
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"data": [{"id": "post_1", "message": "Hello World"}]}
		mock_response.headers = {}
		mock_get.return_value = mock_response

		client = FacebookGraphClient(page_id=self.mock_page.name)
		posts = client.get_page_posts()
		
		self.assertEqual(len(posts.get("data", [])), 1)
		self.assertEqual(posts["data"][0]["id"], "post_1")

	@patch("social_media.facebook.graph_client.requests.post")
	def test_create_post(self, mock_post):
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"id": "new_post_id"}
		mock_response.headers = {}
		mock_post.return_value = mock_response

		client = FacebookGraphClient(page_id=self.mock_page.name)
		res = client.create_page_post("Hello from test suite")
		
		self.assertEqual(res.get("id"), "new_post_id")
