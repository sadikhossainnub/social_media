import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import pytz
from social_media.facebook.graph_client import FacebookGraphClient


class FacebookAutoPostPublisher(Document):
	"""Handles automatic and scheduled post publishing"""
	facebook_page: str
	facebook_post: str | None
	post_content: str | None
	post_image: str | None
	variant_b_content: str | None
	variant_b_image: str | None
	winning_variant: str | None
	schedule_type: str
	schedule_datetime: datetime | str | None
	suggested_best_time: datetime | str | None
	target_timezone: str
	content_calendar: str | None
	publish_status: str
	published_datetime: datetime | str | None
	published_post_id: str | None
	auto_analyze_engagement: int | bool
	notify_on_publish: int | bool

	def validate(self):
		"""Validate post publisher configuration"""
		if not self.post_content and not self.facebook_post:
			frappe.throw("Either post content or Facebook Post reference is required")
		
		if self.schedule_type != "Immediate" and not self.schedule_datetime:
			frappe.throw("Schedule date and time is required for scheduled posts")

	def on_submit(self):
		"""Schedule the post for publishing"""
		if self.schedule_type == "Immediate":
			self.publish_now()
		else:
			self._schedule_for_publishing()

	@frappe.whitelist()
	def publish_now(self):
		"""Publish the post immediately"""
		import os
		try:
			# Get post content (check A/B testing winning variant)
			content = self.post_content
			image = self.post_image
			
			if self.winning_variant == "B" and self.variant_b_content:
				content = self.variant_b_content
				image = self.variant_b_image or self.post_image

			# Clean HTML formatting from Text Editor field
			clean_content = frappe.utils.strip_html(str(content or "")).strip() if content else ""

			# Init Graph API client
			client = FacebookGraphClient(page_id=self.facebook_page)
			
			# Call Graph API to create post
			res = None
			if image:
				if image.startswith(("http://", "https://")):
					res = client.create_photo_post(clean_content, image_url=image)
				else:
					site_file_path = frappe.get_site_path("public", image.lstrip("/"))
					if os.path.exists(site_file_path):
						with open(site_file_path, "rb") as img_file:
							res = client.create_photo_post(clean_content, image_file=img_file)
					else:
						full_url = frappe.utils.get_url(image)
						res = client.create_photo_post(clean_content, image_url=full_url)
			else:
				res = client.create_page_post(clean_content)

			if res and "id" in res:
				published_id = res["id"]
				now_dt = datetime.now()
				
				# Log/create entry in Facebook Post Doctype if not already present
				fb_post_name = None
				if frappe.db.exists("Facebook Post", published_id):
					fb_post_name = published_id
				else:
					post_doc = frappe.get_doc({
						"doctype": "Facebook Post",
						"post_id": published_id,
						"page": self.facebook_page,
						"message": clean_content,
						"permalink_url": f"https://facebook.com/{published_id}",
						"created_time": now_dt
					})
					post_doc.insert(ignore_permissions=True)
					fb_post_name = post_doc.name
				
				# Update content calendar status
				if self.content_calendar:
					frappe.db.set_value("Facebook Content Calendar", self.content_calendar, {
						"status": "Published",
						"post": fb_post_name
					})
				
				# Safely update database values on current doc
				self.db_set("publish_status", "Published")
				self.db_set("published_datetime", now_dt)
				self.db_set("published_post_id", published_id)
				if not self.facebook_post and fb_post_name:
					self.db_set("facebook_post", fb_post_name)
				
				# Notify admin if configured
				if self.notify_on_publish:
					self._send_admin_notification("published")
				
				# Start engagement tracking if enabled
				if self.auto_analyze_engagement:
					self._schedule_engagement_analysis()
				
				frappe.msgprint(f"Post published successfully! ID: {published_id}", alert=True)
				return True
			else:
				raise Exception("Failed to publish - no valid ID returned from Facebook Graph API")
		
		except Exception as e:
			self.db_set("publish_status", "Failed")
			if self.content_calendar:
				frappe.db.set_value("Facebook Content Calendar", self.content_calendar, "status", "Failed")
			frappe.log_error(f"Error publishing post: {str(e)}", "Facebook Auto Post Publisher")
			frappe.throw(f"Failed to publish post: {str(e)}")

	def _schedule_for_publishing(self):
		"""Schedule post for future publishing"""
		if self.schedule_type == "Best Time":
			self._calculate_best_publishing_time()
		
		# Enqueue job for scheduled publishing
		publish_time = self.schedule_datetime
		
		frappe.enqueue(
			self._delayed_publish,
			job_name=f"fb_publish_{self.name}",
			scheduled_time=publish_time
		)
		
		self.publish_status = "Scheduled"
		self.save()
		
		if self.notify_on_publish:
			self._send_admin_notification("scheduled")

	def _calculate_best_publishing_time(self):
		"""
		Calculate the best time to publish based on audience analytics
		Uses engagement history to determine optimal posting times
		"""
		try:
			from social_media.facebook.insights import get_best_posting_time
			best_slot = get_best_posting_time(self.facebook_page)
			if best_slot and isinstance(best_slot, dict):
				# Default: 18:00:00 on the best day next week
				time_str = best_slot.get("best_time", "18:00:00")
				self.suggested_best_time = datetime.now().replace(hour=18, minute=0, second=0)
				self.schedule_datetime = self.suggested_best_time
		except Exception as e:
			frappe.log_error(f"Error calculating best time: {str(e)}", "Facebook Auto Post Publisher")

	def _delayed_publish(self):
		"""Called by job queue to publish the post at scheduled time"""
		self.publish_now()

	def _schedule_engagement_analysis(self):
		"""Schedule engagement analysis for this post"""
		frappe.enqueue(
			analyze_post_engagement,
			post_id=self.published_post_id,
			doc_name=self.name,
			job_name=f"fb_analysis_{self.name}"
		)

	def _send_admin_notification(self, action):
		"""Send notification to admins"""
		try:
			admin_users = frappe.get_all(
				"User",
				filters={"roles": "System Manager"},
				fields=["name", "email"]
			)
			
			action_text = {
				"published": "Post Published",
				"scheduled": "Post Scheduled",
				"failed": "Post Publishing Failed"
			}
			
			subject = f"[Facebook] {action_text.get(action, 'Post Action')} - {self.facebook_page}"
			content_snippet = str(self.post_content)[:100] if self.post_content else 'N/A'
			message = f"""
Post has been {action}:

Page: {self.facebook_page}
Content: {content_snippet}...
Status: {self.publish_status}
Time: {self.published_datetime or self.schedule_datetime}

Link: {frappe.utils.get_url()}/app/facebook-auto-post-publisher/{self.name}
"""
			
			for user in admin_users:
				if user.email:
					frappe.sendmail(
						recipients=[user.email],
						subject=subject,
						message=message
					)
		
		except Exception as e:
			frappe.log_error(f"Error sending notification: {str(e)}", "Facebook Auto Post Publisher")

	def retry_publish(self):
		"""Retry publishing a failed post"""
		if self.publish_status != "Failed":
			frappe.throw("Only failed posts can be retried")
		
		self.publish_now()


