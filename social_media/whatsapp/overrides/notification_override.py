import frappe
from frappe.email.doctype.notification.notification import Notification
from social_media.whatsapp.utils import send_text, format_number

class WhatsappNotificationOverride(Notification):
	def send_notification_by_channel(self, doc, context):
		"""Extend standard notification to handle WhatsApp channel."""
		if self.channel == "WhatsApp":
			try:
				self.send_whatsapp(doc, context)
			except Exception:
				self.log_error("Failed to send WhatsApp Notification")
		else:
			super().send_notification_by_channel(doc, context)

	def send_whatsapp(self, doc, context):
		"""WhatsApp sending logic for standard Notification."""
		if not self.whatsapp_instance:
			frappe.throw("Please select a WhatsApp Instance in the Notification settings.", title="Missing Instance")

		message = frappe.render_template(self.message, context)
		recipients = self.get_receiver_list(doc, context)

		if not recipients:
			return

		# Handle attachments
		attachments = self.get_attachment(doc)
		media_url = None
		if attachments:
			# If it's a file from Frappe, it might be a relative path or a public URL
			# For simplicity, we'll try to get the first one
			first = attachments[0]
			if first.get("file_url"):
				media_url = first["file_url"]
				if not media_url.startswith("http"):
					# Attempt to build full URL if possible
					base_url = frappe.utils.get_url()
					media_url = base_url + media_url

		for recipient in recipients:
			if not recipient:
				continue
				
			if media_url:
				# Send as media if attachment exists
				frappe.enqueue(
					"social_media.whatsapp.utils.send_media",
					instance_name=self.whatsapp_instance,
					number=format_number(recipient),
					media_url=media_url,
					caption=message,
					now=frappe.flags.in_test
				)
			else:
				# Send as text
				frappe.enqueue(
					"social_media.whatsapp.utils.send_text",
					instance_name=self.whatsapp_instance,
					number=format_number(recipient),
					text=message,
					now=frappe.flags.in_test
				)

def create_notification_customizations():
	"""Create property setters to add WhatsApp support to core Notification DocType."""
	
	# 1. Add 'WhatsApp' to channel options
	if not frappe.db.exists("Property Setter", "Notification-channel-options"):
		frappe.get_doc({
			"doctype": "Property Setter",
			"doctype_or_field": "DocField",
			"doc_type": "Notification",
			"field_name": "channel",
			"property": "options",
			"property_type": "Select",
			"value": "Email\nSlack\nSystem Notification\nSMS\nWhatsApp"
		}).insert(ignore_permissions=True)

	# 2. Add 'whatsapp_instance' field via Custom Field instead of Property Setter for complexity
	if not frappe.db.exists("Custom Field", "Notification-whatsapp_instance"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Notification",
			"fieldname": "whatsapp_instance",
			"fieldtype": "Link",
			"label": "WhatsApp Instance",
			"insert_after": "channel",
			"options": "Whatsapp Instance",
			"mandatory_depends_on": "eval:doc.channel=='WhatsApp'",
			"depends_on": "eval:doc.channel=='WhatsApp'"
		}).insert(ignore_permissions=True)

	frappe.db.commit()
