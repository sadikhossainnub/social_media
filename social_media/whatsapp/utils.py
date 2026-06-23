import frappe
import requests
import json


def format_number(number):
	"""
	Format number for WhatsApp, default to Bangladesh (880) if no country code.
	- 01XXXXXXXXX (11 digits) -> 8801XXXXXXXXX
	- 1XXXXXXXXX (10 digits) -> 8801XXXXXXXXX
	- Removes +, spaces, etc.
	"""
	if not number:
		return ""
	
	# Strip non-digits
	num = "".join(filter(str.isdigit, str(number)))
	
	if num.startswith("01") and len(num) == 11:
		return "88" + num
	elif num.startswith("1") and len(num) == 10:
		return "880" + num
	elif num.startswith("880") and len(num) == 13:
		return num
	
	return num


# ──────────────────────────────────────────────
# Settings Helper
# ──────────────────────────────────────────────

def get_settings():
	"""Return Whatsapp Settings with cleaned endpoint and decrypted global API key."""
	settings = frappe.get_single("Whatsapp Settings")
	if not settings.evolution_api_endpoint:
		frappe.throw("Please configure Whatsapp Settings first.")

	endpoint = settings.evolution_api_endpoint.strip()

	# Password field must be read via get_password
	global_api_key = settings.get_password("api_key")
	if not global_api_key:
		frappe.throw("Please set the Global API Key in Whatsapp Settings.")

	if endpoint.endswith("/"):
		endpoint = endpoint[:-1]
	if endpoint.endswith("/manager"):
		endpoint = endpoint[:-8]

	settings.evolution_api_endpoint = endpoint
	settings.api_key = global_api_key
	return settings


def _get_instance_key(instance_name):
	"""Get the instance-specific API key (hash) for an instance."""
	api_key = frappe.db.get_value("Whatsapp Instance", instance_name, "apikey")
	if not api_key:
		# Fall back to global key
		settings = get_settings()
		return settings.api_key
	return api_key


def _global_headers():
	"""Headers using global API key — for create/delete instance."""
	settings = get_settings()
	return {
		"apikey": settings.api_key,
		"Content-Type": "application/json"
	}, settings.evolution_api_endpoint


def _instance_headers(instance_name):
	"""Headers for instance operations. Uses global API key as the admin key works for all operations."""
	settings = get_settings()
	return {
		"apikey": settings.api_key,
		"Content-Type": "application/json"
	}, settings.evolution_api_endpoint


def _handle_response(response, operation_name):
	"""Common response handler — raises frappe error with details on failure."""
	if response.status_code not in (200, 201):
		error_body = response.text[:500]
		frappe.log_error(
			title=f"WhatsApp API Error: {operation_name}",
			message=f"Status: {response.status_code}\nResponse: {error_body}"
		)
		frappe.throw(f"Evolution API Error ({operation_name}): HTTP {response.status_code} — {error_body}")
	try:
		return response.json()
	except ValueError:
		return {"status": "ok"}


# ──────────────────────────────────────────────
# Instance Management
# ──────────────────────────────────────────────

def create_instance(instance_name, token=None, number=None, integration="WHATSAPP-BAILEYS"):
	"""
	POST /instance/create
	Auth: globalApikey
	Returns: { instance: {...}, hash: "INSTANCE_APIKEY", qrcode: {...} }
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/create"

	payload = {
		"instanceName": instance_name,
		"qrcode": True,
		"integration": integration
	}
	if token:
		payload["token"] = token
	if number:
		payload["number"] = number

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Create Instance")
	except requests.exceptions.ConnectionError:
		frappe.throw(f"Cannot connect to Evolution API: {url}")
	except requests.exceptions.Timeout:
		frappe.throw(f"Evolution API timeout: {url}")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Create Instance Error", message=str(e))
		frappe.throw(f"API Error: {str(e)}")


def fetch_instances(instance_name=None, instance_id=None):
	"""
	GET /instance/fetchInstances
	Auth: globalApikey (admin fetch)
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/fetchInstances"

	params = {}
	if instance_name:
		params["instanceName"] = instance_name
	if instance_id:
		params["instanceId"] = instance_id

	try:
		response = requests.get(url, headers=headers, params=params, timeout=15)
		return _handle_response(response, "Fetch Instances")
	except requests.exceptions.ConnectionError:
		frappe.throw(f"Cannot connect to Evolution API: {url}")
	except requests.exceptions.Timeout:
		frappe.throw(f"Evolution API timeout: {url}")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Fetch Instances Error", message=str(e))
		frappe.throw(f"API Error: {str(e)}")


