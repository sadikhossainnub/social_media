"""
Facebook OAuth Authentication
Handles OAuth 2.0 flow for Facebook integration
"""

import frappe
import requests
import json
from datetime import datetime, timedelta


@frappe.whitelist(allow_guest=True)
def verify_facebook_login(access_token, user_id):
	"""
	Verify a Facebook user's login status and token validity.
	
	Args:
		access_token: Facebook user access token
		user_id: Facebook user ID
	
	Returns:
		dict: Login verification result
	"""
	try:
		# Verify token with Facebook Graph API
		params = {
			"input_token": access_token,
			"access_token": access_token
		}
		
		url = "https://graph.facebook.com/v18.0/debug_token"
		response = requests.get(url, params=params, timeout=10)
		result = response.json()
		
		if response.status_code != 200:
			return {
				"status": "not_authorized",
				"message": "Token verification failed"
			}
		
		data = result.get("data", {})
		
		if data.get("is_valid"):
			return {
				"status": "connected",
				"user_id": user_id,
				"app_id": data.get("app_id"),
				"expires_at": data.get("expires_at"),
				"message": "Token verified successfully"
			}
		else:
			return {
				"status": "not_authorized",
				"message": "Token is invalid or expired"
			}
	
	except Exception as e:
		frappe.log_error(f"Token verification error: {str(e)}", "Facebook OAuth")
		return {
			"status": "error",
			"message": f"Verification failed: {str(e)}"
		}


@frappe.whitelist(allow_guest=True)

def get_oauth_url():
	"""
	Generate Facebook OAuth URL for authentication.
	
	Returns:
		str: OAuth URL for Facebook authentication
	"""
	settings = frappe.get_doc("Facebook Settings")
	
	if not settings.app_id:
		frappe.throw("Facebook App ID is not configured.")
	
	# Get redirect URI
	site_url = frappe.utils.get_url()
	redirect_uri = f"{site_url}/api/method/social_media.facebook.auth.callback"
	
	# OAuth scopes
	scopes = [
		"pages_manage_posts",
		"pages_read_engagement",
		"leads_retrieval",
		"pages_messaging",
		"public_profile"
	]
	
	# Build OAuth URL
	oauth_url = (
		f"https://www.facebook.com/v18.0/dialog/oauth"
		f"?client_id={settings.app_id}"
		f"&redirect_uri={redirect_uri}"
		f"&scope={','.join(scopes)}"
		f"&response_type=code"
	)
	
	return oauth_url


@frappe.whitelist(allow_guest=True)
def callback():
	"""
	Handle OAuth callback from Facebook.
	This is called after user authenticates with Facebook.
	"""
	import frappe.oauth
	
	code = frappe.request.args.get("code")
	error = frappe.request.args.get("error")
	
	frappe.log_error(f"OAuth Callback - Code: {bool(code)}, Error: {error}", "Facebook OAuth")
	
	if error:
		frappe.log_error(f"Facebook OAuth Error: {error}", "Facebook OAuth")
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/app/facebook-settings?oauth=error"
		return
	
	if not code:
		frappe.log_error("No authorization code received from Facebook", "Facebook OAuth")
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/app/facebook-settings?oauth=no_code"
		return
	
	try:
		# Exchange code for short-lived user token
		frappe.log_error(f"Exchanging code for token...", "Facebook OAuth")
		tokens = exchange_code_for_token(code)
		
		if not tokens:
			frappe.log_error("Token exchange failed - response was None", "Facebook OAuth")
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/app/facebook-settings?oauth=token_error"
			return
		
		frappe.log_error(f"Short-lived token received: {list(tokens.keys())}", "Facebook OAuth")
		
		# Exchange short-lived for long-lived token (60 days)
		frappe.log_error("Exchanging for long-lived token...", "Facebook OAuth")
		long_lived_tokens = exchange_short_lived_token(tokens.get("access_token"))
		
		if long_lived_tokens:
			frappe.log_error("Long-lived token obtained", "Facebook OAuth")
			tokens = long_lived_tokens
		else:
			frappe.log_error("Long-lived token exchange failed, using short-lived", "Facebook OAuth")
		
		# Get user pages
		frappe.log_error("Fetching user pages...", "Facebook OAuth")
		pages = get_user_pages(tokens.get("access_token"))
		frappe.log_error(f"Pages fetched: {len(pages) if pages else 0} pages", "Facebook OAuth")
		
		if not pages:
			frappe.log_error("No pages found for authenticated user", "Facebook OAuth")
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/app/facebook-settings?oauth=no_pages"
			return
		
		# Auto-select page (first one if multiple)
		selected_page = pages[0]
		frappe.log_error(f"Selected page: {selected_page.get('name')} (ID: {selected_page.get('id')})", "Facebook OAuth")
		
		# Auto-create/update all fetched pages
		for p in pages:
			create_or_update_facebook_page(p.get("id"), p.get("name"), p.get("access_token"))

		# Save tokens and page info
		frappe.log_error("Saving tokens to Facebook Settings...", "Facebook OAuth")
		save_tokens(tokens, selected_page)
		frappe.log_error("Tokens saved successfully!", "Facebook OAuth")
		
		# Redirect with success
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/app/facebook-settings?oauth=success"
		
	except Exception as e:
		frappe.log_error(f"OAuth callback exception: {str(e)}\n{frappe.get_traceback()}", "Facebook OAuth")
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/app/facebook-settings?oauth=error"


