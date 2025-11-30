import frappe
from frappe.model.document import Document


class WhatsAppMessage(Document):
	def validate(self):
		if not self.timestamp:
			self.timestamp = frappe.utils.now()
		
		if not self.created_time:
			self.created_time = frappe.utils.now()
		
		# Validate phone number format
		if self.phone_number and not self.phone_number.startswith('+'):
			frappe.throw("Phone number must include country code with + prefix")
	
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
		"""Send message via WhatsApp Business API"""
		# Implementation for sending message
		pass
	
	def mark_as_read(self):
		"""Mark message as read"""
		self.is_read = 1
		self.delivery_status = "read"
		self.save()
	
	def send_template_message(self, template_name, parameters=None):
		"""Send WhatsApp template message"""
		self.is_template_message = 1
		self.template_name = template_name
		self.message_type = "template"
		if parameters:
			self.message_content = str(parameters)
		self.save()