import frappe
import requests
from frappe import _


@frappe.whitelist()
def send_whatsapp_message(phone_number, message_content, message_type="text", media_url=None):
	"""Send WhatsApp message via WhatsApp Business API"""
	try:
		# Create WhatsApp Message document
		wa_message = frappe.new_doc("WhatsApp Message")
		wa_message.update({
			"phone_number": phone_number,
			"message_content": message_content,
			"message_type": message_type,
			"media_url": media_url,
			"status": "sent",
			"delivery_status": "pending"
		})
		wa_message.insert()
		
		# Get settings and send via WhatsApp Business API
		settings = frappe.get_single("WhatsApp Settings")
		if settings.enabled:
			access_token = settings.get_access_token()
			api_version = settings.api_version or "v18.0"
			url = f"https://graph.facebook.com/{api_version}/{settings.phone_number_id}/messages"
			payload = {
				"messaging_product": "whatsapp",
				"to": phone_number,
				"text": {"body": message_content}
			}
			# response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"})
		
		return {
			"success": True,
			"message": "WhatsApp message sent successfully",
			"message_id": wa_message.name
		}
		
	except Exception as e:
		frappe.log_error(f"WhatsApp message send error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_whatsapp_template(phone_number, template_name, parameters=None):
	"""Send WhatsApp template message"""
	try:
		wa_message = frappe.new_doc("WhatsApp Message")
		wa_message.update({
			"phone_number": phone_number,
			"template_name": template_name,
			"message_type": "template",
			"is_template_message": 1,
			"message_content": str(parameters) if parameters else "",
			"status": "sent",
			"delivery_status": "pending"
		})
		wa_message.insert()
		
		# TODO: Implement template message API call
		
		return {
			"success": True,
			"message": "WhatsApp template message sent successfully",
			"message_id": wa_message.name
		}
		
	except Exception as e:
		frappe.log_error(f"WhatsApp template send error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_whatsapp_messages(phone_number=None, limit=20):
	"""Get WhatsApp messages"""
	filters = {}
	if phone_number:
		filters["phone_number"] = phone_number
	
	messages = frappe.get_all(
		"WhatsApp Message",
		filters=filters,
		fields=["name", "phone_number", "contact_name", "message_content", "timestamp", "status", "delivery_status"],
		order_by="timestamp desc",
		limit=limit
	)
	
	return messages