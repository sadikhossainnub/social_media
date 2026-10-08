"""
Real-time Notifications
Handles Socket.IO broadcasts for comments, messages, and alerts to the Vue portal.

Uses Frappe's doctype-based rooms so that browsers can subscribe via
socket.emit("doctype_subscribe", "Facebook Messenger Chat") and receive events.
All publishes use after_commit=True to ensure data is committed before broadcast.
"""

import frappe


def is_realtime_enabled():
	"""Check if real-time notifications are enabled in settings."""
	try:
		return getattr(frappe.get_single("Facebook Settings"), "enable_realtime_notifications", 1)
	except Exception:
		return True


def publish_new_comment(comment_doc):
	"""Broadcast new comment to the portal via doctype room."""
	if not is_realtime_enabled():
		return

	try:
		comment_data = {
			"name": comment_doc.name,
			"comment_id": comment_doc.comment_id,
			"post": comment_doc.post,
			"post_id": comment_doc.post_id,
			"page": comment_doc.page,
			"commenter_name": comment_doc.commenter_name,
			"message": comment_doc.message,
			"created_time": str(comment_doc.created_time),
			"sentiment": comment_doc.sentiment,
			"sentiment_score": comment_doc.sentiment_score,
			"is_hidden": getattr(comment_doc, "is_hidden", 0),
			"is_spam": getattr(comment_doc, "is_spam", 0),
		}

		# Publish to the doctype room — browsers join via
		# socket.emit("doctype_subscribe", "Facebook Comment")
		frappe.publish_realtime(
			event="fb_new_comment",
			message=comment_data,
			doctype="Facebook Comment",
			after_commit=True,
		)
	except Exception as e:
		frappe.log_error(f"Error publishing real-time comment: {str(e)}", "Facebook Realtime")


def publish_new_message(message_doc):
	"""Broadcast new Messenger message to the portal via doctype room."""
	if not is_realtime_enabled():
		return

	try:
		message_data = {
			"name": message_doc.name,
			"sender_id": message_doc.sender_id,
			"sender_name": message_doc.sender_name,
			"page": message_doc.page,
			"conversation_id": message_doc.conversation_id,
			"direction": message_doc.direction,
			"timestamp": str(message_doc.timestamp),
			"message": message_doc.message,
			"is_read": message_doc.is_read,
			"attachments": message_doc.attachments,
			"conversation_status": getattr(message_doc, "conversation_status", "Open"),
			"assigned_agent": getattr(message_doc, "assigned_agent", None),
		}

		# Primary event: new message — browsers subscribe to the doctype room
		frappe.publish_realtime(
			event="fb_new_message",
			message=message_data,
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)

		# Thread update event for conversation list re-sorting
		frappe.publish_realtime(
			event="fb_thread_update",
			message=message_data,
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)

		# General alert for incoming messages only
		if message_doc.direction == "Incoming":
			frappe.publish_realtime(
				event="fb_alert",
				message={
					"title": f"New Message from {message_doc.sender_name}",
					"message": message_doc.message[:100] if message_doc.message else "Attachment",
					"type": "message",
					"page": message_doc.page,
					"conversation_id": message_doc.conversation_id,
				},
				doctype="Facebook Messenger Chat",
				after_commit=True,
			)
	except Exception as e:
		frappe.log_error(f"Error publishing real-time message: {str(e)}", "Facebook Realtime")


def publish_complaint_alert(message_doc):
	"""Broadcast urgent complaint alert to the portal."""
	if not is_realtime_enabled():
		return

	try:
		frappe.publish_realtime(
			event="fb_complaint_alert",
			message={
				"name": message_doc.name,
				"sender_name": message_doc.sender_name,
				"message": message_doc.message,
				"conversation_id": message_doc.conversation_id,
				"priority": getattr(message_doc, "priority", "High"),
				"page": message_doc.page,
			},
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)
	except Exception as e:
		frappe.log_error(f"Error publishing complaint alert: {str(e)}", "Facebook Realtime")


def publish_notification(notification_data):
	"""Broadcast system notification to the portal."""
	if not is_realtime_enabled():
		return

	try:
		frappe.publish_realtime(
			event="fb_notification",
			message=notification_data,
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)
	except Exception as e:
		frappe.log_error(f"Error publishing real-time notification: {str(e)}", "Facebook Realtime")


def publish_delivery_receipt(conversation_id, watermark=None):
	"""Broadcast message delivery receipt over Socket.IO."""
	if not is_realtime_enabled():
		return

	try:
		frappe.publish_realtime(
			event="fb_delivery_receipt",
			message={
				"conversation_id": conversation_id,
				"watermark": watermark,
			},
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)
	except Exception as e:
		frappe.log_error(f"Error publishing delivery receipt: {str(e)}", "Facebook Realtime")


def publish_read_receipt(conversation_id, watermark=None):
	"""Broadcast message read/seen receipt over Socket.IO."""
	if not is_realtime_enabled():
		return

	try:
		frappe.publish_realtime(
			event="fb_read_receipt",
			message={
				"conversation_id": conversation_id,
				"watermark": watermark,
			},
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)
	except Exception as e:
		frappe.log_error(f"Error publishing read receipt: {str(e)}", "Facebook Realtime")


def publish_typing_indicator(conversation_id, sender_psid, is_typing=True):
	"""Broadcast customer typing status over Socket.IO."""
	if not is_realtime_enabled():
		return

	try:
		frappe.publish_realtime(
			event="fb_typing_indicator",
			message={
				"conversation_id": conversation_id,
				"sender_psid": sender_psid,
				"is_typing": bool(is_typing),
			},
			doctype="Facebook Messenger Chat",
			after_commit=True,
		)
	except Exception as e:
		frappe.log_error(f"Error publishing typing indicator: {str(e)}", "Facebook Realtime")
