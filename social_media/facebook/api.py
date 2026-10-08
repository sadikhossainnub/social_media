"""
Facebook API Integration
Main webhook handler for Facebook events
"""

import frappe
import requests
import json
import hmac
import hashlib
from datetime import datetime


def verify_webhook_signature():
	"""
	Verify that the payload was sent by Facebook using SHA-256 or SHA-1.
	Gracefully logs signature mismatches without breaking webhook availability.
	"""
	settings = frappe.get_single("Facebook Settings")
	secret = settings.get_password("webhook_signature_secret") or settings.get_password("app_secret")
	if not secret:
		return

	signature_header = frappe.request.headers.get("X-Hub-Signature-256") or frappe.request.headers.get("X-Hub-Signature")
	if not signature_header:
		return

	try:
		payload = frappe.request.get_data()
		if signature_header.startswith("sha256="):
			expected_sig = signature_header.split("sha256=")[1]
			mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
			computed_sig = mac.hexdigest()
			if not hmac.compare_digest(computed_sig, expected_sig):
				frappe.log_error("X-Hub-Signature-256 mismatch", "Facebook Webhook Security")
		elif signature_header.startswith("sha1="):
			expected_sig = signature_header.split("sha1=")[1]
			mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha1)
			computed_sig = mac.hexdigest()
			if not hmac.compare_digest(computed_sig, expected_sig):
				frappe.log_error("X-Hub-Signature sha1 mismatch", "Facebook Webhook Security")
	except Exception as e:
		frappe.log_error(f"Error checking webhook signature: {str(e)}", "Facebook Webhook Security")


@frappe.whitelist(allow_guest=True)
def webhook():
	"""
	Main webhook endpoint for Facebook events.
	Routes to appropriate handlers based on event type.
	"""
	# Handle GET request for webhook verification from Meta
	if frappe.request.method == "GET":
		return handle_verification()

	if frappe.request.method != "POST":
		return "Invalid Request"

	try:
		verify_webhook_signature()
		
		data = frappe.request.get_json()
		if not data:
			return "Empty Body"

		object_type = data.get("object")

		if object_type in ("page", "instagram"):
			handle_page_event(data)
		elif object_type == "standby":
			handle_standby(data)

		return "OK"
	except Exception as e:
		frappe.log_error(
			title="Facebook Webhook Error",
			message=f"Error: {str(e)}"
		)
		return "OK"


def handle_verification():
	"""
	Handle webhook verification request from Facebook Meta.
	Returns raw challenge string with HTTP 200 status as expected by Meta.
	"""
	verify_token = frappe.request.args.get("hub.verify_token") or frappe.request.args.get("verify_token")
	mode = frappe.request.args.get("hub.mode") or frappe.request.args.get("mode")
	challenge = frappe.request.args.get("hub.challenge") or frappe.request.args.get("challenge")

	if mode == "subscribe" and challenge:
		settings = frappe.get_single("Facebook Settings")
		expected_token = getattr(settings, "messenger_verify_token", None) or getattr(settings, "webhook_verify_token", None)
		
		if not expected_token or verify_token == expected_token:
			frappe.local.response["type"] = "raw"
			frappe.local.response["response"] = str(challenge)
			frappe.local.response["http_status_code"] = 200
			return
		else:
			frappe.log_error(f"Verification token mismatch: received {verify_token}", "Facebook Webhook Verification")

	frappe.local.response["type"] = "raw"
	frappe.local.response["response"] = str(challenge or "Invalid Request")
	frappe.local.response["http_status_code"] = 200
	return


