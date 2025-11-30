import frappe
from social_media.connectors.base.connector import BaseConnector
from typing import Dict, List, Any
import json


class FacebookConnector(BaseConnector):
	"""Facebook Graph API connector"""
	
	BASE_URL = "https://graph.facebook.com/v18.0"
	
	def publish_post(self, post_doc) -> Dict[str, Any]:
		"""Publish post to Facebook page"""
		try:
			# Upload media first if attachments exist
			media_ids = []
			for attachment in post_doc.attachments:
				if attachment.attachment_type in ["Image", "Video"]:
					media_id = self._upload_media(attachment)
					if media_id:
						media_ids.append(media_id)
			
			# Create post payload
			payload = {
				"message": post_doc.content,
				"access_token": self.account.get_password("oauth_access_token")
			}
			
			if media_ids:
				if len(media_ids) == 1:
					payload["object_attachment"] = media_ids[0]
				else:
					payload["attached_media"] = [{"media_fbid": mid} for mid in media_ids]
			
			# Publish to page
			page_id = self.channel.account_id
			url = f"{self.BASE_URL}/{page_id}/feed"
			
			response = self.make_request("POST", url, json=payload)
			
			if response.status_code == 200:
				data = response.json()
				return {
					"success": True,
					"post_id": data.get("id"),
					"post_url": f"https://facebook.com/{data.get('id')}"
				}
			else:
				return {
					"success": False,
					"error": response.text
				}
				
		except Exception as e:
			frappe.log_error(f"Facebook publish error: {str(e)}")
			return {"success": False, "error": str(e)}
	
	def schedule_post(self, post_doc, scheduled_time) -> Dict[str, Any]:
		"""Schedule Facebook post"""
		# Facebook doesn't support native scheduling via API
		# Use Frappe's scheduler instead
		frappe.enqueue(
			"social_media.connectors.meta.facebook.publish_scheduled_post",
			post_id=post_doc.name,
			queue="long",
			at_time=scheduled_time
		)
		return {"success": True, "scheduled": True}
	
	def fetch_messages(self, since=None) -> List[Dict]:
		"""Fetch page messages and comments"""
		messages = []
		
		try:
			# Fetch page conversations
			page_id = self.channel.account_id
			url = f"{self.BASE_URL}/{page_id}/conversations"
			
			params = {
				"access_token": self.account.get_password("oauth_access_token"),
				"fields": "id,updated_time,message_count,participants"
			}
			
			if since:
				params["since"] = since
			
			response = self.make_request("GET", url, params=params)
			
			if response.status_code == 200:
				data = response.json()
				for conversation in data.get("data", []):
					# Fetch messages for each conversation
					conv_messages = self._fetch_conversation_messages(conversation["id"])
					messages.extend(conv_messages)
			
			return messages
			
		except Exception as e:
			frappe.log_error(f"Facebook fetch messages error: {str(e)}")
			return []
	
	def process_webhook(self, event_data) -> Dict[str, Any]:
		"""Process Facebook webhook event"""
		try:
			entry = event_data.get("entry", [{}])[0]
			changes = entry.get("changes", [])
			
			for change in changes:
				field = change.get("field")
				value = change.get("value", {})
				
				if field == "messages":
					self._process_message_event(value)
				elif field == "feed":
					self._process_feed_event(value)
			
			return {"success": True}
			
		except Exception as e:
			frappe.log_error(f"Facebook webhook error: {str(e)}")
			return {"success": False, "error": str(e)}
	
	def get_analytics(self, post_id=None, date_range=None) -> Dict[str, Any]:
		"""Get Facebook page analytics"""
		try:
			page_id = self.channel.account_id
			
			if post_id:
				# Get specific post insights
				url = f"{self.BASE_URL}/{post_id}/insights"
				metrics = ["post_impressions", "post_engaged_users", "post_clicks"]
			else:
				# Get page insights
				url = f"{self.BASE_URL}/{page_id}/insights"
				metrics = ["page_impressions", "page_engaged_users", "page_fans"]
			
			params = {
				"metric": ",".join(metrics),
				"access_token": self.account.get_password("oauth_access_token")
			}
			
			if date_range:
				params.update(date_range)
			
			response = self.make_request("GET", url, params=params)
			
			if response.status_code == 200:
				return {"success": True, "data": response.json()}
			else:
				return {"success": False, "error": response.text}
				
		except Exception as e:
			frappe.log_error(f"Facebook analytics error: {str(e)}")
			return {"success": False, "error": str(e)}
	
	def _refresh_oauth_token(self) -> bool:
		"""Refresh Facebook access token"""
		try:
			url = f"{self.BASE_URL}/oauth/access_token"
			params = {
				"grant_type": "fb_exchange_token",
				"client_id": self.account.app_id,
				"client_secret": self.account.get_password("app_secret"),
				"fb_exchange_token": self.account.get_password("oauth_access_token")
			}
			
			response = requests.get(url, params=params)
			
			if response.status_code == 200:
				data = response.json()
				self.account.oauth_access_token = data["access_token"]
				self.account.expires_on = frappe.utils.add_days(frappe.utils.now(), 60)
				self.account.save()
				return True
			
			return False
			
		except Exception as e:
			frappe.log_error(f"Facebook token refresh error: {str(e)}")
			return False
	
	def _get_auth_headers(self) -> Dict[str, str]:
		"""Get Facebook auth headers"""
		return {
			"Authorization": f"Bearer {self.account.get_password('oauth_access_token')}"
		}
	
	def _upload_media(self, attachment) -> str:
		"""Upload media to Facebook"""
		try:
			page_id = self.channel.account_id
			url = f"{self.BASE_URL}/{page_id}/photos"
			
			files = {"source": ("image.jpg", attachment.file_url)}
			data = {
				"access_token": self.account.get_password("oauth_access_token"),
				"published": "false"
			}
			
			response = requests.post(url, files=files, data=data)
			
			if response.status_code == 200:
				return response.json().get("id")
			
			return None
			
		except Exception as e:
			frappe.log_error(f"Facebook media upload error: {str(e)}")
			return None
	
	def _fetch_conversation_messages(self, conversation_id) -> List[Dict]:
		"""Fetch messages for a conversation"""
		try:
			url = f"{self.BASE_URL}/{conversation_id}/messages"
			params = {
				"access_token": self.account.get_password("oauth_access_token"),
				"fields": "id,created_time,from,to,message,attachments"
			}
			
			response = self.make_request("GET", url, params=params)
			
			if response.status_code == 200:
				return response.json().get("data", [])
			
			return []
			
		except Exception as e:
			frappe.log_error(f"Facebook conversation messages error: {str(e)}")
			return []
	
	def _process_message_event(self, value):
		"""Process incoming message webhook"""
		# Create or update conversation and message records
		pass
	
	def _process_feed_event(self, value):
		"""Process feed webhook (comments, reactions)"""
		# Process comments and reactions on posts
		pass


@frappe.whitelist()
def publish_scheduled_post(post_id):
	"""Background job to publish scheduled Facebook post"""
	post_doc = frappe.get_doc("Social Post", post_id)
	
	# Get Facebook account for the post
	for platform in post_doc.platforms:
		if platform.channel and "Facebook" in platform.channel:
			channel_doc = frappe.get_doc("Social Media Channel", platform.channel)
			account_doc = frappe.get_doc("Social Account", {"channel": channel_doc.name})
			
			connector = FacebookConnector(account_doc)
			result = connector.publish_post(post_doc)
			
			if result["success"]:
				platform.status = "Published"
				platform.platform_post_id = result["post_id"]
				platform.post_url = result["post_url"]
				platform.published_at = frappe.utils.now()
				post_doc.status = "Published"
				post_doc.published_on = frappe.utils.now()
			else:
				platform.status = "Failed"
				platform.error_message = result["error"]
				post_doc.status = "Failed"
				post_doc.error_log = result["error"]
			
			post_doc.save()
			break