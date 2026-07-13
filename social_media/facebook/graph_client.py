"""
Facebook Graph API Client
Central service class for all Facebook Graph API interactions.
Handles token management, rate limiting, error logging, and retries.
"""

import frappe
import requests
import time
import json
import hashlib
import hmac
from datetime import datetime, timedelta


class FacebookGraphClient:
	"""
	Centralized Facebook Graph API client.

	Usage:
		client = FacebookGraphClient(page_id="123456")
		result = client.get("/me/posts", params={"fields": "id,message"})

		# Or without page_id (uses default from settings):
		client = FacebookGraphClient()
		result = client.post(f"/{page_id}/feed", data={"message": "Hello!"})
	"""

	BASE_URL = "https://graph.facebook.com"
	MAX_RETRIES = 3
	RETRY_BACKOFF_FACTOR = 2  # seconds

	def __init__(self, page_id=None, use_user_token=False):
		"""
		Initialize the Graph API client.

		Args:
			page_id: Facebook Page ID. If None, uses default from Facebook Settings.
			use_user_token: If True, uses user access token instead of page token.
		"""
		self._settings = None
		self._page_doc = None
		self._page_id = page_id
		self._use_user_token = use_user_token
		self._api_version = None
		self._access_token = None

	@property
	def settings(self):
		"""Lazy-load Facebook Settings singleton."""
		if self._settings is None:
			self._settings = frappe.get_single("Facebook Settings")
		return self._settings

	@property
	def api_version(self):
		"""Get configured Graph API version."""
		if self._api_version is None:
			self._api_version = getattr(self.settings, "graph_api_version", None) or "v21.0"
		return self._api_version

	@property
	def base_url(self):
		"""Full base URL with API version."""
		return f"{self.BASE_URL}/{self.api_version}"

	@property
	def page_id(self):
		"""Resolve page ID."""
		if self._page_id:
			return self._page_id
		return self.settings.page_id

	@property
	def access_token(self):
		"""
		Resolve the appropriate access token.
		Priority: page-specific token → settings page token → user token.
		"""
		if self._access_token:
			return self._access_token

		if self._use_user_token:
			token = self.settings.get_password("user_access_token", raise_exception=False)
			if token:
				self._access_token = token
				return self._access_token

		# Try page-specific token from Facebook Page doctype
		if self._page_id:
			try:
				page_doc = frappe.get_doc("Facebook Page", self._page_id)
				token = page_doc.get_password("access_token", raise_exception=False)
				if token:
					self._access_token = token
					return self._access_token
			except frappe.DoesNotExistError:
				pass

		# Fallback to settings page access token
		token = self.settings.get_password("page_access_token", raise_exception=False)
		if token:
			self._access_token = token
		return self._access_token

	def _build_url(self, endpoint):
		"""Build full API URL from endpoint."""
		if endpoint.startswith("http"):
			return endpoint
		if not endpoint.startswith("/"):
			endpoint = f"/{endpoint}"
		return f"{self.base_url}{endpoint}"

	def _log_api_call(self, url, method, params, data, response_status, response_body, error_message, duration_ms):
		"""Log API call to Facebook API Log doctype."""
		try:
			# Sanitize params — remove access_token from logged data
			safe_params = {k: v for k, v in (params or {}).items() if k != "access_token"}

			frappe.get_doc({
				"doctype": "Facebook API Log",
				"request_url": url,
				"method": method,
				"request_params": json.dumps(safe_params, default=str) if safe_params else None,
				"request_body": json.dumps(data, default=str) if data else None,
				"response_status": response_status,
				"response_body": json.dumps(response_body, default=str)[:10000] if response_body else None,
				"error_message": error_message,
				"duration_ms": duration_ms,
				"page": self._page_id,
				"user": frappe.session.user,
				"timestamp": datetime.now()
			}).insert(ignore_permissions=True)
		except Exception:
			# Never let logging failures break API calls
			pass

	def _handle_rate_limit(self, response):
		"""
		Check Facebook rate limit headers and back off if needed.
		Headers: X-App-Usage, X-Business-Use-Case-Usage
		"""
		app_usage = response.headers.get("X-App-Usage")
		if app_usage:
			try:
				usage = json.loads(app_usage)
				# If any usage metric > 80%, sleep briefly
				call_count = usage.get("call_count", 0)
				total_cputime = usage.get("total_cputime", 0)
				total_time = usage.get("total_time", 0)

				if max(call_count, total_cputime, total_time) > 80:
					wait_time = min(max(call_count, total_cputime, total_time) - 60, 30)
					frappe.log_error(
						f"Facebook API rate limit approaching: call={call_count}%, cpu={total_cputime}%, time={total_time}%. Waiting {wait_time}s.",
						"Facebook Rate Limit"
					)
					time.sleep(max(wait_time, 1))
			except (json.JSONDecodeError, TypeError):
				pass

	def request(self, method, endpoint, params=None, data=None, files=None, timeout=30):
		"""
		Make a Graph API request with retry logic, rate limit handling, and logging.

		Args:
			method: HTTP method (GET, POST, DELETE)
			endpoint: API endpoint (e.g., '/me/accounts', '/{page_id}/feed')
			params: Query parameters dict
			data: Request body dict (for POST)
			files: File uploads dict
			timeout: Request timeout in seconds

		Returns:
			dict: Parsed JSON response or None on error

		Raises:
			FacebookAPIError: On non-retryable errors
		"""
		if not self.access_token:
			frappe.log_error("No access token available for Facebook API call", "Facebook Integration")
			return None

		url = self._build_url(endpoint)

		if params is None:
			params = {}
		params["access_token"] = self.access_token

		last_error = None
		for attempt in range(self.MAX_RETRIES):
			start_time = time.time()
			response_status = None
			response_body = None
			error_message = None

			try:
				if method.upper() == "GET":
					response = requests.get(url, params=params, timeout=timeout)
				elif method.upper() == "POST":
					if files:
						response = requests.post(url, params=params, data=data, files=files, timeout=timeout)
					else:
						response = requests.post(url, params=params, json=data, timeout=timeout)
				elif method.upper() == "DELETE":
					response = requests.delete(url, params=params, timeout=timeout)
				else:
					frappe.log_error(f"Invalid HTTP method: {method}", "Facebook Integration")
					return None

				duration_ms = (time.time() - start_time) * 1000
				response_status = response.status_code

				# Handle rate limiting
				self._handle_rate_limit(response)

				# Parse response
				try:
					response_body = response.json()
				except (json.JSONDecodeError, ValueError):
					response_body = {"raw": response.text[:2000]}

				# Check for errors
				if response.status_code == 200 and "error" not in response_body:
					# Success — log and return
					self._log_api_call(url, method, params, data, response_status, response_body, None, duration_ms)
					return response_body

				# Handle Facebook API errors
				fb_error = response_body.get("error", {})
				error_code = fb_error.get("code", 0)
				error_message = fb_error.get("message", f"HTTP {response.status_code}")

				# Non-retryable errors
				if error_code in (10, 100, 190, 200, 803):
					# 10: API permission denied
					# 100: Invalid parameter
					# 190: Invalid/expired token
					# 200: Permission error
					# 803: Some objects not found
					if error_code == 190:
						# Token expired — mark as disconnected
						try:
							self.settings.is_connected = 0
							self.settings.save(ignore_permissions=True)
						except Exception:
							pass
						frappe.log_error(
							f"Facebook token expired: {error_message}",
							"Facebook Token Expired"
						)

					self._log_api_call(url, method, params, data, response_status, response_body, error_message, duration_ms)
					return None

				# Retryable errors (rate limit, server error)
				if response.status_code in (429, 500, 502, 503) or error_code in (1, 2, 4, 17, 32, 613):
					last_error = error_message
					wait = self.RETRY_BACKOFF_FACTOR ** attempt
					time.sleep(wait)
					continue

				# Other errors — don't retry
				self._log_api_call(url, method, params, data, response_status, response_body, error_message, duration_ms)
				return None

			except requests.exceptions.Timeout:
				duration_ms = (time.time() - start_time) * 1000
				last_error = f"Request timed out after {timeout}s"
				self._log_api_call(url, method, params, data, 0, None, last_error, duration_ms)
				if attempt < self.MAX_RETRIES - 1:
					time.sleep(self.RETRY_BACKOFF_FACTOR ** attempt)
					continue
				return None

			except requests.exceptions.ConnectionError as e:
				duration_ms = (time.time() - start_time) * 1000
				last_error = f"Connection error: {str(e)}"
				self._log_api_call(url, method, params, data, 0, None, last_error, duration_ms)
				if attempt < self.MAX_RETRIES - 1:
					time.sleep(self.RETRY_BACKOFF_FACTOR ** attempt)
					continue
				return None

			except Exception as e:
				duration_ms = (time.time() - start_time) * 1000
				last_error = f"Unexpected error: {str(e)}"
				self._log_api_call(url, method, params, data, 0, None, last_error, duration_ms)
				frappe.log_error(f"Facebook API error: {str(e)}\n{frappe.get_traceback()}", "Facebook Integration")
				return None

		# All retries exhausted
		frappe.log_error(
			f"Facebook API call failed after {self.MAX_RETRIES} retries: {last_error}\nEndpoint: {endpoint}",
			"Facebook Integration"
		)
		return None

	def get(self, endpoint, params=None, timeout=30):
		"""Make a GET request."""
		return self.request("GET", endpoint, params=params, timeout=timeout)

	def post(self, endpoint, data=None, params=None, files=None, timeout=30):
		"""Make a POST request."""
		return self.request("POST", endpoint, params=params, data=data, files=files, timeout=timeout)

	def delete(self, endpoint, params=None, timeout=30):
		"""Make a DELETE request."""
		return self.request("DELETE", endpoint, params=params, timeout=timeout)

	# ── Page Methods ──────────────────────────────────────────────────

	def get_page_info(self, page_id=None, fields=None):
		"""Get page information."""
		pid = page_id or self.page_id
		if not fields:
			fields = "id,name,category,fan_count,followers_count,cover,picture.type(large)"
		return self.get(f"/{pid}", params={"fields": fields})

	def get_page_posts(self, page_id=None, limit=25, fields=None):
		"""Get posts from a page."""
		pid = page_id or self.page_id
		if not fields:
			fields = "id,message,created_time,full_picture,permalink_url,shares,type,likes.summary(true),comments.summary(true)"
		return self.get(f"/{pid}/posts", params={"fields": fields, "limit": limit})

	def create_page_post(self, message, page_id=None, link=None, image_url=None):
		"""Create a text/link post on a page."""
		pid = page_id or self.page_id
		data = {"message": message}
		if link:
			data["link"] = link
		if image_url:
			data["picture"] = image_url
		return self.post(f"/{pid}/feed", data=data)

	def create_photo_post(self, message, image_url=None, image_file=None, page_id=None):
		"""Create a photo post on a page."""
		pid = page_id or self.page_id
		data = {"message": message}
		if image_url:
			data["url"] = image_url
			return self.post(f"/{pid}/photos", data=data)
		elif image_file:
			files = {"source": image_file}
			return self.post(f"/{pid}/photos", data={"message": message}, files=files)
		return None

	def create_multi_photo_post(self, message, photo_ids, page_id=None):
		"""
		Create a multi-photo (carousel) post.
		First upload photos unpublished, then create a post referencing them.
		"""
		pid = page_id or self.page_id
		data = {"message": message}
		for i, photo_id in enumerate(photo_ids):
			data[f"attached_media[{i}]"] = json.dumps({"media_fbid": photo_id})
		return self.post(f"/{pid}/feed", data=data)

	def upload_unpublished_photo(self, image_url=None, image_file=None, page_id=None):
		"""Upload a photo as unpublished (for multi-photo posts)."""
		pid = page_id or self.page_id
		data = {"published": "false"}
		if image_url:
			data["url"] = image_url
			return self.post(f"/{pid}/photos", data=data)
		elif image_file:
			files = {"source": image_file}
			return self.post(f"/{pid}/photos", data=data, files=files)
		return None

	def create_video_post(self, message, video_url, page_id=None):
		"""Create a video post on a page."""
		pid = page_id or self.page_id
		data = {"description": message, "file_url": video_url}
		return self.post(f"/{pid}/videos", data=data)

	def delete_post(self, post_id):
		"""Delete a post."""
		return self.delete(f"/{post_id}")

	# ── Comment Methods ───────────────────────────────────────────────

	def get_post_comments(self, post_id, limit=100, fields=None):
		"""Get comments on a post."""
		if not fields:
			fields = "id,message,from,created_time,like_count,comment_count,attachment"
		return self.get(f"/{post_id}/comments", params={"fields": fields, "limit": limit})

	def reply_to_comment(self, comment_id, message):
		"""Reply to a comment."""
		return self.post(f"/{comment_id}/comments", data={"message": message})

	def hide_comment(self, comment_id):
		"""Hide a comment."""
		return self.post(f"/{comment_id}", data={"is_hidden": True})

	def unhide_comment(self, comment_id):
		"""Unhide a comment."""
		return self.post(f"/{comment_id}", data={"is_hidden": False})

	def delete_comment(self, comment_id):
		"""Delete a comment."""
		return self.delete(f"/{comment_id}")

	# ── Messenger Methods ─────────────────────────────────────────────

	def send_message(self, recipient_id, message_text, quick_replies=None):
		"""Send a Messenger message."""
		data = {
			"recipient": {"id": recipient_id},
			"message": {"text": message_text}
		}
		if quick_replies:
			data["message"]["quick_replies"] = quick_replies
		return self.post("/me/messages", data=data)

	def send_typing_indicator(self, recipient_id, action="typing_on"):
		"""Show/hide typing indicator."""
		data = {
			"recipient": {"id": recipient_id},
			"sender_action": action
		}
		return self.post("/me/messages", data=data)

	def get_conversations(self, page_id=None, limit=25, fields=None):
		"""Get Messenger conversations."""
		pid = page_id or self.page_id
		if not fields:
			fields = "id,updated_time,participants,messages.limit(1){message,from,created_time},unread_count"
		return self.get(f"/{pid}/conversations", params={"fields": fields, "limit": limit})

	def get_conversation_messages(self, conversation_id, limit=50, fields=None):
		"""Get messages in a conversation."""
		if not fields:
			fields = "id,message,from,to,created_time,attachments"
		return self.get(f"/{conversation_id}/messages", params={"fields": fields, "limit": limit})

	# ── Insights Methods ──────────────────────────────────────────────

	def get_page_insights(self, page_id=None, metrics=None, period="day", since=None, until=None):
		"""
		Get page-level insights.

		Args:
			metrics: List of metric names. Defaults to common engagement metrics.
			period: Aggregation period (day, week, days_28)
			since: Start date (unix timestamp or YYYY-MM-DD)
			until: End date (unix timestamp or YYYY-MM-DD)
		"""
		pid = page_id or self.page_id
		if not metrics:
			metrics = [
				"page_impressions",
				"page_engaged_users",
				"page_fans",
				"page_fan_adds",
				"page_views_total",
				"page_post_engagements",
				"page_video_views"
			]

		params = {
			"metric": ",".join(metrics),
			"period": period
		}
		if since:
			params["since"] = since
		if until:
			params["until"] = until

		return self.get(f"/{pid}/insights", params=params)

	def get_post_insights(self, post_id, metrics=None):
		"""Get insights for a specific post."""
		if not metrics:
			metrics = [
				"post_impressions",
				"post_engaged_users",
				"post_clicks",
				"post_reactions_by_type_total"
			]
		return self.get(f"/{post_id}/insights", params={"metric": ",".join(metrics)})

	# ── Lead Methods ──────────────────────────────────────────────────

	def get_lead_forms(self, page_id=None):
		"""Get lead forms for a page."""
		pid = page_id or self.page_id
		return self.get(f"/{pid}/leadgen_forms", params={"fields": "id,name,status,created_time"})

	def get_lead_data(self, lead_id):
		"""Get full lead data."""
		return self.get(
			f"/{lead_id}",
			params={"fields": "id,form_id,created_time,field_data,ad_id,ad_name,campaign_id,campaign_name"}
		)

	def get_form_leads(self, form_id, limit=100):
		"""Get leads from a specific form."""
		return self.get(
			f"/{form_id}/leads",
			params={
				"fields": "id,created_time,field_data,ad_name,campaign_name,ad_id,campaign_id",
				"limit": limit
			}
		)

	# ── Ads / Marketing Methods ───────────────────────────────────────

	def get_ad_accounts(self, user_id="me"):
		"""Get ad accounts for the user."""
		return self.get(f"/{user_id}/adaccounts", params={"fields": "id,name,account_status,currency,timezone_name"})

	def get_campaigns(self, ad_account_id, limit=50):
		"""Get campaigns for an ad account."""
		return self.get(
			f"/{ad_account_id}/campaigns",
			params={
				"fields": "id,name,objective,status,daily_budget,lifetime_budget,start_time,stop_time",
				"limit": limit
			}
		)

	def get_campaign_insights(self, campaign_id, date_preset="last_30d"):
		"""Get insights for a campaign."""
		return self.get(
			f"/{campaign_id}/insights",
			params={
				"fields": "impressions,clicks,spend,reach,cpc,cpm,ctr",
				"date_preset": date_preset
			}
		)

	def update_campaign_status(self, campaign_id, status):
		"""Update campaign status (ACTIVE, PAUSED)."""
		return self.post(f"/{campaign_id}", data={"status": status})

	# ── Webhook Signature Verification ────────────────────────────────

	@staticmethod
	def verify_webhook_signature(payload_body, signature_header, app_secret):
		"""
		Verify X-Hub-Signature-256 header from Facebook webhook.

		Args:
			payload_body: Raw request body (bytes)
			signature_header: Value of X-Hub-Signature-256 header
			app_secret: Facebook App Secret

		Returns:
			bool: True if signature is valid
		"""
		if not signature_header:
			return False

		try:
			# Signature format: sha256=<hash>
			parts = signature_header.split("=", 1)
			if len(parts) != 2 or parts[0] != "sha256":
				return False

			expected_signature = parts[1]

			# Compute HMAC-SHA256
			computed_hash = hmac.new(
				app_secret.encode("utf-8"),
				msg=payload_body if isinstance(payload_body, bytes) else payload_body.encode("utf-8"),
				digestmod=hashlib.sha256
			).hexdigest()

			return hmac.compare_digest(computed_hash, expected_signature)

		except Exception:
			return False

	# ── User/Page Discovery ──────────────────────────────────────────

	def get_user_pages(self):
		"""Get all pages accessible by the authenticated user (uses user token)."""
		client = FacebookGraphClient(use_user_token=True)
		return client.get("/me/accounts", params={"fields": "id,name,access_token,category,fan_count"})

	def subscribe_page_to_app(self, page_id=None):
		"""Subscribe a page to the app's webhook."""
		pid = page_id or self.page_id
		return self.post(
			f"/{pid}/subscribed_apps",
			data={
				"subscribed_fields": "messages,messaging_postbacks,message_deliveries,message_reads,feed,leadgen"
			}
		)

	def unsubscribe_page_from_app(self, page_id=None):
		"""Unsubscribe a page from the app's webhook."""
		pid = page_id or self.page_id
		return self.delete(f"/{pid}/subscribed_apps")