def handle_page_event(data):
	"""Handle page events from Facebook."""
	entry = data.get("entry", [])

	for entry_data in entry:
		messaging = entry_data.get("messaging", [])
		standby = entry_data.get("standby", [])
		changes = entry_data.get("changes", [])

		messaging_events = list(messaging) + list(standby)

		for change in changes:
			field = change.get("field")
			value = change.get("value", {})
			if field in ("messaging", "messages") and isinstance(value, dict):
				messaging_events.append(value)

		# Handle messaging events (Messenger)
		for event in messaging_events:
			sender_psid = event.get("sender", {}).get("id")
			recipient_psid = event.get("recipient", {}).get("id")

			if event.get("message"):
				handle_message(event, sender_psid, recipient_psid)
			elif event.get("postback"):
				handle_postback(event, sender_psid, recipient_psid)
			elif event.get("delivery"):
				handle_delivery(event, sender_psid, recipient_psid)
			elif event.get("read"):
				handle_read(event, sender_psid, recipient_psid)

		# Handle changes events (Lead Ads, Comments, etc.)
		for change in changes:
			field = change.get("field")
			value = change.get("value", {})

			if field == "lead_generation":
				handle_lead_generation(value)
			elif field == "feed" and value.get("comment_id"):
				handle_comment(value)
			elif field == "comments" and value.get("comment_id"):
				handle_comment_reply(value)


def handle_message(event, sender_psid, recipient_psid):
	"""Handle incoming and echo messages."""
	message = event.get("message", {})
	message_id = message.get("mid")
	text = message.get("text", "")
	attachments = message.get("attachments", [])
	is_echo = message.get("is_echo", False)

	if is_echo:
		customer_psid = recipient_psid
		sender_name = "Page Admin"
		direction = "Outgoing"
		page_id = sender_psid
	else:
		customer_psid = sender_psid
		sender_name = get_sender_name(sender_psid)
		direction = "Incoming"
		page_id = recipient_psid

	# Avoid duplicate messages if mid or message text already exists
	if message_id and frappe.db.exists("Facebook Messenger Chat", {"message": text, "sender_id": customer_psid, "direction": direction}):
		return

	customer = find_customer_by_psid(customer_psid)
	conversation_id = f"t_{customer_psid}"

	# Create chat record
	chat_doc = frappe.get_doc({
		"doctype": "Facebook Messenger Chat",
		"sender_id": customer_psid,
		"sender_name": sender_name,
		"page": page_id,
		"conversation_id": conversation_id,
		"message": text,
		"direction": direction,
		"customer": customer,
		"is_read": 1 if is_echo else 0,
		"attachments": frappe.as_json(attachments) if attachments else "[]"
	})
	chat_doc.insert(ignore_permissions=True)
	frappe.db.commit()

	# Publish to realtime
	try:
		from social_media.facebook.realtime import publish_new_message
		publish_new_message(chat_doc)
	except Exception:
		pass

	# Process AI background tasks for incoming messages
	if direction == "Incoming":
		try:
			frappe.enqueue(
				"social_media.facebook.ai_agent.process_incoming_messenger_message",
				queue="short",
				chat_name=chat_doc.name,
				enqueue_after_commit=True
			)
		except Exception:
			pass


def handle_postback(event, sender_psid, recipient_psid):
	"""Handle postback events (button clicks)."""
	postback = event.get("postback", {})
	payload = postback.get("payload")

	sender_name = get_sender_name(sender_psid)
	page_id = recipient_psid

	chat_doc = frappe.get_doc({
		"doctype": "Facebook Messenger Chat",
		"sender_id": sender_psid,
		"sender_name": sender_name,
		"page": page_id,
		"conversation_id": f"t_{sender_psid}",
		"message": f"POSTBACK: {payload or 'No payload'}",
		"direction": "Incoming"
	})
	chat_doc.insert(ignore_permissions=True)
	frappe.db.commit()
	
	# Publish to realtime
	try:
		from social_media.facebook.realtime import publish_new_message
		publish_new_message(chat_doc)
	except Exception:
		pass


def handle_delivery(event, sender_psid, recipient_psid):
	"""Handle message delivery confirmations from Meta."""
	delivery = event.get("delivery", {})
	mids = delivery.get("mids") or []
	watermark = delivery.get("watermark")
	conversation_id = f"t_{sender_psid}"

	try:
		frappe.db.sql("""
			UPDATE `tabFacebook Messenger Chat`
			SET is_delivered = 1
			WHERE conversation_id = %s AND direction = 'Outgoing'
		""", (conversation_id,))
		frappe.db.commit()

		from social_media.facebook.realtime import publish_delivery_receipt
		publish_delivery_receipt(conversation_id, watermark)
	except Exception as e:
		frappe.log_error(f"Error handling delivery receipt: {str(e)}", "Facebook Webhook")


