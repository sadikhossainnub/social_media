import frappe
from frappe import _
from social_media.facebook.api import send_facebook_message
from social_media.instragram.api import send_instagram_message
from social_media.whatsapp.api import send_whatsapp_message


@frappe.whitelist()
def send_message(platform, recipient, message_content, message_type="text", **kwargs):
	"""Unified API to send messages across all platforms"""
	
	platform = platform.lower()
	
	try:
		if platform == "facebook":
			return send_facebook_message(
				recipient_id=recipient,
				message_content=message_content,
				message_type=message_type,
				page_id=kwargs.get("page_id")
			)
		
		elif platform == "instagram":
			return send_instagram_message(
				recipient_id=recipient,
				message_content=message_content,
				message_type=message_type,
				media_url=kwargs.get("media_url")
			)
		
		elif platform == "whatsapp":
			return send_whatsapp_message(
				phone_number=recipient,
				message_content=message_content,
				message_type=message_type,
				media_url=kwargs.get("media_url")
			)
		
		else:
			return {"success": False, "error": f"Unsupported platform: {platform}"}
	
	except Exception as e:
		frappe.log_error(f"Unified message send error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_all_messages(limit=50):
	"""Get messages from all platforms"""
	
	messages = []
	
	# Facebook messages
	fb_messages = frappe.get_all(
		"Facebook Message",
		fields=["name", "sender_id", "recipient_id", "message_content", "timestamp", "status", "'Facebook' as platform"],
		order_by="timestamp desc",
		limit=limit//3
	)
	messages.extend(fb_messages)
	
	# Instagram messages
	ig_messages = frappe.get_all(
		"Instagram Message",
		fields=["name", "sender_id", "recipient_id", "message_content", "timestamp", "status", "'Instagram' as platform"],
		order_by="timestamp desc",
		limit=limit//3
	)
	messages.extend(ig_messages)
	
	# WhatsApp messages
	wa_messages = frappe.get_all(
		"WhatsApp Message",
		fields=["name", "phone_number as recipient_id", "message_content", "timestamp", "status", "'WhatsApp' as platform"],
		order_by="timestamp desc",
		limit=limit//3
	)
	messages.extend(wa_messages)
	
	# Sort by timestamp
	messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
	
	return messages[:limit]


@frappe.whitelist()
def create_send_message(platform, recipient, message_content, message_type="text", **kwargs):
	"""Create Send Message document"""
	
	send_msg = frappe.new_doc("Send Message")
	send_msg.update({
		"platform": platform.title(),
		"recipient": recipient,
		"message_content": message_content,
		"message_type": message_type,
		"media_url": kwargs.get("media_url"),
		"template_name": kwargs.get("template_name"),
		"send_immediately": kwargs.get("send_immediately", 1)
	})
	send_msg.insert()
	
	if send_msg.send_immediately:
		send_msg.send_message()
	
	return {
		"success": True,
		"message": "Send Message created successfully",
		"name": send_msg.name,
		"status": send_msg.status
	}


@frappe.whitelist()
def bulk_send_messages(platform, recipients, message_content, message_type="text"):
	"""Send messages to multiple recipients"""
	
	results = []
	recipient_list = recipients.split(",") if isinstance(recipients, str) else recipients
	
	for recipient in recipient_list:
		recipient = recipient.strip()
		if recipient:
			result = create_send_message(
				platform=platform,
				recipient=recipient,
				message_content=message_content,
				message_type=message_type
			)
			results.append({"recipient": recipient, "result": result})
	
	return {
		"success": True,
		"message": f"Bulk messages created for {len(results)} recipients",
		"results": results
	}