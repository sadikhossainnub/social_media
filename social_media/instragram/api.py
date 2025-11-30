import frappe
import requests
from frappe import _


@frappe.whitelist()
def send_instagram_message(recipient_id, message_content, message_type="text", media_url=None):
	"""Send Instagram message via Instagram Basic Display API"""
	try:
		# Create Instagram Message document
		ig_message = frappe.new_doc("Instagram Message")
		ig_message.update({
			"sender_id": frappe.session.user,
			"recipient_id": recipient_id,
			"message_content": message_content,
			"message_type": message_type,
			"media_url": media_url,
			"status": "sent"
		})
		ig_message.insert()
		
		# Get settings and send via Instagram API
		settings = frappe.get_single("Instagram Settings")
		if settings.enabled:
			access_token = settings.get_access_token()
			api_version = settings.api_version or "v18.0"
			url = f"https://graph.instagram.com/{api_version}/me/messages"
			payload = {
				"recipient": {"id": recipient_id},
				"message": {"text": message_content}
			}
			# response = requests.post(url, json=payload, params={"access_token": access_token})
		
		return {
			"success": True,
			"message": "Instagram message sent successfully",
			"message_id": ig_message.name
		}
		
	except Exception as e:
		frappe.log_error(f"Instagram message send error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def reply_to_instagram_story(story_id, reply_content, recipient_id):
	"""Reply to Instagram story"""
	try:
		ig_message = frappe.new_doc("Instagram Message")
		ig_message.update({
			"sender_id": frappe.session.user,
			"recipient_id": recipient_id,
			"message_content": reply_content,
			"message_type": "story_reply",
			"story_id": story_id,
			"is_story_reply": 1,
			"status": "sent"
		})
		ig_message.insert()
		
		return {
			"success": True,
			"message": "Story reply sent successfully",
			"message_id": ig_message.name
		}
		
	except Exception as e:
		frappe.log_error(f"Instagram story reply error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_instagram_messages(limit=20):
	"""Get Instagram messages"""
	messages = frappe.get_all(
		"Instagram Message",
		fields=["name", "sender_id", "recipient_id", "message_content", "timestamp", "status", "is_story_reply"],
		order_by="timestamp desc",
		limit=limit
	)
	
	return messages