def connect_instance(instance_name):
	"""
	GET /instance/connect/{instance}
	Auth: globalApikey (admin key works for all operations)
	Returns QR code for pairing.
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/connect/{instance_name}"

	try:
		response = requests.get(url, headers=headers, timeout=15)
		if response.status_code in (200, 201):
			return response.json()
		else:
			error_body = response.text[:500]
			frappe.log_error(
				title="WhatsApp Connect Error",
				message=f"URL: {url}\nStatus: {response.status_code}\nResponse: {error_body}"
			)
			frappe.throw(f"Connect failed (HTTP {response.status_code}): {error_body}")
	except requests.exceptions.ConnectionError:
		frappe.throw(f"Cannot connect to Evolution API: {url}")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Connect Error", message=f"URL: {url}\n{str(e)}")
		frappe.throw(f"Connect error: {str(e)}")


def restart_instance(instance_name):
	"""
	POST /instance/restart/{instance}
	Auth: globalApikey
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/restart/{instance_name}"

	try:
		response = requests.post(url, headers=headers, timeout=15)
		return _handle_response(response, "Restart Instance")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Restart Error", message=str(e))
		frappe.throw(f"Restart failed: {str(e)}")


def connection_state(instance_name):
	"""
	GET /instance/connectionState/{instance}
	Auth: globalApikey
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/connectionState/{instance_name}"

	try:
		response = requests.get(url, headers=headers, timeout=10)
		if response.status_code == 200:
			return response.json()
	except Exception:
		pass
	return None


def logout_instance(instance_name):
	"""
	DELETE /instance/logout/{instance}
	Auth: globalApikey
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/logout/{instance_name}"

	try:
		response = requests.delete(url, headers=headers, timeout=15)
		return _handle_response(response, "Logout Instance")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Logout Error", message=str(e))
		frappe.throw(f"Logout failed: {str(e)}")


def delete_instance(instance_name):
	"""
	DELETE /instance/delete/{instance}
	Auth: globalApikey
	"""
	headers, base_url = _global_headers()
	url = f"{base_url}/instance/delete/{instance_name}"

	try:
		response = requests.delete(url, headers=headers, timeout=15)
		return _handle_response(response, "Delete Instance")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Delete Error", message=str(e))
		frappe.throw(f"Delete failed: {str(e)}")


# ──────────────────────────────────────────────
# Send Message
# ──────────────────────────────────────────────

def send_text(instance_name, number, text, delay=None):
	"""
	POST /message/sendText/{instance}
	Auth: instance apikey
	Payload: {"number": "...", "text": "..."}
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendText/{instance_name}"

	payload = {
		"number": format_number(number),
		"text": text
	}
	if delay:
		payload["delay"] = delay

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send Text")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Text Error", message=str(e))
		raise e


def send_media(instance_name, number, media_url, mediatype="image",
               mimetype="image/png", caption="", filename=""):
	"""
	POST /message/sendMedia/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendMedia/{instance_name}"

	payload = {
		"number": format_number(number),
		"mediatype": mediatype,
		"mimetype": mimetype,
		"caption": caption,
		"media": media_url,
		"fileName": filename or "file"
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=60)
		return _handle_response(response, "Send Media")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Media Error", message=str(e))
		raise e


