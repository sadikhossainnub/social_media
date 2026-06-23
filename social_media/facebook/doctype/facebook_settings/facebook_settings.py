# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta


class FacebookSettings(Document):
    def before_save(self):
        """Set the redirect URI before saving."""
        if not self.redirect_uri:
            site_url = frappe.utils.get_url()
            self.redirect_uri = f"{site_url}/api/method/social_media.facebook.auth.callback"
        
        # Generate messenger verify token if not set
        if not self.messenger_verify_token:
            import secrets
            self.messenger_verify_token = secrets.token_urlsafe(32)

    def after_save(self):
        """Update connection status based on current configuration"""
        self.update_connection_status()

    def update_connection_status(self):
        """Update connection status based on current state"""
        if self.is_connected and self.page_access_token:
            frappe.db.set_value("Facebook Settings", self.name, {
                "connection_status": "Connected"
            })
        else:
            frappe.db.set_value("Facebook Settings", self.name, {
                "connection_status": "Not Connected"
            })


@frappe.whitelist()
def get_connection_status():
    """Get current connection status."""
    settings = frappe.get_doc("Facebook Settings")
    
    return {
        "is_connected": bool(settings.is_connected),
        "page_name": settings.page_name or "",
        "page_id": settings.page_id or "",
        "token_expiry": settings.token_expiry,
        "app_id": settings.app_id or ""
    }


@frappe.whitelist()
def refresh_token():
    """Refresh the access token if it's about to expire."""
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.user_access_token:
        return {"success": False, "message": "No user token found"}
    
    # Check if token is expiring soon (within 7 days)
    if settings.token_expiry:
        days_until_expiry = (settings.token_expiry - datetime.now()).days
        if days_until_expiry > 7:
            return {
                "success": True,
                "message": f"Token valid for {days_until_expiry} more days"
            }
    
    # Import auth module and refresh
    from social_media.facebook import auth
    tokens = auth.exchange_short_lived_token(settings.user_access_token)
    
    if not tokens:
        return {"success": False, "message": "Failed to refresh token"}
    
    # Update settings
    settings.user_access_token = tokens.get("access_token")
    
    if "expires_in" in tokens:
        expiry_days = int(tokens["expires_in"]) // (24 * 3600)
        settings.token_expiry = datetime.now() + timedelta(days=expiry_days)
    
    settings.save(ignore_permissions=True)
    
    return {
        "success": True,
        "message": "Token refreshed successfully",
        "expires_in": tokens.get("expires_in")
    }


@frappe.whitelist()
def disconnect():
    """Disconnect from Facebook."""
    settings = frappe.get_doc("Facebook Settings")
    
    settings.is_connected = 0
    settings.user_access_token = ""
    settings.page_access_token = ""
    settings.page_id = ""
    settings.page_name = ""
    settings.token_expiry = None
    
    settings.save(ignore_permissions=True)
    
    return {"message": "Disconnected from Facebook"}


@frappe.whitelist()
def test_post():
    """Test post to Facebook."""
    from social_media.facebook import post
    
    result = post.post_to_page("Test post from ERPNext!")
    
    if result.get("success"):
        return {
            "success": True,
            "message": f"Test post successful! ID: {result.get('post_id')}"
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error")
        }


@frappe.whitelist()
def sync_leads(form_id=None):
    """Sync leads from Facebook."""
    from social_media.facebook import leads
    
    return leads.sync_leads(form_id)


@frappe.whitelist()
def get_leads(form_id=None, status=None):
    """Get Facebook leads."""
    from social_media.facebook import leads
    
    return leads.get_leads(form_id, status)