def handle_read(event, sender_psid, recipient_psid):
	"""Handle message read confirmations from Meta."""
	read = event.get("read", {})
	watermark = read.get("watermark")
	conversation_id = f"t_{sender_psid}"

	try:
		frappe.db.sql("""
			UPDATE `tabFacebook Messenger Chat`
			SET is_read = 1, is_delivered = 1
			WHERE conversation_id = %s AND direction = 'Outgoing'
		""", (conversation_id,))
		frappe.db.commit()

		from social_media.facebook.realtime import publish_read_receipt
		publish_read_receipt(conversation_id, watermark)
	except Exception as e:
		frappe.log_error(f"Error handling read receipt: {str(e)}", "Facebook Webhook")


def handle_standby(data):
	"""Handle standby events (when user is not active)."""
	entry = data.get("entry", [])

	for entry_data in entry:
		messaging = entry_data.get("messaging", [])

		for event in messaging:
			sender_psid = event.get("sender", {}).get("id")
			recipient_psid = event.get("recipient", {}).get("id")

			if event.get("message"):
				handle_message(event, sender_psid, recipient_psid)
			elif event.get("postback"):
				handle_postback(event, sender_psid, recipient_psid)


def handle_lead_generation(value):
	"""Handle lead generation events from Facebook Lead Ads."""
	leadgen_id = value.get("leadgen_id")
	form_id = value.get("form_id")

	if leadgen_id:
		# Fetch full lead details
		lead_details = get_lead_details(leadgen_id)

		if lead_details:
			# Create Facebook Lead record
			from social_media.facebook.leads import create_facebook_lead
			create_facebook_lead(lead_details)

			# Auto-create ERPNext Lead if enabled
			settings = frappe.get_single("Facebook Settings")
			if settings.enable_lead_ads:
				from social_media.facebook.leads import create_erpnext_lead
				create_erpnext_lead(lead_details)

			frappe.db.commit()


def handle_comment(value):
	"""Handle new comments on posts."""
	comment_id = value.get("comment_id")
	message = value.get("message", "")
	post_id = value.get("post_id")
	created_time_str = value.get("created_time")
	
	# Map created_time to datetime
	created_time = datetime.now()
	if created_time_str:
		try:
			created_time = datetime.fromtimestamp(int(created_time_str))
		except ValueError:
			pass

	# Get page info from settings
	settings = frappe.get_single("Facebook Settings")

	comment_doc = frappe.get_doc({
		"doctype": "Facebook Comment",
		"comment_id": comment_id,
		"page": settings.page_id,
		"post": post_id,  # Link to Post
		"post_id": post_id,
		"commenter_name": value.get("from", {}).get("name", "User"),
		"commenter_psid": value.get("from", {}).get("id"),
		"message": message,
		"created_time": created_time
	})
	comment_doc.insert(ignore_permissions=True)
	frappe.db.commit()

	# Publish to realtime
	try:
		from social_media.facebook.realtime import publish_new_comment
		publish_new_comment(comment_doc)
	except Exception:
		pass

	# AI agent process comment asynchronously
	try:
		from social_media.facebook.ai_agent import process_comment_with_ai
		process_comment_with_ai(comment_doc)
	except Exception as e:
		frappe.log_error(f"Error calling AI comment processing: {str(e)}", "Facebook Webhook AI")


def handle_comment_reply(value):
	"""Handle comment replies."""
	comment_id = value.get("comment_id")
	message = value.get("message", "")
	created_time_str = value.get("created_time")
	
	# Map created_time to datetime
	created_time = datetime.now()
	if created_time_str:
		try:
			created_time = datetime.fromtimestamp(int(created_time_str))
		except ValueError:
			pass

	settings = frappe.get_single("Facebook Settings")

	comment_doc = frappe.get_doc({
		"doctype": "Facebook Comment",
		"comment_id": comment_id,
		"page": settings.page_id,
		"post": value.get("post_id"),
		"post_id": value.get("post_id"),
		"commenter_name": value.get("from", {}).get("name", "User"),
		"commenter_psid": value.get("from", {}).get("id"),
		"message": message,
		"created_time": created_time
	})
	comment_doc.insert(ignore_permissions=True)
	frappe.db.commit()
	
	# Publish to realtime
	try:
		from social_media.facebook.realtime import publish_new_comment
		publish_new_comment(comment_doc)
	except Exception:
		pass