def send_audio(instance_name, number, audio_url):
	"""
	POST /message/sendWhatsAppAudio/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendWhatsAppAudio/{instance_name}"

	payload = {
		"number": format_number(number),
		"audio": audio_url
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=60)
		return _handle_response(response, "Send Audio")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Audio Error", message=str(e))
		raise e


def send_location(instance_name, number, name, address, latitude, longitude):
	"""
	POST /message/sendLocation/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendLocation/{instance_name}"

	payload = {
		"number": format_number(number),
		"name": name,
		"address": address,
		"latitude": latitude,
		"longitude": longitude
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send Location")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Location Error", message=str(e))
		raise e


def send_contact(instance_name, number, contacts):
	"""
	POST /message/sendContact/{instance}
	Auth: instance apikey
	contacts: [{"fullName": "...", "wuid": "...", "phoneNumber": "..."}]
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendContact/{instance_name}"

	payload = {
		"number": format_number(number),
		"contact": contacts
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send Contact")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Contact Error", message=str(e))
		raise e


def send_reaction(instance_name, remote_jid, from_me, message_id, reaction):
	"""
	POST /message/sendReaction/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendReaction/{instance_name}"

	payload = {
		"key": {
			"remoteJid": remote_jid,
			"fromMe": from_me,
			"id": message_id
		},
		"reaction": reaction
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Send Reaction")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Reaction Error", message=str(e))
		raise e


def send_poll(instance_name, number, poll_name, values, selectable_count=1):
	"""
	POST /message/sendPoll/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendPoll/{instance_name}"

	payload = {
		"number": format_number(number),
		"name": poll_name,
		"selectableCount": selectable_count,
		"values": values
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send Poll")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Poll Error", message=str(e))
		raise e


def send_buttons(instance_name, number, title, description, footer, buttons):
	"""
	POST /message/sendButtons/{instance}
	Auth: instance apikey
	buttons: [{"type": "reply", "displayText": "...", "id": "..."}]
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendButtons/{instance_name}"

	payload = {
		"number": format_number(number),
		"title": title,
		"description": description,
		"footer": footer,
		"buttons": buttons
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send Buttons")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Buttons Error", message=str(e))
		raise e


def send_list(instance_name, number, title, description, button_text, footer_text, sections):
	"""
	POST /message/sendList/{instance}
	Auth: instance apikey
	sections: [{"title": "...", "rows": [{"title": "...", "description": "...", "rowId": "..."}]}]
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendList/{instance_name}"

	payload = {
		"number": format_number(number),
		"title": title,
		"description": description,
		"buttonText": button_text,
		"footerText": footer_text,
		"sections": sections
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send List")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send List Error", message=str(e))
		raise e


def send_sticker(instance_name, number, sticker_url):
	"""
	POST /message/sendSticker/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/message/sendSticker/{instance_name}"

	payload = {
		"number": number,
		"sticker": sticker_url
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Send Sticker")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Send Sticker Error", message=str(e))
		raise e


# ──────────────────────────────────────────────
# Webhook
# ──────────────────────────────────────────────

def set_webhook(instance_name, webhook_url):
	"""
	POST /webhook/set/{instance}
	Auth: instance apikey
	v2.3 payload structure with nested 'webhook' object
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/webhook/set/{instance_name}"

	payload = {
		"webhook": {
			"enabled": True,
			"url": webhook_url,
			"byEvents": False,
			"base64": False,
			"events": [
				"APPLICATION_STARTUP",
				"QRCODE_UPDATED",
				"MESSAGES_UPSERT",
				"MESSAGES_UPDATE",
				"MESSAGES_DELETE",
				"SEND_MESSAGE",
				"CONTACTS_SET",
				"CONTACTS_UPSERT",
				"CONTACTS_UPDATE",
				"PRESENCE_UPDATE",
				"CHATS_SET",
				"CHATS_UPSERT",
				"CHATS_UPDATE",
				"CHATS_DELETE",
				"CONNECTION_UPDATE",
				"CALL"
			]
		}
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Set Webhook")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Set Webhook Error", message=str(e))
		raise e


def find_webhook(instance_name):
	"""
	GET /webhook/find/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/webhook/find/{instance_name}"

	try:
		response = requests.get(url, headers=headers, timeout=15)
		if response.status_code == 200:
			return response.json()
	except Exception:
		pass
	return None


