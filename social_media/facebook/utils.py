"""
Facebook Utility Functions
Centralized utilities for Facebook Graph API integration
"""

import frappe
import requests
import json
from datetime import datetime, timedelta


def get_settings():
    """Get Facebook Settings document."""
    return frappe.get_doc("Facebook Settings")


def is_connected():
    """Check if Facebook is connected."""
    settings = get_settings()
    return bool(settings.is_connected and settings.page_access_token)


def make_graph_request(endpoint, method="GET", params=None, data=None):
    """
    Central function for all Graph API calls.
    
    Args:
        endpoint: API endpoint (e.g., '/me/accounts')
        method: HTTP method (GET, POST, DELETE)
        params: Query parameters
        data: Request body for POST requests
    
    Returns:
        dict: API response or None on error
    """
    settings = get_settings()
    
    if not settings.is_connected or not settings.page_access_token:
        frappe.log_error("Facebook not connected", "Facebook Integration")
        return None
    
    # Base URL
    base_url = "https://graph.facebook.com/v18.0"
    
    # Default params
    if params is None:
        params = {}
    
    # Add access token
    params["access_token"] = settings.page_access_token
    
    # Build URL
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, params=params, data=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, params=params, timeout=30)
        else:
            frappe.log_error(f"Invalid HTTP method: {method}", "Facebook Integration")
            return None
        
        # Parse response
        result = response.json()
        
        # Check for errors
        if response.status_code != 200 or "error" in result:
            error_msg = result.get("error", {}).get("message", "Unknown error")
            frappe.log_error(
                f"Facebook API Error: {error_msg}\nEndpoint: {endpoint}\nStatus: {response.status_code}",
                "Facebook Integration"
            )
            
            # Handle token expiration
            if response.status_code == 401:
                settings.is_connected = 0
                settings.save(ignore_permissions=True)
                frappe.msgprint("Facebook connection expired. Please reconnect.", indicator="red", alert=True)
            
            return None
        
        return result
        
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Facebook API Request Error: {str(e)}", "Facebook Integration")
        return None
    except Exception as e:
        frappe.log_error(f"Facebook API Error: {str(e)}", "Facebook Integration")
        return None


def get_user_pages():
    """Get all pages accessible by the user."""
    result = make_graph_request("/me/accounts", method="GET")
    if result and "data" in result:
        return result["data"]
    return []


def get_page_info(page_id):
    """Get information about a specific page."""
    result = make_graph_request(f"/{page_id}", method="GET")
    return result


def exchange_code_for_token(code):
    """
    Exchange authorization code for user access token.
    
    Args:
        code: Authorization code from OAuth redirect
    
    Returns:
        dict: Token information or None on error
    """
    settings = get_settings()
    
    params = {
        "client_id": settings.app_id,
        "client_secret": settings.app_secret,
        "redirect_uri": get_redirect_uri(),
        "code": code
    }
    
    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        if response.status_code != 200 or "error" in result:
            frappe.log_error(f"Token exchange failed: {result}", "Facebook Integration")
            return None
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Token exchange error: {str(e)}", "Facebook Integration")
        return None


def exchange_short_lived_token(long_lived=False):
    """
    Exchange short-lived token for long-lived token.
    
    Args:
        long_lived: If True, exchange for 60-day token
    
    Returns:
        dict: Token information or None on error
    """
    settings = get_settings()
    
    if not settings.user_access_token:
        return None
    
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": settings.app_id,
        "client_secret": settings.app_secret,
        "fb_exchange_token": settings.user_access_token
    }
    
    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        if response.status_code != 200 or "error" in result:
            frappe.log_error(f"Token refresh failed: {result}", "Facebook Integration")
            return None
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Token refresh error: {str(e)}", "Facebook Integration")
        return None


def get_redirect_uri():
    """Get the OAuth redirect URI."""
    site_url = frappe.utils.get_url()
    return f"{site_url}/api/method/social_media.facebook.auth.callback"


