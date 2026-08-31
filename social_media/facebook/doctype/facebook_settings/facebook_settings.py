# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

# pyrefly: ignore [missing-import]
import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta


class FacebookSettings(Document):
    def onload(self):
        """Set dynamic fields on load."""
        site_url = frappe.utils.get_url()
        self.webhook_url = f"{site_url}/api/method/social_media.facebook.api.webhook"
        if not self.redirect_uri:
            self.redirect_uri = f"{site_url}/api/method/social_media.facebook.auth.callback"

    def before_save(self):
        """Set the redirect URI before saving and format graph_api_version."""
        site_url = frappe.utils.get_url()
        self.webhook_url = f"{site_url}/api/method/social_media.facebook.api.webhook"
        if not self.redirect_uri:
            self.redirect_uri = f"{site_url}/api/method/social_media.facebook.auth.callback"
        
        # Format Graph API Version string (e.g. '21' -> 'v21.0', '21.0' -> 'v21.0')
        if self.graph_api_version:
            v_str = str(self.graph_api_version).strip().lower()
            if not v_str.startswith("v"):
                v_str = f"v{v_str}"
            if "." not in v_str:
                v_str = f"{v_str}.0"
            self.graph_api_version = v_str
        else:
            self.graph_api_version = "v21.0"

        # Generate messenger verify token if not set
        if not self.messenger_verify_token:
            import secrets
            self.messenger_verify_token = secrets.token_hex(5)

    def after_save(self):
        """Update connection status based on current configuration"""
        self.update_connection_status()

    def update_connection_status(self):
        """Update connection status based on current state"""
        if self.page_access_token or (self.is_connected and self.app_id):
            frappe.db.set_value("Facebook Settings", self.name, "is_connected", 1, update_modified=False)
        else:
            frappe.db.set_value("Facebook Settings", self.name, "is_connected", 0, update_modified=False)



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
    
    # Use get_password() for Password fields
    user_access_token = settings.get_password("user_access_token")
    if not user_access_token:
        return {"success": False, "message": "No user token found"}
    
    # Check if token is expiring soon (within 7 days)
    if settings.token_expiry:
        from frappe.utils import get_datetime
        expiry_dt = get_datetime(settings.token_expiry)
        days_until_expiry = (expiry_dt - datetime.now()).days
        if days_until_expiry > 7:
            return {
                "success": True,
                "message": f"Token valid for {days_until_expiry} more days"
            }
    
    # Import auth module and refresh
    from social_media.facebook import auth
    tokens = auth.exchange_short_lived_token(user_access_token)
    
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


@frappe.whitelist()
def set_manual_token(page_access_token, page_id=None, page_name=None):
	"""
	Manually set a Page Access Token obtained from Facebook Graph API Explorer.

	Args:
		page_access_token : Valid Facebook Page Access Token
		page_id           : Facebook Page ID (optional — fetched automatically if blank)
		page_name         : Facebook Page Name (optional — fetched automatically if blank)

	Returns:
		dict: Result with success flag and message
	"""
	import requests

	if not page_access_token:
		frappe.throw("Page Access Token is required.")

	# ── Validate the token against Facebook Graph API ──────────────────────────
	try:
		settings_doc = frappe.get_doc("Facebook Settings")
		api_ver = getattr(settings_doc, "graph_api_version", None) or "v21.0"
		verify_url = f"https://graph.facebook.com/{api_ver}/me"
		resp = requests.get(
			verify_url,
			params={"access_token": page_access_token, "fields": "id,name"},
			timeout=15,
		)
		result = resp.json()

		if resp.status_code != 200 or "error" in result:
			error_msg = result.get("error", {}).get("message", "Invalid token")
			frappe.throw(f"Token validation failed: {error_msg}")

		# Auto-fill page_id / page_name from the API response if not supplied
		if not page_id:
			page_id = result.get("id", "")
		if not page_name:
			page_name = result.get("name", "")

	except requests.exceptions.RequestException as e:
		frappe.throw(f"Could not reach Facebook API: {str(e)}")

	# ── Save to Facebook Settings ───────────────────────────────────────────────
	settings = frappe.get_doc("Facebook Settings")
	settings.page_access_token = page_access_token
	settings.user_access_token = page_access_token   # use as user token too
	settings.page_id           = page_id
	settings.page_name         = page_name
	settings.is_connected      = 1
	settings.token_expiry      = None                 # unknown expiry for manual tokens
	settings.save(ignore_permissions=True)

	# Auto-create or update Facebook Page document
	from social_media.facebook.auth import create_or_update_facebook_page
	create_or_update_facebook_page(page_id, page_name, page_access_token)

	frappe.db.commit()

	return {
		"success"   : True,
		"message"   : f"Token saved! Connected to page: {page_name} (ID: {page_id})",
		"page_id"   : page_id,
		"page_name" : page_name,
	}