# ──────────────────────────────────────────────
# Chat Operations
# ──────────────────────────────────────────────

def check_whatsapp_number(instance_name, numbers):
	"""
	POST /chat/whatsappNumbers/{instance}
	Auth: instance apikey
	numbers: ["55911111111", "55922222222"]
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/chat/whatsappNumbers/{instance_name}"

	payload = {"numbers": [format_number(n) for n in numbers]}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Check WhatsApp Numbers")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Check Number Error", message=str(e))
		raise e


def find_contacts(instance_name, remote_jid=None):
	"""
	POST /chat/findContacts/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/chat/findContacts/{instance_name}"

	payload = {"where": {}}
	if remote_jid:
		payload["where"]["id"] = remote_jid

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Find Contacts")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Find Contacts Error", message=str(e))
		raise e


def find_messages(instance_name, remote_jid, page=1, offset=10):
	"""
	POST /chat/findMessages/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/chat/findMessages/{instance_name}"

	payload = {
		"where": {
			"key": {
				"remoteJid": remote_jid
			}
		},
		"page": page,
		"offset": offset
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Find Messages")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Find Messages Error", message=str(e))
		raise e


def fetch_profile_picture(instance_name, number):
	"""
	POST /chat/fetchProfilePictureUrl/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/chat/fetchProfilePictureUrl/{instance_name}"

	payload = {"number": format_number(number)}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Fetch Profile Picture")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Fetch Profile Picture Error", message=str(e))
		return None


def mark_message_as_read(instance_name, remote_jid, from_me, message_id):
	"""
	POST /chat/markMessageAsRead/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/chat/markMessageAsRead/{instance_name}"

	payload = {
		"readMessages": [
			{
				"remoteJid": remote_jid,
				"fromMe": from_me,
				"id": message_id
			}
		]
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Mark As Read")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Mark Read Error", message=str(e))
		raise e


# ──────────────────────────────────────────────
# Group Operations
# ──────────────────────────────────────────────

def create_group(instance_name, subject, description, participants):
	"""
	POST /group/create/{instance}
	Auth: instance apikey
	participants: ["5531900000000", "5531900000000"]
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/group/create/{instance_name}"

	payload = {
		"subject": subject,
		"description": description,
		"participants": [format_number(p) for p in participants]
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		return _handle_response(response, "Create Group")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Create Group Error", message=str(e))
		raise e


def fetch_all_groups(instance_name, get_participants=False):
	"""
	GET /group/fetchAllGroups/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/group/fetchAllGroups/{instance_name}"

	params = {"getParticipants": str(get_participants).lower()}

	try:
		response = requests.get(url, headers=headers, params=params, timeout=15)
		return _handle_response(response, "Fetch All Groups")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Fetch Groups Error", message=str(e))
		raise e


# ──────────────────────────────────────────────
# Settings Operations
# ──────────────────────────────────────────────

def set_instance_settings(instance_name, reject_call=False, msg_call="",
                          groups_ignore=False, always_online=False,
                          read_messages=False, read_status=False,
                          sync_full_history=False):
	"""
	POST /settings/set/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/settings/set/{instance_name}"

	payload = {
		"rejectCall": reject_call,
		"msgCall": msg_call,
		"groupsIgnore": groups_ignore,
		"alwaysOnline": always_online,
		"readMessages": read_messages,
		"syncFullHistory": sync_full_history,
		"readStatus": read_status
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=15)
		return _handle_response(response, "Set Settings")
	except requests.exceptions.RequestException as e:
		frappe.log_error(title="WhatsApp Set Settings Error", message=str(e))
		raise e


def find_instance_settings(instance_name):
	"""
	GET /settings/find/{instance}
	Auth: instance apikey
	"""
	headers, base_url = _instance_headers(instance_name)
	url = f"{base_url}/settings/find/{instance_name}"

	try:
		response = requests.get(url, headers=headers, timeout=15)
		if response.status_code == 200:
			return response.json()
	except Exception:
		pass
	return None
