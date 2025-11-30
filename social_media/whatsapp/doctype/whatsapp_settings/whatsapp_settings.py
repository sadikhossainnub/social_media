import frappe
import requests
from frappe.model.document import Document


class WhatsAppSettings(Document):
	def validate(self):
		if self.enabled and not all([self.access_token, self.phone_number_id]):
			frappe.throw("Access Token and Phone Number ID are required when WhatsApp integration is enabled")
	
	@frappe.whitelist()
	def test_connection(self):
		"""Test WhatsApp Business API connection"""
		try:
			url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
			headers = {"Authorization": f"Bearer {self.get_password('access_token')}"}
			response = requests.get(url, headers=headers)
			
			if response.status_code == 200:
				data = response.json()
				frappe.msgprint(f"Connection successful! Phone Number: {data.get('display_phone_number', 'Connected')}")
				return {"success": True, "data": data}
			else:
				frappe.throw(f"Connection failed: {response.text}")
				
		except Exception as e:
			frappe.throw(f"Connection test failed: {str(e)}")
	
	def get_access_token(self):
		"""Get decrypted access token"""
		return self.get_password("access_token")