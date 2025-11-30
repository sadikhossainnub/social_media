import frappe
from frappe.model.document import Document


class SocialPost(Document):
	def validate(self):
		if not self.platforms:
			frappe.throw("At least one platform must be selected")
		
		# Validate content length per platform
		for platform in self.platforms:
			channel_doc = frappe.get_doc("Social Media Channel", platform.channel)
			self._validate_content_length(channel_doc.platform)
	
	def on_submit(self):
		"""Publish post when submitted"""
		if self.scheduled_time and self.scheduled_time > frappe.utils.now():
			# Schedule for later
			from social_media.api_social import schedule_social_post
			schedule_social_post(self.name, self.scheduled_time)
		else:
			# Publish immediately
			from social_media.api_social import publish_social_post
			frappe.enqueue(
				publish_social_post,
				post_id=self.name,
				queue="short"
			)
	
	@frappe.whitelist()
	def publish_now(self):
		"""Manually publish post"""
		from social_media.api_social import publish_social_post
		return publish_social_post(self.name)
	
	@frappe.whitelist()
	def schedule_post(self, scheduled_time):
		"""Schedule post for later"""
		from social_media.api_social import schedule_social_post
		return schedule_social_post(self.name, scheduled_time)
	
	@frappe.whitelist()
	def preview_post(self):
		"""Generate post preview for different platforms"""
		previews = {}
		
		for platform in self.platforms:
			channel_doc = frappe.get_doc("Social Media Channel", platform.channel)
			
			preview = {
				"platform": channel_doc.platform,
				"channel": channel_doc.channel_name,
				"content": self.content,
				"attachments": [att.file_url for att in self.attachments],
				"character_count": len(self.content),
				"character_limit": self._get_character_limit(channel_doc.platform)
			}
			
			previews[platform.channel] = preview
		
		return previews
	
	def _validate_content_length(self, platform):
		"""Validate content length for platform"""
		limits = {
			"Facebook": 63206,
			"Instagram": 2200,
			"Twitter": 280,
			"LinkedIn": 3000
		}
		
		limit = limits.get(platform)
		if limit and len(self.content) > limit:
			frappe.throw(f"Content exceeds {platform} limit of {limit} characters")
	
	def _get_character_limit(self, platform):
		"""Get character limit for platform"""
		limits = {
			"Facebook": 63206,
			"Instagram": 2200,
			"Twitter": 280,
			"LinkedIn": 3000
		}
		return limits.get(platform, 0)