def get_sender_name(sender_psid):
	"""Get sender's name from cache/DB non-blockingly, or queue background lookup."""
	if not sender_psid:
		return "Facebook User"

	cache_key = f"fb_sender_name_{sender_psid}"
	try:
		cached = frappe.cache().get_value(cache_key)
		if cached:
			return cached
	except Exception:
		pass

	# Check local Messenger Chat records
	existing_name = frappe.db.get_value(
		"Facebook Messenger Chat",
		{"sender_id": sender_psid, "sender_name": ["not in", ["Facebook User", "Unknown", None]]},
		"sender_name"
	)
	if existing_name:
		try:
			frappe.cache().set_value(cache_key, existing_name, expires_in_sec=86400)
		except Exception:
			pass
		return existing_name

	# Check Customer record
	customer_name = frappe.db.get_value("Customer", {"facebook_psid": sender_psid}, "customer_name")
	if customer_name:
		try:
			frappe.cache().set_value(cache_key, customer_name, expires_in_sec=86400)
		except Exception:
			pass
		return customer_name

	# Enqueue background API fetch so current webhook execution completes in < 5ms
	try:
		frappe.enqueue(
			"social_media.facebook.api.async_update_sender_name",
			queue="short",
			sender_psid=sender_psid,
			enqueue_after_commit=True
		)
	except Exception:
		pass

	return "Facebook User"


def async_update_sender_name(sender_psid):
	"""Fetch sender name from Graph API in background and update DB & Redis cache."""
	settings = frappe.get_single("Facebook Settings")
	if not settings.is_connected:
		return

	import requests
	params = {
		"access_token": settings.get_password("page_access_token"),
		"fields": "first_name,last_name,name"
	}

	from social_media.facebook.utils import get_graph_api_version
	url = f"https://graph.facebook.com/{get_graph_api_version()}/{sender_psid}"

	try:
		response = requests.get(url, params=params, timeout=10)
		if response.status_code == 200:
			res = response.json()
			name = res.get("name")
			if name:
				cache_key = f"fb_sender_name_{sender_psid}"
				frappe.cache().set_value(cache_key, name, expires_in_sec=86400)
				frappe.db.sql("""
					UPDATE `tabFacebook Messenger Chat`
					SET sender_name = %s
					WHERE sender_id = %s AND (sender_name IS NULL OR sender_name IN ('Facebook User', 'Unknown'))
				""", (name, sender_psid))
				frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error in async_update_sender_name: {str(e)}", "Facebook Webhook")


def find_customer_by_psid(psid):
	"""Find customer by PSID."""
	customer = frappe.db.get_value(
		"Customer",
		{"facebook_psid": psid},
		"name"
	)

	return customer


def get_lead_details(lead_id):
	"""
	Fetch full lead details from Facebook.
	"""
	settings = frappe.get_single("Facebook Settings")

	if not settings.is_connected:
		return None

	import requests
	params = {
		"access_token": settings.get_password("page_access_token"),
		"fields": "id,form_id,created_time,field_data,ad_id,ad_name,campaign_id,campaign_name"
	}

	from social_media.facebook.utils import get_graph_api_version
	url = f"https://graph.facebook.com/{get_graph_api_version()}/{lead_id}"

	try:
		response = requests.get(url, params=params, timeout=15)
		result = response.json()

		if response.status_code == 200:
			# Parse field_data
			field_data = result.get("field_data", [])
			parsed_data = parse_field_data(field_data)
			result.update(parsed_data)
			return result

	except Exception:
		pass

	return None


def parse_field_data(field_data):
	"""Parse Facebook lead field_data into a flat dictionary."""
	parsed = {}

	for field in field_data:
		name = field.get("name", "")
		values = field.get("values", [])

		if values:
			parsed[name] = values[0] if len(values) == 1 else values

	return parsed
