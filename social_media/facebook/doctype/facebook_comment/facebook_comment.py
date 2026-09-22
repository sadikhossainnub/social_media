# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import send_text
from social_media.facebook.graph_client import FacebookGraphClient


class FacebookComment(Document):
	comment_id: str
	post: str
	post_id: str | None
	page: str
	page_name: str | None
	commenter_name: str | None
	commenter_psid: str | None
	message: str | None
	like_count: int | None
	reply_count: int | None
	reply_message: str | None
	replied_time: str | None
	replied_by: str | None

	def after_insert(self):
		"""Fetch replies when comment is created."""
		self.fetch_replies()

	@frappe.whitelist()
	def reply(self, message):
		"""Reply to this comment via direct message to commenter."""
		try:
			if not self.commenter_psid:
				frappe.throw("Commenter PSID not available")
			
			# Send direct message to commenter
			response = send_text(
				page_id=self.page,
				recipient_id=self.commenter_psid,
				message=message
			)
			
			# Update reply fields
			self.db_set("reply_message", message)
			self.db_set("replied_time", frappe.utils.now())
			self.db_set("replied_by", frappe.session.user)
			
			# Log the message
			self.log_message(
				direction="Outbound",
				status="Sent",
				recipient_psid=self.commenter_psid,
				message_text=message
			)
			
			frappe.msgprint("Reply sent successfully!", alert=True)
			return response
		except Exception as e:
			frappe.log_error(
				title="Facebook Comment Reply Error",
				message=f"Comment: {self.name}\n{str(e)}"
			)
			frappe.throw(f"Failed to reply: {str(e)}")

	@frappe.whitelist()
	def like_comment(self):
		"""Like this comment via Facebook Graph API."""
		try:
			client = FacebookGraphClient(page_id=self.page)
			res = client.post(f"/{self.comment_id}/likes")
			if res and res.get("success"):
				self.db_set("like_count", (self.like_count or 0) + 1)
				frappe.msgprint("Comment liked on Facebook!", alert=True)
			else:
				self.db_set("like_count", (self.like_count or 0) + 1)
				frappe.msgprint("Comment liked locally.", alert=True)
		except Exception as e:
			frappe.throw(f"Failed to like comment: {str(e)}")

	@frappe.whitelist()
	def fetch_replies(self):
		"""Fetch replies for this comment from Facebook Graph API."""
		try:
			if not self.comment_id:
				return

			client = FacebookGraphClient(page_id=self.page)
			res = client.get(f"/{self.comment_id}/comments", params={"fields": "id,message,from,created_time,like_count"})

			if res and "data" in res:
				replies = res["data"]
				count = len(replies)
				self.db_set("reply_count", count)
				frappe.msgprint(f"Fetched {count} replies from Facebook!", alert=True)
		except Exception as e:
			frappe.log_error(f"Error fetching comment replies: {str(e)}", "Facebook Comment")

	def log_message(self, direction, status, recipient_psid, message_text):
		"""Log a message to Facebook Message Log."""
		doc = frappe.get_doc({
			"doctype": "Facebook Message Log",
			"instance": self.page,
			"direction": direction,
			"status": status,
			"sender_psid": recipient_psid,
			"message_text": message_text
		})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
