import frappe
import json


def extract_message_content(message_content):
	"""
	Extract message type, text body, and media info from Evolution API message.
	Returns: (message_type, text_body, media_info)
	"""
	text_body = ""
	media_info = {}
	message_type = "Text"

	if "conversation" in message_content:
		text_body = message_content["conversation"]
		message_type = "Text"

	elif "extendedTextMessage" in message_content:
		text_body = message_content["extendedTextMessage"].get("text", "")
		message_type = "Text"

	elif "imageMessage" in message_content:
		img_msg = message_content["imageMessage"]
		text_body = "[Image] " + img_msg.get("caption", "")
		media_info = {
			"type": "image",
			"url": img_msg.get("url", ""),
			"caption": img_msg.get("caption", "")
		}
		message_type = "Media"

	elif "videoMessage" in message_content:
		vid_msg = message_content["videoMessage"]
		text_body = "[Video] " + vid_msg.get("caption", "")
		media_info = {
			"type": "video",
			"url": vid_msg.get("url", ""),
			"caption": vid_msg.get("caption", "")
		}
		message_type = "Media"

	elif "documentMessage" in message_content:
		doc_msg = message_content["documentMessage"]
		text_body = "[Document] " + doc_msg.get("fileName", "")
		media_info = {
			"type": "document",
			"url": doc_msg.get("url", ""),
			"caption": doc_msg.get("fileName", "")
		}
		message_type = "Media"

	elif "audioMessage" in message_content:
		audio_msg = message_content["audioMessage"]
		text_body = "[Audio Message]"
		media_info = {
			"url": audio_msg.get("url", "")
		}
		message_type = "Audio"

	elif "stickerMessage" in message_content:
		text_body = "[Sticker]"
		message_type = "Text"

	elif "locationMessage" in message_content:
		loc = message_content["locationMessage"]
		latitude = loc.get("degreesLatitude", 0)
		longitude = loc.get("degreesLongitude", 0)
		text_body = f"[Location] {latitude}, {longitude}"
		media_info = {
			"latitude": latitude,
			"longitude": longitude,
			"name": loc.get("name", "Location"),
			"address": loc.get("address", "")
		}
		message_type = "Location"

	elif "contactMessage" in message_content:
		contact_msg = message_content["contactMessage"]
		text_body = "[Contact] " + contact_msg.get("displayName", "Unknown")
		message_type = "Text"

	else:
		text_body = "[Unsupported message type]"
		message_type = "Text"

	return message_type, text_body, media_info


@frappe.whitelist(allow_guest=True)
def webhook():
	"""
	Webhook endpoint for Evolution API v2.3.
	Handles: MESSAGES_UPSERT, CONNECTION_UPDATE, QRCODE_UPDATED, SEND_MESSAGE
	"""
	if frappe.request.method != "POST":
		return

	try:
		data = frappe.request.get_json()
		if not data:
			return

		event = data.get("event")
		instance_name = data.get("instance")

		if event == "messages.upsert":
			handle_message_upsert(data)
		elif event == "connection.update":
			handle_connection_update(data)
		elif event == "qrcode.updated":
			handle_qrcode_updated(data)
		elif event == "send.message":
			handle_send_message(data)

		return "OK"
	except Exception as e:
		frappe.log_error(
			title="WhatsApp Webhook Error",
			message=f"Event: {data.get('event') if data else 'N/A'}\n{str(e)}"
		)
		return "Error"


def handle_message_upsert(data):
	"""Handle incoming messages (MESSAGES_UPSERT) and save to Whatsapp Chat."""
	payload = data.get("data", {})
	key = payload.get("key", {})
	message_content = payload.get("message", {})

	if key.get("fromMe"):
		return  # Skip own messages — handled by SEND_MESSAGE event

	remote_jid = key.get("remoteJid", "")
	phone_number = remote_jid.split("@")[0] if remote_jid else "Unknown"

	# Get instance
	instance_name = data.get("instance")
	instance_doc = frappe.db.get_value(
		"Whatsapp Instance", {"instance_name": instance_name}, "name"
	)

	if not instance_doc:
		frappe.log_error(
			title="WhatsApp Instance Not Found",
			message=f"Instance name: {instance_name}"
		)
		return

	# Extract message type and content
	message_type, text_body, media_info = extract_message_content(message_content)

	# Find or create Whatsapp Chat for this number
	chat_name = frappe.db.get_value(
		"Whatsapp Chat",
		{"instance": instance_doc, "recipient_number": phone_number},
		"name"
	)

	if chat_name:
		chat_doc = frappe.get_doc("Whatsapp Chat", chat_name)
	else:
		# Create new chat
		chat_doc = frappe.get_doc({
			"doctype": "Whatsapp Chat",
			"instance": instance_doc,
			"recipient_number": phone_number,
			"message_type": message_type,
			"message": text_body,
			"status": "Draft"
		})

	# Update chat with incoming message
	chat_doc.message_type = message_type
	
	if message_type == "Text":
		chat_doc.message = text_body
	elif message_type == "Media":
		if media_info:
			chat_doc.media_url = media_info.get("url")
			chat_doc.media_type = media_info.get("type")
			chat_doc.caption = media_info.get("caption", "")
			chat_doc.message = f"[{media_info.get('type')}] {media_info.get('caption', '')}"
	elif message_type == "Location":
		if media_info:
			chat_doc.latitude = media_info.get("latitude")
			chat_doc.longitude = media_info.get("longitude")
			chat_doc.location_name = media_info.get("name")
			chat_doc.location_address = media_info.get("address")
			chat_doc.message = f"[Location] {media_info.get('name', '')} ({media_info.get('latitude')}, {media_info.get('longitude')})"
	elif message_type == "Audio":
		if media_info:
			chat_doc.media_url = media_info.get("url")
			chat_doc.message = "[Audio Message]"

	chat_doc.status = "Delivered"
	
	if chat_name:
		chat_doc.save(ignore_permissions=True)
	else:
		chat_doc.insert(ignore_permissions=True)
	
	frappe.db.commit()

	# Also log to Message Log for detailed tracking
	log_doc = frappe.get_doc({
		"doctype": "Whatsapp Message Log",
		"instance": instance_doc,
		"direction": "Inbound",
		"status": "Received",
		"recipient_number": phone_number,
		"message_id": key.get("id"),
		"message_body": text_body
	})
	log_doc.insert(ignore_permissions=True)
	frappe.db.commit()


