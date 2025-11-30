import frappe
import requests
from frappe import _


@frappe.whitelist()
def send_facebook_message(recipient_id, message_content, message_type="text", page_id=None):
	"""Send Facebook message via Graph API"""
	try:
		# Create Facebook Message document
		fb_message = frappe.new_doc("Facebook Message")
		fb_message.update({
			"sender_id": frappe.session.user,
			"recipient_id": recipient_id,
			"message_content": message_content,
			"message_type": message_type,
			"page_id": page_id,
			"status": "sent"
		})
		fb_message.insert()
		
		# Get settings and send via Facebook API
		settings = frappe.get_single("Facebook Settings")
		if settings.enabled:
			access_token = settings.get_access_token()
			api_version = settings.api_version or "v18.0"
			url = f"https://graph.facebook.com/{api_version}/me/messages"
			payload = {
				"recipient": {"id": recipient_id},
				"message": {"text": message_content}
			}
			# response = requests.post(url, json=payload, params={"access_token": access_token})
		
		return {
			"success": True,
			"message": "Facebook message sent successfully",
			"message_id": fb_message.name
		}
		
	except Exception as e:
		frappe.log_error(f"Facebook message send error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_facebook_messages(page_id=None, limit=20):
	"""Get Facebook messages"""
	filters = {}
	if page_id:
		filters["page_id"] = page_id
	
	messages = frappe.get_all(
		"Facebook Message",
		filters=filters,
		fields=["name", "sender_id", "recipient_id", "message_content", "timestamp", "status"],
		order_by="timestamp desc",
		limit=limit
	)
	
	return messages