def save_tokens(tokens, page_info=None):
    """
    Save tokens and page information to Facebook Settings.
    
    Args:
        tokens: Dictionary with access_token, expires_in
        page_info: Optional page information
    """
    settings = get_settings()
    
    # Save tokens
    settings.user_access_token = tokens.get("access_token")
    
    # Calculate expiry
    if "expires_in" in tokens:
        expiry_days = int(tokens["expires_in"]) // (24 * 3600)
        settings.token_expiry = datetime.now() + timedelta(days=expiry_days)
    
    # Save page info if provided
    if page_info:
        settings.page_access_token = page_info.get("access_token")
        settings.page_id = page_info.get("id")
        settings.page_name = page_info.get("name")
    
    settings.is_connected = 1
    settings.save(ignore_permissions=True)


def create_post_log(reference_doctype, reference_name, post_id, message, status, error_message=None):
    """Create a Facebook Post Log entry."""
    doc = frappe.get_doc({
        "doctype": "Facebook Post Log",
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "post_id": post_id,
        "post_message": message,
        "status": status,
        "error_message": error_message
    })
    
    if status == "Posted":
        doc.posted_at = datetime.now()
    
    doc.insert(ignore_permissions=True)
    return doc.name


def create_messenger_chat(sender_id, sender_name, message, direction, customer=None):
    """Create a Facebook Messenger Chat entry."""
    doc = frappe.get_doc({
        "doctype": "Facebook Messenger Chat",
        "sender_id": sender_id,
        "sender_name": sender_name,
        "message": message,
        "direction": direction,
        "timestamp": datetime.now()
    })
    
    if customer:
        doc.customer = customer
    
    doc.insert(ignore_permissions=True)
    return doc.name


def create_facebook_lead(lead_data):
    """Create a Facebook Lead entry."""
    doc = frappe.get_doc({
        "doctype": "Facebook Lead",
        "facebook_lead_id": lead_data.get("id"),
        "lead_form_id": lead_data.get("form_id"),
        "full_name": lead_data.get("full_name", ""),
        "email": lead_data.get("email", ""),
        "phone": lead_data.get("phone", ""),
        "ad_name": lead_data.get("ad_name", ""),
        "campaign_name": lead_data.get("campaign_name", ""),
        "raw_data": json.dumps(lead_data, indent=2),
        "status": "New",
        "created_at": datetime.now()
    })
    
    doc.insert(ignore_permissions=True)
    return doc.name


def subscribe_app_to_page(page_id, app_access_token=None, callback_url=None):
    """
    Subscribe the app to a Facebook page's webhooks.

    Args:
        page_id: Facebook Page ID
        app_access_token: Page access token
        callback_url: Webhook callback URL

    Returns:
        dict: API response or None on error
    """
    data = {}
    if callback_url:
        data["callback_url"] = callback_url

    params = {}
    if app_access_token:
        params["access_token"] = app_access_token

    return make_graph_request(
        f"/{page_id}/subscribed_apps",
        method="POST",
        params=params if params else None,
        data=data if data else None
    )


def unsubscribe_app_from_page(page_id, app_access_token=None):
    """
    Unsubscribe the app from a Facebook page's webhooks.

    Args:
        page_id: Facebook Page ID
        app_access_token: Page access token

    Returns:
        dict: API response or None on error
    """
    params = {}
    if app_access_token:
        params["access_token"] = app_access_token

    return make_graph_request(
        f"/{page_id}/subscribed_apps",
        method="DELETE",
        params=params if params else None
    )


def set_greeting_text(page_id, greeting_text):
    """
    Set the Messenger greeting text for a page.

    Args:
        page_id: Facebook Page ID
        greeting_text: Greeting message text

    Returns:
        dict: API response or None on error
    """
    import json as _json
    data = {
        "greeting": _json.dumps([
            {"locale": "default", "text": greeting_text}
        ])
    }
    return make_graph_request(
        f"/{page_id}/messenger_profile",
        method="POST",
        data=data
    )


def get_subscribed_fields(page_id, access_token=None):
    """
    Get the currently subscribed webhook fields for a page.

    Args:
        page_id: Facebook Page ID
        access_token: Page access token

    Returns:
        dict: API response or None on error
    """
    params = {}
    if access_token:
        params["access_token"] = access_token

    return make_graph_request(
        f"/{page_id}/subscribed_apps",
        method="GET",
        params=params if params else None
    )