def handle_connection_update(data):
	"""Handle CONNECTION_UPDATE — auto-update instance status."""
	instance_name = data.get("instance")
	payload = data.get("data", {})

	state = payload.get("state") or payload.get("status")

	if not instance_name or not state:
		return

	if frappe.db.exists("Whatsapp Instance", instance_name):
		status = "Disconnected"
		if state == "open":
			status = "Connected"
		elif state == "connecting":
			status = "Connecting"

		update_data = {"status": status}
		if status == "Connected":
			update_data["qr_code_base64"] = ""

		frappe.db.set_value("Whatsapp Instance", instance_name, update_data)
		frappe.db.commit()


def handle_qrcode_updated(data):
	"""Handle QRCODE_UPDATED — auto-update QR code on the instance."""
	instance_name = data.get("instance")
	payload = data.get("data", {})

	qrcode_base64 = payload.get("qrcode", {}).get("base64") or payload.get("base64")

	if not instance_name or not qrcode_base64:
		return

	if frappe.db.exists("Whatsapp Instance", instance_name):
		frappe.db.set_value("Whatsapp Instance", instance_name, {
			"qr_code_base64": qrcode_base64,
			"status": "Connecting"
		})
		frappe.db.commit()


def handle_send_message(data):
	"""Handle SEND_MESSAGE — log outbound messages to Whatsapp Chat and Message Log."""
	instance_name = data.get("instance")
	payload = data.get("data", {})
	key = payload.get("key", {})
	message_content = payload.get("message", {})

	remote_jid = key.get("remoteJid", "")
	phone_number = remote_jid.split("@")[0] if remote_jid else "Unknown"

	instance_doc = frappe.db.get_value(
		"Whatsapp Instance", {"instance_name": instance_name}, "name"
	)

	if not instance_doc:
		frappe.log_error(
			title="WhatsApp Instance Not Found",
			message=f"Instance name: {instance_name}"
		)
		return

	# Extract message content
	message_type, text_body, media_info = extract_message_content(message_content)

	# Find or create Whatsapp Chat for this number
	chat_name = frappe.db.get_value(
		"Whatsapp Chat",
		{"instance": instance_doc, "recipient_number": phone_number},
		"name"
	)

	if chat_name:
		chat_doc = frappe.get_doc("Whatsapp Chat", chat_name)
	else:
		# Create new chat
		chat_doc = frappe.get_doc({
			"doctype": "Whatsapp Chat",
			"instance": instance_doc,
			"recipient_number": phone_number,
			"message_type": message_type,
			"message": text_body,
			"status": "Draft"
		})

	# Update chat with outgoing message
	chat_doc.message_type = message_type

	if message_type == "Text":
		chat_doc.message = text_body
	elif message_type == "Media":
		if media_info:
			chat_doc.media_url = media_info.get("url")
			chat_doc.media_type = media_info.get("type")
			chat_doc.caption = media_info.get("caption", "")
			chat_doc.message = f"[{media_info.get('type')}] {media_info.get('caption', '')}"
	elif message_type == "Location":
		if media_info:
			chat_doc.latitude = media_info.get("latitude")
			chat_doc.longitude = media_info.get("longitude")
			chat_doc.location_name = media_info.get("name")
			chat_doc.location_address = media_info.get("address")
			chat_doc.message = f"[Location] {media_info.get('name', '')} ({media_info.get('latitude')}, {media_info.get('longitude')})"
	elif message_type == "Audio":
		if media_info:
			chat_doc.media_url = media_info.get("url")
			chat_doc.message = "[Audio Message]"

	chat_doc.status = "Sent"

	if chat_name:
		chat_doc.save(ignore_permissions=True)
	else:
		chat_doc.insert(ignore_permissions=True)

	frappe.db.commit()

	# Also log to Message Log for detailed tracking
	log_doc = frappe.get_doc({
		"doctype": "Whatsapp Message Log",
		"instance": instance_doc,
		"direction": "Outbound",
		"status": "Sent",
		"recipient_number": phone_number,
		"message_id": key.get("id"),
		"message_body": text_body
	})
	log_doc.insert(ignore_permissions=True)
	frappe.db.commit()
