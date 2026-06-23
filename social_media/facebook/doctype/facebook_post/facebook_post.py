# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import send_text


class FacebookPost(Document):
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
            
            if not comment:
                frappe.throw("Comment not found")
            
            # Send direct message to commenter
            response = send_text(
                page_id=self.page,
                recipient_psid=comment.commenter_psid,
                text=message
            )
            
            # Log the message
            self.log_message(
                direction="Outbound",
                status="Sent",
                recipient_psid=comment.commenter_psid,
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
        """Like this post."""
        try:
            # This would call Facebook API to like the post
            # For now, just update the count locally
            self.like_count = (self.like_count or 0) + 1
            self.save()
            frappe.msgprint("Post liked!")
        except Exception as e:
            frappe.throw(f"Failed to like post: {str(e)}")

    @frappe.whitelist()
    def fetch_comments(self):
        """Fetch comments for this post from Facebook."""
        try:
            # This would call Facebook API to fetch comments
            # For now, just update the count locally
            frappe.msgprint("Comments fetched (API integration needed)")
        except Exception as e:
            frappe.msgprint(f"Failed to fetch comments: {str(e)}")

    @frappe.whitelist()
    def fetch_post_details(self):
        """Fetch latest post details from Facebook."""
        try:
            # This would call Facebook API to fetch post details
            frappe.msgprint("Post details refreshed (API integration needed)")
        except Exception as e:
            frappe.msgprint(f"Failed to refresh post details: {str(e)}")

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
