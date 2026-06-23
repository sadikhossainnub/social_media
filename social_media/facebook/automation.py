"""
Facebook Automation System
Handles all AI-powered automation features for Facebook
"""

import frappe
from frappe.model.document import Document
from datetime import datetime
import json


class FacebookAutomationSystem:
    """Main automation system for Facebook integration"""

    def __init__(self, page_id=None):
        """Initialize with Facebook page ID"""
        self.page_id = page_id
        self.settings = frappe.get_single("Facebook Settings")
        
        # Use page_id from settings if not provided
        if not self.page_id and self.settings.page_id:
            self.page_id = self.settings.page_id

    def handle_incoming_message(self, message_data):
        """
        Handle incoming Facebook message with automation
        
        Args:
            message_data: Dictionary with message details
                - message_id: Facebook message ID
                - sender_id: Sender's Facebook ID
                - sender_name: Sender's name
                - message_text: Message content
                - has_image: Boolean if message has image
                - has_media: Boolean if message has media
        """
        try:
            # 1. Process auto-reply
            self._process_auto_reply(message_data)
            
            # 2. Save interaction data
            self._save_user_interaction(message_data)
            
            # 3. Send admin notification if needed
            self._check_and_notify_admin(message_data)
        
        except Exception as e:
            frappe.log_error(f"Error handling incoming message: {str(e)}", "Facebook Automation")

    def handle_incoming_comment(self, comment_data):
        """
        Handle incoming Facebook comment with AI reply
        
        Args:
            comment_data: Dictionary with comment details
                - comment_id: Facebook comment ID
                - post_id: Facebook post ID
                - comment_text: Comment content
                - author_id: Author's Facebook ID
                - author_name: Author's name
        """
        try:
            from social_media.facebook.doctype.facebook_ai_comment_reply.facebook_ai_comment_reply import process_new_comment
            
            # Process comment with AI reply system
            process_new_comment(comment_data)
        
        except Exception as e:
            frappe.log_error(f"Error handling incoming comment: {str(e)}", "Facebook Automation")

    def _process_auto_reply(self, message_data):
        """Process auto-reply for incoming message"""
        try:
            from social_media.facebook.doctype.facebook_auto_reply.facebook_auto_reply import process_incoming_message
            
            message_data["page_id"] = self.page_id
            process_incoming_message(message_data)
        
        except Exception as e:
            frappe.log_error(f"Error processing auto-reply: {str(e)}", "Facebook Automation")

    def _save_user_interaction(self, message_data):
        """Save user interaction data for analytics"""
        try:
            # Create chat record
            frappe.get_doc({
                "doctype": "Facebook Messenger Chat",
                "sender_id": message_data.get("sender_id"),
                "sender_name": message_data.get("sender_name"),
                "message": message_data.get("message_text"),
                "direction": "Incoming",
                "is_read": 0
            }).insert(ignore_permissions=True)
        
        except Exception as e:
            frappe.log_error(f"Error saving interaction: {str(e)}", "Facebook Automation")

    def _check_and_notify_admin(self, message_data):
        """
        Check if admin notification is needed
        Conditions: New customer, negative sentiment, keyword triggers
        """
        try:
            # Check if sender is new customer
            existing_logs = frappe.db.count(
                "Facebook Messenger Chat",
                filters={
                    "sender_id": message_data.get("sender_id")
                }
            )
            
            is_new_customer = existing_logs <= 1
            
            # Check sentiment if contains negative words
            negative_keywords = ["problem", "issue", "not working", "terrible", "worst"]
            message_lower = message_data.get("message_text", "").lower()
            has_negative = any(keyword in message_lower for keyword in negative_keywords)
            
            # Notify admin if new customer or negative sentiment
            if is_new_customer or has_negative:
                self._send_admin_notification(message_data, is_new_customer, has_negative)
        
        except Exception as e:
            frappe.log_error(f"Error checking admin notification: {str(e)}", "Facebook Automation")

    def _send_admin_notification(self, message_data, is_new=False, negative=False):
        """Send notification to admin"""
        try:
            admin_users = frappe.get_all(
                "User",
                filters={"roles": "Administrator"},
                fields=["name", "email"]
            )
            
            notification_type = []
            if is_new:
                notification_type.append("New Customer Message")
            if negative:
                notification_type.append("Negative Sentiment Detected")
            
            subject = f"[Facebook] {', '.join(notification_type)} from {message_data.get('sender_name')}"
            message = f"""
New message from {message_data.get('sender_name')}:

Message: {message_data.get('message_text')[:200]}...

Status: {'New Customer' if is_new else 'Existing Customer'}
Sentiment: {'Negative' if negative else 'Neutral/Positive'}

Facebook Page: {self.page_id or self.settings.page_name}
Time: {datetime.now()}

Link: {frappe.utils.get_url()}/app/facebook-messenger-chat
"""
            
            for user in admin_users:
                if user.email:
                    frappe.sendmail(
                        recipients=[user.email],
                        subject=subject,
                        message=message,
                        priority="Urgent" if negative else "Normal"
                    )
        
        except Exception as e:
            frappe.log_error(f"Error sending admin notification: {str(e)}", "Facebook Automation")


