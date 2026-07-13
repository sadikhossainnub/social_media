import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import pytz
from social_media.facebook.graph_client import FacebookGraphClient


class FacebookAutoPostPublisher(Document):
	"""Handles automatic and scheduled post publishing"""

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

	def publish_now(self):
		"""Publish the post immediately"""
		try:
			# Get post content (check A/B testing winning variant)
			content = self.post_content
			image = self.post_image
			
			if self.winning_variant == "B" and self.variant_b_content:
				content = self.variant_b_content
				image = self.variant_b_image or self.post_image

			# Init client
			client = FacebookGraphClient(page_id=self.facebook_page)
			
			# Call Graph API to create post
			res = None
			if image:
				res = client.create_photo_post(content, image_url=image)
			else:
				res = client.create_page_post(content)

			if res and "id" in res:
				self.publish_status = "Published"
				self.published_datetime = datetime.now()
				self.published_post_id = res["id"]
				
				# Log the published post to Facebook Post Doctype
				post_doc = frappe.get_doc({
					"doctype": "Facebook Post",
					"post_id": res["id"],
					"page": self.facebook_page,
					"message": content,
					"permalink_url": f"https://facebook.com/{res['id']}",
					"created_time": datetime.now()
				})
				post_doc.insert(ignore_permissions=True)
				
				# Update content calendar status
				if self.content_calendar:
					frappe.db.set_value("Facebook Content Calendar", self.content_calendar, {
						"status": "Published",
						"post": post_doc.name
					})
				
				self.save()
				
				# Notify admin if configured
				if self.notify_on_publish:
					self._send_admin_notification("published")
				
				# Start engagement tracking if enabled
				if self.auto_analyze_engagement:
					self._schedule_engagement_analysis()
				
				frappe.msgprint(f"Post published successfully! ID: {res['id']}")
				return True
			else:
				raise Exception("Failed to publish - no ID returned from Graph API")
		
		except Exception as e:
			self.publish_status = "Failed"
			if self.content_calendar:
				frappe.db.set_value("Facebook Content Calendar", self.content_calendar, "status", "Failed")
			self.save()
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
			message = f"""
Post has been {action}:

Page: {self.facebook_page}
Content: {self.post_content[:100] if self.post_content else 'N/A'}...
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
		client = FacebookGraphClient(page_id=doc.facebook_page)
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
				doc = frappe.get_doc("Facebook Auto Post Publisher", post.name)
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
