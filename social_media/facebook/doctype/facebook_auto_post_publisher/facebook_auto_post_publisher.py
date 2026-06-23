import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import pytz


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
			# Get post content
			content = self.post_content or self._get_facebook_post_content()
			
			# Publish to Facebook
			post_id = self._publish_to_facebook(content)
			
			self.publish_status = "Published"
			self.published_datetime = datetime.now()
			self.published_post_id = post_id
			self.save()
			
			# Notify admin if configured
			if self.notify_on_publish:
				self._send_admin_notification("published")
			
			# Start engagement tracking if enabled
			if self.auto_analyze_engagement:
				self._schedule_engagement_analysis()
			
			frappe.msgprint(f"Post published successfully! ID: {post_id}")
		
		except Exception as e:
			self.publish_status = "Failed"
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
			# Get the page's engagement data
			engagement_data = self._get_page_engagement_data()
			
			if engagement_data:
				best_hour = engagement_data.get("best_hour", 18)  # Default: 6 PM
				best_day = engagement_data.get("best_day", "weekday")
				
				# Calculate the next best time slot
				next_best_time = self._calculate_next_best_slot(best_hour, best_day)
				self.schedule_datetime = next_best_time
		
		except Exception as e:
			frappe.log_error(f"Error calculating best time: {str(e)}", "Facebook Auto Post Publisher")
			# Fall back to the originally set time

	def _calculate_next_best_slot(self, hour, day_preference):
		"""Calculate the next best time slot for publishing"""
		now = datetime.now(pytz.timezone(self.target_timezone or "UTC"))
		
		# Calculate target time for today
		target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
		
		# If time has passed, schedule for tomorrow
		if target <= now:
			target += timedelta(days=1)
		
		return target

	def _delayed_publish(self):
		"""Called by job queue to publish the post at scheduled time"""
		self.publish_now()

	def _get_facebook_post_content(self):
		"""Get content from linked Facebook Post"""
		if self.facebook_post:
			post = frappe.get_doc("Facebook Post", self.facebook_post)
			return {
				"text": post.post_text,
				"image": post.post_image
			}
		return None

	def _publish_to_facebook(self, content):
		"""
		Publish content to Facebook API
		Returns the Facebook post ID
		"""
		try:
			# This would integrate with Facebook API
			# For now, just simulate the API call
			post_id = f"post_{self.name}_{datetime.now().timestamp()}"
			
			frappe.log_error(
				f"Publishing to Facebook: {content}",
				"Facebook Auto Post Publisher Debug"
			)
			
			return post_id
		
		except Exception as e:
			frappe.log_error(f"Error publishing to Facebook API: {str(e)}", "Facebook Auto Post Publisher")
			raise

	def _get_page_engagement_data(self):
		"""Get engagement analytics for the page"""
		try:
			# Query engagement data from Facebook Post documents
			engagement_stats = frappe.db.sql("""
				SELECT 
					HOUR(published_at) as hour,
					AVG(likes + comments + shares) as avg_engagement
				FROM `tabFacebook Post`
				WHERE facebook_page = %s AND published_at IS NOT NULL
				GROUP BY HOUR(published_at)
				ORDER BY avg_engagement DESC
				LIMIT 1
			""", (self.facebook_page,), as_dict=True)
			
			if engagement_stats:
				return {
					"best_hour": engagement_stats[0].get("hour", 18),
					"best_day": "weekday"  # Would be calculated from day-of-week data
				}
			return None
		
		except Exception as e:
			frappe.log_error(f"Error getting engagement data: {str(e)}", "Facebook Auto Post Publisher")
			return None

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
				filters={"roles": "Administrator"},
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
		# Query Facebook API for engagement data
		engagement_data = {
			"likes": 0,
			"comments": 0,
			"shares": 0
		}
		
		# Update the Facebook Auto Post Publisher document
		doc = frappe.get_doc("Facebook Auto Post Publisher", doc_name)
		frappe.db.set_value(
			"Facebook Auto Post Publisher",
			doc_name,
			"publish_status",
			"Published"
		)
		
		frappe.log_error(
			f"Analyzing engagement for post {post_id}: {engagement_data}",
			"Facebook Auto Post Publisher Debug"
		)
	
	except Exception as e:
		frappe.log_error(f"Error analyzing engagement: {str(e)}", "Facebook Auto Post Publisher")


def process_scheduled_posts():
	"""
	Process scheduled posts that are due for publishing
	Called by cron job every 5 minutes
	"""
	try:
		# Get all scheduled posts that are due for publishing
		now = datetime.now()
		
		scheduled_posts = frappe.get_list(
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
					f"Error processing scheduled post {post.name}: {str(e)}",
					"Facebook Auto Post Publisher - Scheduled Posts Processing"
				)
				frappe.db.rollback()
	
	except Exception as e:
		frappe.log_error(
			f"Error in process_scheduled_posts: {str(e)}",
			"Facebook Auto Post Publisher - Scheduled Posts Processing"
		)


@frappe.whitelist()
def schedule_multiple_posts(posts_data):
	"""
	Schedule multiple posts in bulk
	
	Args:
		posts_data: List of post dictionaries
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
			doc.insert()
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


def process_scheduled_posts():
	"""
	Process scheduled posts that are due for publishing
	Called by cron job every 5 minutes
	"""
	try:
		now = datetime.now()
		
		# Find all scheduled posts that are due
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
		
		if scheduled_posts:
			frappe.log_error(
				f"Processed {len(scheduled_posts)} scheduled posts",
				"Facebook Auto Post Publisher - Cron"
			)
	
	except Exception as e:
		frappe.log_error(
			f"Error in process_scheduled_posts cron: {str(e)}",
			"Facebook Auto Post Publisher - Cron"
		)