def get_page_posts(page_id, access_token=None, limit=25):
    """
    Fetch posts from a Facebook page.

    Args:
        page_id: Facebook Page ID
        access_token: Page access token
        limit: Maximum number of posts to fetch

    Returns:
        dict: API response with post data or None on error
    """
    params = {
        "limit": limit,
        "fields": "id,message,created_time,full_picture,permalink_url,shares,likes.summary(true),comments.summary(true)"
    }
    if access_token:
        params["access_token"] = access_token

    return make_graph_request(f"/{page_id}/posts", method="GET", params=params)


def create_post(page_id, message, access_token=None, link=None, picture=None, name=None, caption=None):
    """
    Create a new post on a Facebook page.

    Args:
        page_id: Facebook Page ID
        message: Post message text
        access_token: Page access token
        link: Optional URL to attach
        picture: Optional image URL
        name: Optional link name/title
        caption: Optional link caption

    Returns:
        dict: API response with post ID or None on error
    """
    data = {"message": message}
    if link:
        data["link"] = link
    if picture:
        data["picture"] = picture
    if name:
        data["name"] = name
    if caption:
        data["caption"] = caption

    params = {}
    if access_token:
        params["access_token"] = access_token

    return make_graph_request(
        f"/{page_id}/feed",
        method="POST",
        params=params if params else None,
        data=data
    )


def get_post_comments(page_id, post_id, access_token=None):
    """
    Fetch comments for a specific post.

    Args:
        page_id: Facebook Page ID (unused but kept for API consistency)
        post_id: Facebook Post ID
        access_token: Page access token

    Returns:
        dict: API response with comment data or None on error
    """
    params = {
        "fields": "id,message,from,created_time,like_count,comment_count"
    }
    if access_token:
        params["access_token"] = access_token

    return make_graph_request(f"/{post_id}/comments", method="GET", params=params)


def send_text(page_id, recipient_id, message):
    """
    Send a text message via Facebook Messenger.
    
    Args:
        page_id: Facebook page ID
        recipient_id: Recipient's PSID
        message: Message text
    
    Returns:
        dict: API response
    """
    from social_media.facebook import messenger
    
    return messenger.send_message(recipient_id, message)


def get_lead_form_details(form_id, access_token=None):
    """
    Get details of a Facebook Lead Form.
    
    Args:
        form_id: Facebook Lead Form ID
        access_token: Optional access token (uses page token if not provided)
    
    Returns:
        dict: Form details including questions and metadata
    """
    settings = get_settings()
    
    if not access_token:
        access_token = settings.page_access_token
    
    if not access_token:
        frappe.log_error("No access token available for lead form API call", "Facebook Integration")
        return None
    
    params = {
        "access_token": access_token,
        "fields": "id,name,created_time,updated_time,questions,lead_gen_data"
    }
    
    url = f"https://graph.facebook.com/v18.0/{form_id}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        if response.status_code != 200 or "error" in result:
            error_msg = result.get("error", {}).get("message", "Unknown error")
            frappe.log_error(
                f"Failed to fetch lead form details: {error_msg}\nForm ID: {form_id}",
                "Facebook Integration"
            )
            return None
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Lead form details fetch error: {str(e)}", "Facebook Integration")
        return None


def get_lead_form_leads(form_id, access_token=None, limit=100):
    """
    Get leads from a Facebook Lead Form.
    
    Args:
        form_id: Facebook Lead Form ID
        access_token: Optional access token (uses page token if not provided)
        limit: Maximum number of leads to fetch (default 100)
    
    Returns:
        dict: Lead data with pagination info
    """
    settings = get_settings()
    
    if not access_token:
        access_token = settings.page_access_token
    
    if not access_token:
        frappe.log_error("No access token available for leads API call", "Facebook Integration")
        return None
    
    params = {
        "access_token": access_token,
        "limit": limit,
        "fields": "id,created_time,field_data,ad_name,campaign_name,ad_id,campaign_id"
    }
    
    url = f"https://graph.facebook.com/v18.0/{form_id}/leads"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        if response.status_code != 200 or "error" in result:
            error_msg = result.get("error", {}).get("message", "Unknown error")
            frappe.log_error(
                f"Failed to fetch lead form leads: {error_msg}\nForm ID: {form_id}",
                "Facebook Integration"
            )
            return None
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Lead form leads fetch error: {str(e)}", "Facebook Integration")
        return None
