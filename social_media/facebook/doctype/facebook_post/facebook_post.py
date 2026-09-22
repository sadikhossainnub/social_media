# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import send_text
from social_media.facebook.graph_client import FacebookGraphClient


class FacebookPost(Document):
	post_id: str
	page: str
	page_name: str | None
	status: str
	post_type: str
	permalink_url: str | None
	message: str | None
	like_count: int | None
	comment_count: int | None
	share_count: int | None
	comments_html: str | None

	def after_insert(self):
		"""Fetch comments when post is created."""
		self.fetch_comments()

	@frappe.whitelist()
	def reply_to_comment(self, comment_id, message):
		"""Reply to a specific comment."""
		try:
			# Get the comment to find the commenter's PSID
			comment = frappe.db.get_value(
				"Facebook Comment",
				comment_id,
				["commenter_psid", "post_id"],
				as_dict=True
			)
			
			if not isinstance(comment, dict):
				frappe.throw("Comment not found")
			
			psid = comment.get("commenter_psid")
			if not psid:
				frappe.throw("Commenter PSID not available")

			# Send direct message to commenter
			response = send_text(
				page_id=self.page,
				recipient_id=str(psid),
				message=message
			)
			
			# Log the message
			self.log_message(
				direction="Outbound",
				status="Sent",
				recipient_psid=str(psid),
				message_text=message
			)
			
			return response
		except Exception as e:
			frappe.log_error(
				title="Facebook Reply to Comment Error",
				message=f"Comment: {comment_id}\n{str(e)}"
			)
			frappe.throw(f"Failed to reply: {str(e)}")

	@frappe.whitelist()
	def like_post(self):
		"""Like this post via Facebook Graph API."""
		try:
			client = FacebookGraphClient(page_id=self.page)
			res = client.post(f"/{self.post_id}/likes")
			if isinstance(res, dict) and res.get("success"):
				self.db_set("like_count", (self.like_count or 0) + 1)
				frappe.msgprint("Post liked on Facebook!", alert=True)
			else:
				self.db_set("like_count", (self.like_count or 0) + 1)
				frappe.msgprint("Post liked locally.", alert=True)
		except Exception as e:
			frappe.throw(f"Failed to like post: {str(e)}")

	@frappe.whitelist()
	def fetch_comments(self):
		"""Fetch comments for this post from Facebook Graph API."""
		try:
			if not self.post_id:
				return

			client = FacebookGraphClient(page_id=self.page)
			res = client.get_post_comments(self.post_id)

			if isinstance(res, dict) and "data" in res:
				comments_list = res.get("data")
				if isinstance(comments_list, list):
					count = len(comments_list)

					html_builder = []
					for c in comments_list:
						if not isinstance(c, dict):
							continue

						cid = c.get("id")
						msg = c.get("message", "")
						created_time = c.get("created_time")
						from_dict = c.get("from") if isinstance(c.get("from"), dict) else {}
						c_name = from_dict.get("name", "Anonymous")
						c_psid = from_dict.get("id", "")
						like_cnt = c.get("like_count", 0)

						html_builder.append(f"""
						<div style="border-bottom: 1px solid #eee; padding: 8px 0;">
							<strong>{frappe.utils.escape_html(str(c_name))}</strong> 
							<small class="text-muted">({created_time or ''})</small>
							<p style="margin: 4px 0 0 0;">{frappe.utils.escape_html(str(msg))}</p>
						</div>
						""")

						# Create or update Facebook Comment doc
						if cid:
							if not frappe.db.exists("Facebook Comment", str(cid)):
								comment_doc = frappe.get_doc({
									"doctype": "Facebook Comment",
									"comment_id": cid,
									"post": self.name,
									"post_id": self.post_id,
									"page": self.page,
									"commenter_name": c_name,
									"commenter_psid": c_psid,
									"message": msg,
									"like_count": like_cnt,
									"created_time": created_time
								})
								comment_doc.insert(ignore_permissions=True)
							else:
								frappe.db.set_value("Facebook Comment", str(cid), {
									"message": msg,
									"like_count": like_cnt
								})

					self.db_set("comment_count", count)
					self.db_set("comments_html", "".join(html_builder))
					frappe.msgprint(f"Fetched {count} comments from Facebook!", alert=True)
				else:
					frappe.msgprint("No comments list found in Facebook response.", alert=True)
			else:
				frappe.msgprint("No comments found on Facebook for this post.", alert=True)
		except Exception as e:
			frappe.log_error(f"Error fetching comments: {str(e)}", "Facebook Post")
			frappe.msgprint(f"Failed to fetch comments: {str(e)}", alert=True)

	@frappe.whitelist()
	def fetch_post_details(self):
		"""Fetch latest post details from Facebook Graph API."""
		try:
			if not self.post_id:
				return

			client = FacebookGraphClient(page_id=self.page)
			res = client.get(
				f"/{self.post_id}",
				params={"fields": "id,message,created_time,shares,likes.summary(true),comments.summary(true),permalink_url"}
			)

			if isinstance(res, dict):
				msg = res.get("message")
				permalink = res.get("permalink_url")
				
				likes_obj = res.get("likes")
				likes_summary = likes_obj.get("summary") if isinstance(likes_obj, dict) else None
				likes_count = likes_summary.get("total_count") if isinstance(likes_summary, dict) else None

				comments_obj = res.get("comments")
				comments_summary = comments_obj.get("summary") if isinstance(comments_obj, dict) else None
				comments_count = comments_summary.get("total_count") if isinstance(comments_summary, dict) else None

				shares_obj = res.get("shares")
				shares_count = shares_obj.get("count") if isinstance(shares_obj, dict) else None

				if msg:
					self.db_set("message", str(msg))
				if permalink:
					self.db_set("permalink_url", str(permalink))
				if likes_count is not None:
					self.db_set("like_count", int(likes_count))
				if comments_count is not None:
					self.db_set("comment_count", int(comments_count))
				if shares_count is not None:
					self.db_set("share_count", int(shares_count))

				frappe.msgprint("Post details refreshed successfully from Facebook!", alert=True)
			else:
				frappe.msgprint("Could not fetch post details from Facebook Graph API.", alert=True)
		except Exception as e:
			frappe.log_error(f"Error refreshing post details: {str(e)}", "Facebook Post")
			frappe.msgprint(f"Failed to refresh post details: {str(e)}", alert=True)

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