def exchange_code_for_token(code):
	"""
	Exchange authorization code for user access token.
	
	Args:
		code: Authorization code from OAuth redirect
	
	Returns:
		dict: Token information or None on error
	"""
	settings = frappe.get_doc("Facebook Settings")
	
	site_url = frappe.utils.get_url()
	redirect_uri = f"{site_url}/api/method/social_media.facebook.auth.callback"
	
	# Use get_password() - Password fields return empty string via normal attribute access
	app_secret = settings.get_password("app_secret")
	
	frappe.log_error(f"Token Exchange - App ID: {settings.app_id[:5]}..., Redirect URI: {redirect_uri}", "Facebook OAuth")
	
	params = {
		"client_id": settings.app_id,
		"client_secret": app_secret,
		"redirect_uri": redirect_uri,
		"code": code
	}
	
	url = "https://graph.facebook.com/v18.0/oauth/access_token"
	
	try:
		frappe.log_error(f"Making request to {url}", "Facebook OAuth")
		response = requests.get(url, params=params, timeout=30)
		result = response.json()
		
		frappe.log_error(f"Token Exchange Response - Status: {response.status_code}, Keys: {list(result.keys())}", "Facebook OAuth")
		
		if response.status_code != 200 or "error" in result:
			error_info = result.get("error", {})
			frappe.log_error(f"Token exchange failed - Error: {error_info}", "Facebook OAuth")
			return None
		
		frappe.log_error(f"Token exchange successful - Access Token length: {len(result.get('access_token', ''))}", "Facebook OAuth")
		return result
		
	except Exception as e:
		frappe.log_error(f"Token exchange exception: {str(e)}\n{frappe.get_traceback()}", "Facebook OAuth")
		return None


