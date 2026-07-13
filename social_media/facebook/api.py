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
	Verify that the payload was sent by Facebook by hashing it with
	webhook_signature_secret or app_secret using SHA-256.
	"""
	settings = frappe.get_single("Facebook Settings")
	# Use webhook_signature_secret first, fallback to app_secret
	secret = settings.get_password("webhook_signature_secret") or settings.get_password("app_secret")
	if not secret:
		return # Skip if no secret is configured yet

	signature_header = frappe.request.headers.get("X-Hub-Signature-256")
	if not signature_header or not signature_header.startswith("sha256="):
		frappe.log_error("Missing or invalid X-Hub-Signature-256 header", "Facebook Webhook Security")
		frappe.throw("Missing or invalid X-Hub-Signature-256 header", frappe.PermissionError)

	expected_signature = signature_header.split("sha256=")[1]
	
	# Compute signature using raw payload
	payload = frappe.request.get_data()
	mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
	computed_signature = mac.hexdigest()
	
	if not hmac.compare_digest(computed_signature, expected_signature):
		frappe.log_error("X-Hub-Signature-256 signature verification failed", "Facebook Webhook Security")
		frappe.throw("Signature verification failed", frappe.PermissionError)


@frappe.whitelist(allow_guest=True)
def webhook():
	"""
	Main webhook endpoint for Facebook events.
	Routes to appropriate handlers based on event type.
	"""
	# Handle GET request for webhook verification
	if frappe.request.method == "GET":
		return handle_verification()

	if frappe.request.method != "POST":
		return "Invalid Request"

	try:
		# Verify signature
		verify_webhook_signature()
		
		data = frappe.request.get_json()
		if not data:
			return "Empty Body"

		object_type = data.get("object")

		if object_type == "page":
			handle_page_event(data)
		elif object_type == "standby":
			handle_standby(data)

		return "OK"
	except frappe.PermissionError:
		# Specifically catch and handle permission errors for signature verification
		frappe.local.response["http_status_code"] = 403
		return "Forbidden"
	except Exception as e:
		frappe.log_error(
			title="Facebook Webhook Error",
			message=f"Event: {data.get('object') if data else 'N/A'}\n{str(e)}"
		)
		return "Error"


def handle_verification():
	"""Handle webhook verification request from Facebook."""
	verify_token = frappe.request.args.get("hub.verify_token")
	mode = frappe.request.args.get("hub.mode")
	challenge = frappe.request.args.get("hub.challenge")

	if mode == "subscribe" and challenge:
		settings = frappe.get_single("Facebook Settings")
		if verify_token == settings.messenger_verify_token:
			frappe.response["type"] = "binary"
			frappe.response["filecontent"] = str(challenge).encode('utf-8')
			frappe.response["filename"] = "challenge.txt"
			return
		else:
			frappe.log_error("Verification token mismatch", "Facebook Webhook")
			frappe.throw("Token mismatch", frappe.PermissionError)

	frappe.response["type"] = "binary"
	frappe.response["filecontent"] = b"Invalid request"
	frappe.response["filename"] = "error.txt"
	return


def handle_page_event(data):
	"""Handle page events from Facebook."""
	entry = data.get("entry", [])

	for entry_data in entry:
		messaging = entry_data.get("messaging", [])
		changes = entry_data.get("changes", [])

		# Handle messaging events (Messenger)
		for event in messaging:
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
	"""Handle incoming messages."""
	message = event.get("message", {})
	message_id = message.get("mid")
	text = message.get("text", "")
	attachments = message.get("attachments", [])

	# Get sender name
	sender_name = get_sender_name(sender_psid)

	# Find customer by PSID
	customer = find_customer_by_psid(sender_psid)
	
	# Determine page name/id from recipient_psid
	page_id = recipient_psid

	# Create chat record
	chat_doc = frappe.get_doc({
		"doctype": "Facebook Messenger Chat",
		"sender_id": sender_psid,
		"sender_name": sender_name,
		"page": page_id,
		"conversation_id": f"t_{sender_psid}",
		"message": text,
		"direction": "Incoming",
		"customer": customer,
		"is_read": 0,
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
	"""Handle message delivery confirmations."""
	delivery = event.get("delivery", {})
	mids = delivery.get("mids")
	watermark = delivery.get("watermark")


def handle_read(event, sender_psid, recipient_psid):
	"""Handle message read confirmations."""
	read = event.get("read", {})
	watermark = read.get("watermark")


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
	"""Get sender's name from Facebook."""
	settings = frappe.get_single("Facebook Settings")

	if not settings.is_connected:
		return "Unknown"

	import requests
	params = {
		"access_token": settings.get_password("page_access_token"),
		"fields": "first_name,last_name,name"
	}

	url = f"https://graph.facebook.com/v21.0/{sender_psid}"

	try:
		response = requests.get(url, params=params, timeout=15)
		result = response.json()

		if response.status_code == 200:
			return result.get("name", "Unknown")

	except Exception:
		pass

	return "Unknown"


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

	url = f"https://graph.facebook.com/v21.0/{lead_id}"

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
