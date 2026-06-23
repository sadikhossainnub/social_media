# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import send_text


class FacebookComment(Document):
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
                recipient_psid=self.commenter_psid,
                text=message
            )
            
            # Update reply fields
            self.reply_message = message
            self.replied_time = frappe.utils.now()
            self.replied_by = frappe.session.user
            self.save()
            
            # Log the message
            self.log_message(
                direction="Outbound",
                status="Sent",
                recipient_psid=self.commenter_psid,
                message_text=message
            )
            
            frappe.msgprint("Reply sent successfully!")
            return response
        except Exception as e:
            frappe.log_error(
                title="Facebook Comment Reply Error",
                message=f"Comment: {self.name}\n{str(e)}"
            )
            frappe.throw(f"Failed to reply: {str(e)}")

    @frappe.whitelist()
    def like_comment(self):
        """Like this comment."""
        try:
            # This would call Facebook API to like the comment
            self.like_count = (self.like_count or 0) + 1
            self.save()
            frappe.msgprint("Comment liked!")
        except Exception as e:
            frappe.throw(f"Failed to like comment: {str(e)}")

    @frappe.whitelist()
    def fetch_replies(self):
        """Fetch replies for this comment from Facebook."""
        try:
            # This would call Facebook API to fetch replies
            frappe.msgprint("Replies fetched (API integration needed)")
        except Exception as e:
            frappe.msgprint(f"Failed to fetch replies: {str(e)}")

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
