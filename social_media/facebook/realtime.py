"""
Real-time Notifications
Handles Socket.IO broadcasts for comments, messages, and alerts to the Vue portal.
"""

import frappe


def is_realtime_enabled():
	"""Check if real-time notifications are enabled in settings."""
	try:
		return getattr(frappe.get_single("Facebook Settings"), "enable_realtime_notifications", 1)
	except Exception:
		return True


def publish_new_comment(comment_doc):
	"""Broadcast new comment to the portal."""
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
			"sentiment_score": comment_doc.sentiment_score
		}
		
		# Publish to all users subscribed to this page event
		frappe.publish_realtime(
			event="fb_new_comment",
			message=comment_data,
			room=f"fb_page_{comment_doc.page}"
		)
		
		# Also publish general alert
		frappe.publish_realtime(
			event="fb_alert",
			message={
				"title": f"New Comment from {comment_doc.commenter_name}",
				"message": comment_doc.message[:100],
				"type": "comment",
				"page": comment_doc.page
			}
		)
	except Exception as e:
		frappe.log_error(f"Error publishing real-time comment: {str(e)}", "Facebook Realtime")


def publish_new_message(message_doc):
	"""Broadcast new Messenger message to the portal."""
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
			"attachments": message_doc.attachments
		}
		
		frappe.publish_realtime(
			event="fb_new_message",
			message=message_data,
			room=f"fb_conversation_{message_doc.conversation_id}"
		)
		
		# Publish to list/inbox room too
		frappe.publish_realtime(
			event="fb_thread_update",
			message=message_data,
			room=f"fb_page_{message_doc.page}"
		)
		
		# Alert
		if message_doc.direction == "Incoming":
			frappe.publish_realtime(
				event="fb_alert",
				message={
					"title": f"New Message from {message_doc.sender_name}",
					"message": message_doc.message[:100] if message_doc.message else "Attachment",
					"type": "message",
					"page": message_doc.page,
					"conversation_id": message_doc.conversation_id
				}
			)
	except Exception as e:
		frappe.log_error(f"Error publishing real-time message: {str(e)}", "Facebook Realtime")


def publish_notification(notification_data):
	"""Broadcast system notification to the portal."""
	if not is_realtime_enabled():
		return

	try:
		frappe.publish_realtime(
			event="fb_notification",
			message=notification_data
		)
	except Exception as e:
		frappe.log_error(f"Error publishing real-time notification: {str(e)}", "Facebook Realtime")
