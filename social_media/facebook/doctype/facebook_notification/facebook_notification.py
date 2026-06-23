# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import send_text


class FacebookNotification(Document):
	pass


def trigger_facebook_notifications(doc, method=None):
	"""Trigger Facebook notifications on document events."""
	if not frappe.db.exists("Facebook Notification", {"document_type": doc.doctype, "enabled": 1}):
		return

	notifications = frappe.get_all(
		"Facebook Notification",
		filters={
			"document_type": doc.doctype,
			"enabled": 1
		},
		fields=["name", "event", "condition", "message_template", "page", "send_to"]
	)

	for notification in notifications:
		# Check event match
		event_match = False
		if method == "after_insert" and notification.event == "After Insert":
			event_match = True
		elif method == "on_update" and notification.event == "After Save":
			event_match = True
		elif method == "on_submit" and notification.event == "On Submit":
			event_match = True
		elif method == "on_cancel" and notification.event == "On Cancel":
			event_match = True

		if not event_match:
			continue

		# Check condition
		if notification.condition:
			try:
				if not frappe.safe_eval(notification.condition, None, {"doc": doc}):
					continue
			except Exception:
				continue

		# Send message
		try:
			send_facebook_message(notification, doc)
		except Exception as e:
			frappe.log_error(
				title="Facebook Notification Error",
				message=f"Notification: {notification.name}\nDocument: {doc.name}\n{str(e)}"
			)


def send_facebook_message(notification, doc):
	"""Send a Facebook message based on notification configuration."""
	page = notification.page
	send_to = notification.send_to
	message_template = notification.message_template

	# Get PSID(s)
	psids = []
	if send_to.startswith("PSID:") or send_to.isdigit():
		# Direct PSID
		psids = [send_to.strip()]
	else:
		# Field name(s)
		field_names = [f.strip() for f in send_to.split(",")]
		for field_name in field_names:
			if hasattr(doc, field_name):
				value = getattr(doc, field_name)
				if value:
					psids.append(str(value))

	if not psids:
		return

	# Render message template
	message = frappe.render_template(message_template, {"doc": doc})

	# Send to each PSID
	for psid in psids:
		try:
			response = send_text(page, psid, message)
			frappe.db.set_value("Facebook Message Log", {
				"instance": page,
				"sender_psid": psid
			}, "status", "Sent")
		except Exception as e:
			frappe.log_error(
				title="Facebook Send Message Error",
				message=f"PSID: {psid}\nMessage: {message}\n{str(e)}"
			)