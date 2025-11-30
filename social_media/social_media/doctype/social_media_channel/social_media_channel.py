import frappe
from frappe.model.document import Document


class SocialMediaChannel(Document):
	def validate(self):
		if self.is_default:
			# Ensure only one default channel per platform per company
			existing = frappe.db.exists("Social Media Channel", {
				"platform": self.platform,
				"company": self.company,
				"is_default": 1,
				"name": ["!=", self.name]
			})
			
			if existing:
				frappe.throw(f"Default channel already exists for {self.platform} in {self.company}")
	
	@frappe.whitelist()
	def sync_channel_info(self):
		"""Sync channel information from platform"""
		try:
			account_doc = frappe.get_doc("Social Account", {"channel": self.name})
			
			from social_media.api_social import get_connector
			connector = get_connector(self.platform, account_doc)
			
			if connector:
				# Get channel info from platform API
				info = connector.get_channel_info()
				
				if info.get("success"):
					data = info.get("data", {})
					self.description = data.get("description", self.description)
					self.profile_image = data.get("profile_image", self.profile_image)
					self.follower_count = data.get("follower_count", self.follower_count)
					self.last_sync = frappe.utils.now()
					self.save()
					
					frappe.msgprint("Channel information synced successfully")
				else:
					frappe.throw(f"Sync failed: {info.get('error')}")
			else:
				frappe.throw(f"No connector available for {self.platform}")
				
		except Exception as e:
			frappe.throw(f"Sync error: {str(e)}")
	
	@frappe.whitelist()
	def test_connection(self):
		"""Test connection to platform"""
		try:
			account_doc = frappe.get_doc("Social Account", {"channel": self.name})
			
			from social_media.api_social import get_connector
			connector = get_connector(self.platform, account_doc)
			
			if connector:
				# Test API connection
				result = connector.test_connection()
				
				if result.get("success"):
					self.status = "Active"
					self.save()
					frappe.msgprint("Connection test successful")
				else:
					self.status = "Error"
					self.save()
					frappe.throw(f"Connection failed: {result.get('error')}")
			else:
				frappe.throw(f"No connector available for {self.platform}")
				
		except Exception as e:
			self.status = "Error"
			self.save()
			frappe.throw(f"Connection test failed: {str(e)}")