def analyze_post_engagement(post_id, doc_name):
	"""
	Analyze engagement metrics for a published post
	Called by job queue
	"""
	try:
		doc = frappe.get_doc("Facebook Auto Post Publisher", doc_name)
		page_id = getattr(doc, "facebook_page", None)
		client = FacebookGraphClient(page_id=page_id)
		insights = client.get_post_insights(post_id)
		
		likes = 0
		comments = 0
		shares = 0
		
		if insights and "data" in insights:
			# Parse metrics or fallback to standard post fields
			pass
			
		frappe.db.set_value(
			"Facebook Auto Post Publisher",
			doc_name,
			"publish_status",
			"Published"
		)
	
	except Exception as e:
		frappe.log_error(f"Error analyzing engagement: {str(e)}", "Facebook Auto Post Publisher")


def process_scheduled_posts():
	"""
	Process scheduled posts that are due for publishing
	Called by cron job every 5 minutes
	"""
	try:
		now = datetime.now()
		
		scheduled_posts = frappe.get_all(
			"Facebook Auto Post Publisher",
			filters={
				"publish_status": "Scheduled",
				"schedule_datetime": ["<=", now]
			},
			fields=["name"]
		)
		
		for post in scheduled_posts:
			try:
				doc: FacebookAutoPostPublisher = frappe.get_doc("Facebook Auto Post Publisher", post.name)  # type: ignore
				doc.publish_now()
				frappe.db.commit()
			except Exception as e:
				frappe.log_error(
					f"Error publishing scheduled post {post.name}: {str(e)}",
					"Facebook Auto Post Publisher - Cron"
				)
				frappe.db.rollback()
	
	except Exception as e:
		frappe.log_error(
			f"Error in process_scheduled_posts cron: {str(e)}",
			"Facebook Auto Post Publisher - Cron"
		)


@frappe.whitelist()
def schedule_multiple_posts(posts_data):
	"""
	Schedule multiple posts in bulk
	"""
	try:
		results = []
		for post_info in posts_data:
			doc = frappe.get_doc({
				"doctype": "Facebook Auto Post Publisher",
				"facebook_page": post_info.get("page_id"),
				"post_content": post_info.get("content"),
				"post_image": post_info.get("image"),
				"schedule_type": post_info.get("schedule_type", "Scheduled"),
				"schedule_datetime": post_info.get("schedule_datetime"),
				"auto_analyze_engagement": post_info.get("analyze", True),
				"notify_on_publish": post_info.get("notify", True)
			})
			doc.insert(ignore_permissions=True)
			doc.submit()
			results.append({
				"name": doc.name,
				"status": "Scheduled"
			})
		
		return {
			"success": True,
			"scheduled_posts": results
		}
	
	except Exception as e:
		frappe.log_error(f"Error scheduling posts: {str(e)}", "Facebook Auto Post Publisher")
		return {
			"success": False,
			"error": str(e)
		}
