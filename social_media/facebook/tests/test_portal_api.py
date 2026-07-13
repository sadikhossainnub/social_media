import frappe
import unittest
from social_media.facebook.portal_api import get_pages, get_conversations


class TestFacebookPortalAPI(unittest.TestCase):
	def setUp(self):
		# Setup page
		self.test_page = frappe.get_doc({
			"doctype": "Facebook Page",
			"page_id": "test_page_999",
			"page_name": "API Test Page",
			"access_token": "token_api",
			"status": "Active"
		})
		self.test_page.save(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Facebook Page", {"page_id": "test_page_999"})
		frappe.db.commit()

	def test_get_pages_endpoint(self):
		# Standard desk user / System Manager should view all connected pages
		frappe.set_user("Administrator")
		res = get_pages()
		self.assertTrue(res["success"])
		
		# Confirm our test page is included in the list
		page_names = [p["page_name"] for p in res["data"]]
		self.assertIn("API Test Page", page_names)

	def test_get_conversations_empty(self):
		frappe.set_user("Administrator")
		res = get_conversations(page_id=self.test_page.name)
		self.assertTrue(res["success"])
		self.assertEqual(len(res["data"]), 0)
