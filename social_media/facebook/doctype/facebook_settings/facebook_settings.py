import frappe
import requests
from frappe.model.document import Document


class FacebookSettings(Document):
	def validate(self):
		if self.enabled and not all([self.app_id, self.app_secret, self.access_token]):
			frappe.throw("App ID, App Secret, and Access Token are required when Facebook integration is enabled")
	
	@frappe.whitelist()
	def test_connection(self):
		"""Test Facebook API connection"""
		try:
			url = f"https://graph.facebook.com/{self.api_version}/me"
			response = requests.get(url, params={"access_token": self.get_password("access_token")})
			
			if response.status_code == 200:
				data = response.json()
				frappe.msgprint(f"Connection successful! Connected to: {data.get('name', 'Facebook')}")
				return {"success": True, "data": data}
			else:
				frappe.throw(f"Connection failed: {response.text}")
				
		except Exception as e:
			frappe.throw(f"Connection test failed: {str(e)}")
	
	def get_access_token(self):
		"""Get decrypted access token"""
		return self.get_password("access_token")
	
	def get_app_secret(self):
		"""Get decrypted app secret"""
		return self.get_password("app_secret")