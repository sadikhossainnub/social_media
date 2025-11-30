import frappe
from frappe.model.document import Document


class FacebookMessage(Document):
	def validate(self):
		if not self.timestamp:
			self.timestamp = frappe.utils.now()
		
		if not self.created_time:
			self.created_time = frappe.utils.now()
	
	def before_save(self):
		self.modified_time = frappe.utils.now()
	
	def after_insert(self):
		"""Auto create lead after message insertion"""
		from social_media.utils.lead_creation import create_lead_from_message
		try:
			create_lead_from_message(self)
		except Exception as e:
			frappe.log_error(f"Auto lead creation failed: {str(e)}")
	
	def send_message(self):
		"""Send message via Facebook API"""
		# Implementation for sending message
		pass
	
	def mark_as_read(self):
		"""Mark message as read"""
		self.is_read = 1
		self.save()
	
	def mark_as_delivered(self):
		"""Mark message as delivered"""
		self.is_delivered = 1
		self.status = "delivered"
		self.save()