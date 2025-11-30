import frappe
from frappe.model.document import Document
from frappe import _


class SendMessage(Document):
	def validate(self):
		if self.platform == "WhatsApp" and not self.recipient.startswith('+'):
			frappe.throw(_("WhatsApp phone number must include country code with + prefix"))
	
	def on_submit(self):
		if self.send_immediately:
			self.send_message()
	
	def send_message(self):
		"""Send message based on platform"""
		try:
			self.status = "Sending"
			self.save()
			
			result = None
			
			if self.platform == "Facebook":
				result = self._send_facebook_message()
			elif self.platform == "Instagram":
				result = self._send_instagram_message()
			elif self.platform == "WhatsApp":
				result = self._send_whatsapp_message()
			
			if result and result.get("success"):
				self.status = "Sent"
				self.sent_at = frappe.utils.now()
				self.response_message = result.get("message", "")
				self.created_message_id = result.get("message_id", "")
			else:
				self.status = "Failed"
				self.error_log = result.get("error", "Unknown error") if result else "No response"
				self.retry_count += 1
			
			self.save()
			
		except Exception as e:
			self.status = "Failed"
			self.error_log = str(e)
			self.retry_count += 1
			self.save()
			frappe.log_error(f"Send Message error: {str(e)}")
	
	def _send_facebook_message(self):
		"""Send Facebook message"""
		from social_media.facebook.api import send_facebook_message
		
		return send_facebook_message(
			recipient_id=self.recipient,
			message_content=self.message_content,
			message_type=self.message_type
		)
	
	def _send_instagram_message(self):
		"""Send Instagram message"""
		from social_media.instragram.api import send_instagram_message
		
		return send_instagram_message(
			recipient_id=self.recipient,
			message_content=self.message_content,
			message_type=self.message_type,
			media_url=self.media_url
		)
	
	def _send_whatsapp_message(self):
		"""Send WhatsApp message"""
		from social_media.whatsapp.api import send_whatsapp_message, send_whatsapp_template
		
		if self.message_type == "template":
			return send_whatsapp_template(
				phone_number=self.recipient,
				template_name=self.template_name,
				parameters=self.message_content
			)
		else:
			return send_whatsapp_message(
				phone_number=self.recipient,
				message_content=self.message_content,
				message_type=self.message_type,
				media_url=self.media_url
			)
	
	@frappe.whitelist()
	def retry_send(self):
		"""Retry sending failed message"""
		if self.status == "Failed":
			self.send_message()
			return {"success": True, "message": "Message retry initiated"}
		else:
			return {"success": False, "message": "Can only retry failed messages"}