def exchange_short_lived_token(user_token):
	"""
	Exchange short-lived token for long-lived token (60 days).
	
	Args:
		user_token: Short-lived user access token
	
	Returns:
		dict: Long-lived token information or None on error
	"""
	settings = frappe.get_doc("Facebook Settings")
	
	# Use get_password() - Password fields return empty string via normal attribute access
	app_secret = settings.get_password("app_secret")
	
	params = {
		"grant_type": "fb_exchange_token",
		"client_id": settings.app_id,
		"client_secret": app_secret,
		"fb_exchange_token": user_token
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


def get_user_pages(access_token):
	"""
	Get all pages accessible by the user.
	
	Args:
		access_token: User access token
	
	Returns:
		list: List of page information
	"""
	params = {
		"access_token": access_token,
		"fields": "id,name,access_token"
	}
	
	url = "https://graph.facebook.com/v18.0/me/accounts"
	
	try:
		frappe.log_error(f"Fetching pages from {url}", "Facebook OAuth")
		response = requests.get(url, params=params, timeout=30)
		result = response.json()
		
		frappe.log_error(f"Pages Response - Status: {response.status_code}, Keys: {list(result.keys())}", "Facebook OAuth")
		
		if response.status_code != 200 or "error" in result:
			error_info = result.get("error", {})
			frappe.log_error(f"Pages fetch failed - Error: {error_info}", "Facebook OAuth")
			return []
		
		pages = result.get("data", [])
		frappe.log_error(f"Pages fetched successfully - Count: {len(pages)}", "Facebook OAuth")
		for idx, page in enumerate(pages):
			frappe.log_error(f"Page {idx}: {page.get('name')} (ID: {page.get('id')})", "Facebook OAuth")
		
		return pages
		
	except Exception as e:
		frappe.log_error(f"Pages fetch exception: {str(e)}\n{frappe.get_traceback()}", "Facebook OAuth")
		return []


def save_tokens(tokens, page_info=None):
	"""
	Save tokens and page information to Facebook Settings.
	
	Args:
		tokens: Dictionary with access_token, expires_in
		page_info: Optional page information
	"""
	settings = frappe.get_doc("Facebook Settings")
	
	# Save tokens
	settings.user_access_token = tokens.get("access_token")
	
	# Calculate expiry - ensure proper ISO format datetime
	if "expires_in" in tokens:
		try:
			expiry_seconds = int(tokens["expires_in"])
			expiry_datetime = datetime.now() + timedelta(seconds=expiry_seconds)
			# Format as ISO 8601 string to ensure compatibility
			settings.token_expiry = expiry_datetime.strftime("%Y-%m-%d %H:%M:%S")
		except (ValueError, TypeError) as e:
			frappe.log_error(f"Error calculating token expiry: {str(e)}", "Facebook OAuth")
			settings.token_expiry = None
	else:
		settings.token_expiry = None
	
	# Save page info if provided
	if page_info:
		settings.page_access_token = page_info.get("access_token")
		settings.page_id = page_info.get("id")
		settings.page_name = page_info.get("name")
		create_or_update_facebook_page(
			page_info.get("id"),
			page_info.get("name"),
			page_info.get("access_token")
		)
	
	settings.is_connected = 1
	settings.save(ignore_permissions=True)


def create_or_update_facebook_page(page_id, page_name, access_token):
	"""Auto-create or update Facebook Page document to sync it with Facebook settings/explorer."""
	if not page_id:
		return
	
	try:
		if frappe.db.exists("Facebook Page", page_id):
			page_doc = frappe.get_doc("Facebook Page", page_id)
			page_doc.page_name = page_name
			page_doc.access_token = access_token
			page_doc.status = "Active"
			page_doc.save(ignore_permissions=True)
			frappe.log_error(f"Updated Facebook Page document: {page_id}", "Facebook OAuth")
		else:
			page_doc = frappe.new_doc("Facebook Page")
			page_doc.page_id = page_id
			page_doc.page_name = page_name
			page_doc.access_token = access_token
			page_doc.status = "Active"
			page_doc.insert(ignore_permissions=True)
			frappe.log_error(f"Created new Facebook Page document: {page_id}", "Facebook OAuth")
	except Exception as e:
		frappe.log_error(f"Error in create_or_update_facebook_page: {str(e)}\n{frappe.get_traceback()}", "Facebook OAuth")


@frappe.whitelist()
def disconnect():
	"""
	Disconnect from Facebook.
	Clears all tokens and connection status.
	"""
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
def get_connection_status():
	"""
	Get current connection status.
	
	Returns:
		dict: Connection status information
	"""
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
	"""
	Refresh the access token if it's about to expire.
	
	Returns:
		dict: Refresh result
	"""
	settings = frappe.get_doc("Facebook Settings")
	
	if not settings.user_access_token:
		return {"success": False, "message": "No user token found"}
	
	# Check if token is expiring soon (within 7 days)
	if settings.token_expiry:
		try:
			# Parse token_expiry if it's a string
			if isinstance(settings.token_expiry, str):
				token_expiry_dt = datetime.strptime(settings.token_expiry, "%Y-%m-%d %H:%M:%S")
			else:
				token_expiry_dt = settings.token_expiry
			
			days_until_expiry = (token_expiry_dt - datetime.now()).days
			if days_until_expiry > 7:
				return {
					"success": True,
					"message": f"Token valid for {days_until_expiry} more days"
				}
		except (ValueError, TypeError) as e:
			frappe.log_error(f"Error parsing token expiry: {str(e)}", "Facebook OAuth")
	
	# Refresh token
	tokens = exchange_short_lived_token(settings.user_access_token)
	
	if not tokens:
		return {"success": False, "message": "Failed to refresh token"}
	
	# Update settings with proper datetime formatting
	settings.user_access_token = tokens.get("access_token")
	
	if "expires_in" in tokens:
		try:
			expiry_seconds = int(tokens["expires_in"])
			expiry_datetime = datetime.now() + timedelta(seconds=expiry_seconds)
			# Format as ISO 8601 string
			settings.token_expiry = expiry_datetime.strftime("%Y-%m-%d %H:%M:%S")
		except (ValueError, TypeError) as e:
			frappe.log_error(f"Error calculating token expiry: {str(e)}", "Facebook OAuth")
			settings.token_expiry = None
	
	settings.save(ignore_permissions=True)
	
	return {
		"success": True,
		"message": "Token refreshed successfully",
		"expires_in": tokens.get("expires_in")
	}
