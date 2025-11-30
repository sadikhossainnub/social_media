import frappe
from frappe.model.document import Document


class SocialAccount(Document):
	def validate(self):
		if self.expires_on and self.expires_on < frappe.utils.now():
			self.status = "Expired"
	
	def get_access_token(self):
		return self.get_password("oauth_access_token")
	
	def get_refresh_token(self):
		return self.get_password("refresh_token")
	
	def get_app_secret(self):
		return self.get_password("app_secret")