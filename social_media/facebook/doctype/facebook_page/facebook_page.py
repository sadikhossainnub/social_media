# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import (
	get_page_info,
	subscribe_app_to_page,
	unsubscribe_app_from_page,
	set_greeting_text,
	get_subscribed_fields,
	get_page_posts,
	create_post,
	get_post_comments
)


class FacebookPage(Document):
	def before_insert(self):
		pass

	def after_insert(self):
		self.subscribe_to_events()

	def subscribe_to_events(self):
		"""Subscribe the app to this page's events."""
		try:
			response = subscribe_app_to_page(
				page_id=self.page_id,
				app_access_token=self.access_token,
				callback_url=self.get_webhook_url()
			)
			if response:
				self.status = "Active"
				self.save()
				frappe.msgprint("Successfully subscribed to Facebook events")
		except Exception as e:
			frappe.msgprint(f"Failed to subscribe: {str(e)}")

	def unsubscribe_from_events(self):
		"""Unsubscribe the app from this page's events."""
		try:
			response = unsubscribe_app_from_page(
				page_id=self.page_id,
				app_access_token=self.access_token
			)
			if response:
				self.status = "Inactive"
				self.save()
				frappe.msgprint("Unsubscribed from Facebook events")
		except Exception as e:
			frappe.msgprint(f"Failed to unsubscribe: {str(e)}")

	@frappe.whitelist()
	def refresh_page_info(self):
		"""Fetch latest page info from Facebook."""
		try:
			response = get_page_info(
				access_token=self.access_token,
				page_id=self.page_id
			)
			if response:
				if response.get("name"):
					self.page_name = response["name"]
				if response.get("picture"):
					picture_data = response["picture"].get("data", {})
					if picture_data.get("url"):
						pass  # Store or display profile picture
				self.save()
				frappe.msgprint("Page info updated")
		except Exception as e:
			frappe.msgprint(f"Failed to refresh page info: {str(e)}")

	@frappe.whitelist()
	def set_greeting(self, greeting_text):
		"""Set the greeting message for new chats."""
		try:
			response = set_greeting_text(
				page_id=self.page_id,
				greeting_text=greeting_text
			)
			if response:
				self.greeting_text = greeting_text
				self.save()
				frappe.msgprint("Greeting text set successfully")
		except Exception as e:
			frappe.msgprint(f"Failed to set greeting: {str(e)}")

	@frappe.whitelist()
	def get_subscribed_fields(self):
		"""Fetch currently subscribed fields from Facebook."""
		try:
			response = get_subscribed_fields(
				page_id=self.page_id,
				access_token=self.access_token
			)
			if response:
				import json
				self.subscribed_fields = json.dumps(response, indent=2)
				self.save()
				frappe.msgprint("Subscribed fields fetched")
		except Exception as e:
			frappe.msgprint(f"Failed to fetch subscribed fields: {str(e)}")

	@frappe.whitelist()
	def fetch_posts(self, limit=25):
		"""Fetch latest posts from this page."""
		try:
			response = get_page_posts(
				page_id=self.page_id,
				access_token=self.access_token,
				limit=limit
			)
			if response and response.get("data"):
				import json
				posts_data = json.dumps(response["data"], indent=2)
				frappe.msgprint(f"Fetched {len(response['data'])} posts")
				return posts_data
		except Exception as e:
			frappe.msgprint(f"Failed to fetch posts: {str(e)}")

	@frappe.whitelist()
	def create_post(self, message, link=None, picture=None, name=None, caption=None):
		"""Create a new post on this page."""
		try:
			response = create_post(
				page_id=self.page_id,
				message=message,
				access_token=self.access_token,
				link=link,
				picture=picture,
				name=name,
				caption=caption
			)
			if response:
				frappe.msgprint(f"Post created: {response.get('id')}")
				return response
		except Exception as e:
			frappe.msgprint(f"Failed to create post: {str(e)}")

	@frappe.whitelist()
	def get_post_comments(self, post_id):
		"""Fetch comments for a specific post."""
		try:
			response = get_post_comments(
				page_id=self.page_id,
				post_id=post_id,
				access_token=self.access_token
			)
			if response:
				import json
				return json.dumps(response, indent=2)
		except Exception as e:
			frappe.msgprint(f"Failed to fetch comments: {str(e)}")

	def get_webhook_url(self):
		"""Get the webhook URL for this page."""
		site_url = frappe.utils.get_url()
		return f"{site_url}/api/method/social_media.facebook.api.webhook"