def process_facebook_webhook(data):
    """
    Process incoming Facebook webhook
    Main entry point for all Facebook events
    
    Args:
        data: Webhook payload from Facebook
    """
    try:
        for entry in data.get("entry", []):
            page_id = entry.get("id")
            
            # Initialize automation system for this page
            automation = FacebookAutomationSystem(page_id)
            
            # Process messages
            for messaging in entry.get("messaging", []):
                if "message" in messaging and "postback" not in messaging:
                    message_data = {
                        "message_id": messaging["message"].get("mid"),
                        "sender_id": messaging["sender"]["id"],
                        "sender_name": messaging["sender"].get("name", "Customer"),
                        "message_text": messaging["message"].get("text", ""),
                        "has_image": "attachments" in messaging["message"],
                        "has_media": len(messaging["message"].get("attachments", [])) > 0
                    }
                    automation.handle_incoming_message(message_data)
            
            # Process comments
            for event in entry.get("changes", []):
                if event.get("field") == "feed":
                    value = event.get("value", {})
                    if "comment_id" in value:
                        comment_data = {
                            "comment_id": value.get("comment_id"),
                            "post_id": value.get("post_id"),
                            "comment_text": value.get("message"),
                            "author_id": value.get("from", {}).get("id"),
                            "author_name": value.get("from", {}).get("name"),
                            "page_id": page_id
                        }
                        automation.handle_incoming_comment(comment_data)
    
    except Exception as e:
        frappe.log_error(f"Error processing webhook: {str(e)}", "Facebook Automation")


@frappe.whitelist()
def get_automation_status(page_id=None):
    """Get automation status for a page"""
    try:
        settings = frappe.get_single("Facebook Settings")
        
        # Use page_id from settings if not provided
        if not page_id and settings.page_id:
            page_id = settings.page_id
        
        if not page_id:
            return {
                "success": False,
                "error": "No page ID configured"
            }
        
        auto_reply_count = frappe.db.count("Facebook Auto Reply", {"facebook_page": page_id, "enabled": 1})
        comment_reply_count = frappe.db.count("Facebook AI Comment Reply", {"facebook_page": page_id})
        scheduled_posts = frappe.db.count("Facebook Auto Post Publisher", {"facebook_page": page_id, "publish_status": "Scheduled"})
        
        return {
            "success": True,
            "auto_replies_enabled": auto_reply_count,
            "ai_comment_replies": comment_reply_count,
            "scheduled_posts": scheduled_posts,
            "automation_active": (auto_reply_count + comment_reply_count + scheduled_posts) > 0
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_interaction_analytics(days=30):
    """Get user interaction analytics"""
    try:
        from datetime import datetime, timedelta
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Get message count
        message_count = frappe.db.count(
            "Facebook Messenger Chat",
            filters={
                "timestamp": [">", start_date]
            }
        )
        
        # Get unique users
        unique_users = frappe.db.sql("""
            SELECT COUNT(DISTINCT sender_id) as count
            FROM `tabFacebook Messenger Chat`
            WHERE timestamp > %s
        """, start_date, as_dict=True)
        
        return {
            "success": True,
            "total_messages": message_count,
            "unique_users": unique_users[0]["count"] if unique_users else 0,
            "period_days": days
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
