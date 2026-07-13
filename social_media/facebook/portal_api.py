"""
Facebook Portal API Layer
Provides whitelisted RPC endpoints for the standalone Vue.js portal.
Returns standard JSON responses: {"success": true, "data": ..., "message": ""}
"""

import frappe
import json
import csv
from io import StringIO
from datetime import datetime
from social_media.facebook.graph_client import FacebookGraphClient
from social_media.facebook.insights import get_best_posting_time


def check_portal_permission(page_id=None, permission_type="can_view"):
	"""
	Check if the current logged-in user has permission for a specific page.
	Permissions map to team roles defined in Facebook Settings.
	"""
	if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
		return True

	settings = frappe.get_single("Facebook Settings")
	roles = settings.get("team_roles") or []

	for role in roles:
		if role.user == frappe.session.user:
			if page_id and role.page != page_id:
				continue
			# Check specific role permission
			if permission_type == "can_post" and not role.can_post:
				continue
			if permission_type == "can_comment" and not role.can_comment:
				continue
			if permission_type == "can_message" and not role.can_message:
				continue
			if permission_type == "can_ads" and not role.can_ads:
				continue
			if permission_type == "can_insights" and not role.can_insights:
				continue
			if permission_type == "can_settings" and not role.can_settings:
				continue
			return True

	return False


def api_response(success=True, data=None, message="", total_count=0, status_code=200):
	"""Standardize API response format."""
	frappe.local.response["http_status_code"] = status_code
	return {
		"success": success,
		"data": data,
		"message": message,
		"total_count": total_count
	}


# ── Auth & Permissions ────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def portal_login(usr, pwd):
	"""
	Log in a user to the portal and establish a session.
	Returns standard session information.
	"""
	try:
		from frappe.auth import LoginManager
		login_manager = LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
	except frappe.AuthenticationError:
		frappe.clear_messages()
		return api_response(success=False, message="Invalid username or password", status_code=401)

	# Get permissions
	user = frappe.session.user
	roles = frappe.get_roles(user)
	
	return api_response(success=True, data={
		"user": user,
		"roles": roles,
		"sid": frappe.session.sid
	})


@frappe.whitelist()
def get_current_user_permissions():
	"""Get all Facebook page permissions for the current user."""
	user = frappe.session.user
	if "System Manager" in frappe.get_roles(user) or user == "Administrator":
		return api_response(success=True, data={"is_admin": True})

	settings = frappe.get_single("Facebook Settings")
	roles = settings.get("team_roles") or []
	
	user_perms = []
	for r in roles:
		if r.user == user:
			user_perms.append({
				"page": r.page,
				"can_post": r.can_post,
				"can_comment": r.can_comment,
				"can_message": r.can_message,
				"can_ads": r.can_ads,
				"can_insights": r.can_insights,
				"can_settings": r.can_settings
			})
	
	return api_response(success=True, data={"is_admin": False, "permissions": user_perms})


# ── Pages Endpoints ───────────────────────────────────────────────────

@frappe.whitelist()
def get_pages():
	"""List all connected pages the user has permission to view."""
	pages = frappe.get_all(
		"Facebook Page",
		fields=["name", "page_id", "page_name", "status", "page_category", "followers_count", "fan_count", "profile_picture_url"]
	)
	
	# Filter pages by user team role
	allowed_pages = []
	for p in pages:
		if check_portal_permission(p.name, "can_view"):
			allowed_pages.append(p)
			
	return api_response(success=True, data=allowed_pages)


@frappe.whitelist()
def get_page_details(page_id):
	"""Get detailed info for a single page, fetching fresh stats from Graph API."""
	if not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	client = FacebookGraphClient(page_id=page_id)
	info = client.get_page_info()
	
	if info:
		# Update database stats
		try:
			doc = frappe.get_doc("Facebook Page", page_id)
			doc.followers_count = info.get("followers_count", 0)
			doc.fan_count = info.get("fan_count", 0)
			if "picture" in info and "data" in info["picture"]:
				doc.profile_picture_url = info["picture"]["data"].get("url")
			if "cover" in info:
				doc.cover_photo_url = info["cover"].get("source")
			doc.save(ignore_permissions=True)
		except Exception:
			pass
			
		return api_response(success=True, data=info)
		
	# Fallback to local DB if Graph API fails
	try:
		doc = frappe.get_doc("Facebook Page", page_id)
		return api_response(success=True, data=doc.as_dict())
	except frappe.DoesNotExistError:
		return api_response(success=False, message="Page not found", status_code=404)


# ── Posts Endpoints ───────────────────────────────────────────────────

@frappe.whitelist()
def get_posts(page_id=None, status=None, page=1, limit=20):
	"""Get posts for a page."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	filters = {}
	if page_id:
		filters["page"] = page_id
	if status:
		filters["status"] = status
		
	limit_start = (int(page) - 1) * int(limit)
	
	posts = frappe.get_all(
		"Facebook Post",
		filters=filters,
		fields=["name", "post_id", "page", "page_name", "status", "post_type", "permalink_url", "message", "created_time", "like_count", "comment_count", "share_count"],
		order_by="created_time desc",
		limit_start=limit_start,
		limit_page_length=limit
	)
	
	total_count = frappe.db.count("Facebook Post", filters=filters)
	return api_response(success=True, data=posts, total_count=total_count)


@frappe.whitelist()
def create_post(page_id, message, post_type="Text", media_url=None, video_url=None, additional_images=None, schedule_time=None, first_comment=None, utm_source=None, utm_medium=None, utm_campaign=None):
	"""Create a new post, with A/B testing and scheduling support."""
	if not check_portal_permission(page_id, "can_post"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	client = FacebookGraphClient(page_id=page_id)
	
	# Handle scheduling
	if schedule_time:
		# Save as scheduled Auto Publisher post
		publisher_doc = frappe.get_doc({
			"doctype": "Facebook Auto Post Publisher",
			"facebook_page": page_id,
			"post_content": message,
			"schedule_type": "Scheduled",
			"schedule_datetime": schedule_time,
			"publish_status": "Scheduled"
		})
		publisher_doc.insert(ignore_permissions=True)
		
		# Create a Content Calendar entry
		cal_doc = frappe.get_doc({
			"doctype": "Facebook Content Calendar",
			"title": message[:50] + "..." if len(message) > 50 else message,
			"page": page_id,
			"scheduled_date": datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S").date(),
			"scheduled_time": datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S").time(),
			"status": "Scheduled",
			"auto_post_publisher": publisher_doc.name,
			"content_preview": message
		})
		cal_doc.insert(ignore_permissions=True)
		
		publisher_doc.content_calendar = cal_doc.name
		publisher_doc.save(ignore_permissions=True)
		
		return api_response(success=True, message="Post successfully scheduled", data=publisher_doc.as_dict())
		
	# Immediate publish to Facebook
	res = None
	if post_type == "Text":
		res = client.create_page_post(message)
	elif post_type == "Image" and media_url:
		res = client.create_photo_post(message, image_url=media_url)
	elif post_type == "Video" and video_url:
		res = client.create_video_post(message, video_url=video_url)
	elif post_type == "Carousel" and additional_images:
		# Multi-image post logic
		imgs = json.loads(additional_images) if isinstance(additional_images, str) else additional_images
		photo_ids = []
		for img in imgs:
			photo_res = client.upload_unpublished_photo(image_url=img)
			if photo_res and "id" in photo_res:
				photo_ids.append(photo_res["id"])
		if photo_ids:
			res = client.create_multi_photo_post(message, photo_ids)
			
	if res and "id" in res:
		post_id = res["id"]
		# Log to DB
		post_doc = frappe.get_doc({
			"doctype": "Facebook Post",
			"post_id": post_id,
			"page": page_id,
			"post_type": post_type,
			"message": message,
			"created_time": datetime.now(),
			"permalink_url": f"https://facebook.com/{post_id}"
		})
		post_doc.insert(ignore_permissions=True)
		
		# Post first comment if provided
		if first_comment:
			try:
				client.reply_to_comment(post_id, first_comment)
			except Exception:
				pass
				
		return api_response(success=True, data=post_doc.as_dict())
		
	return api_response(success=False, message="Failed to publish post to Facebook")


@frappe.whitelist()
def publish_post_now(publisher_name):
	"""Immediately publish a scheduled post."""
	try:
		pub_doc = frappe.get_doc("Facebook Auto Post Publisher", publisher_name)
	except frappe.DoesNotExistError:
		return api_response(success=False, message="Scheduled post not found", status_code=404)
		
	if not check_portal_permission(pub_doc.facebook_page, "can_post"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	# Call publisher task directly
	from social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher import publish_post
	success = publish_post(pub_doc)
	
	if success:
		return api_response(success=True, message="Post published successfully")
	return api_response(success=False, message="Failed to publish post")


@frappe.whitelist()
def get_calendar_entries(page_id, start_date, end_date):
	"""Get content calendar entries for a given date range."""
	if not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	filters = {
		"page": page_id,
		"scheduled_date": ["between", [start_date, end_date]]
	}
	
	entries = frappe.get_all(
		"Facebook Content Calendar",
		filters=filters,
		fields=["name", "title", "scheduled_date", "scheduled_time", "status", "post", "color_tag", "content_preview"]
	)
	
	return api_response(success=True, data=entries)


# ── Comments Endpoints ────────────────────────────────────────────────

@frappe.whitelist()
def get_comments(page_id, post_id=None, sentiment=None, is_hidden=None, page=1, limit=50):
	"""List comments with advanced filters (sentiment, status)."""
	if not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	filters = {"page": page_id}
	if post_id:
		filters["post"] = post_id
	if sentiment:
		filters["sentiment"] = sentiment
	if is_hidden is not None:
		filters["is_hidden"] = int(is_hidden)
		
	limit_start = (int(page) - 1) * int(limit)
	
	comments = frappe.get_all(
		"Facebook Comment",
		filters=filters,
		fields=["name", "comment_id", "post", "post_id", "commenter_name", "message", "created_time", "sentiment", "sentiment_score", "is_hidden", "replied_time", "reply_message"],
		order_by="created_time desc",
		limit_start=limit_start,
		limit_page_length=limit
	)
	
	total_count = frappe.db.count("Facebook Comment", filters=filters)
	return api_response(success=True, data=comments, total_count=total_count)


@frappe.whitelist()
def reply_to_comment(comment_name, reply_message):
	"""Reply to a Facebook comment."""
	try:
		comment_doc = frappe.get_doc("Facebook Comment", comment_name)
	except frappe.DoesNotExistError:
		return api_response(success=False, message="Comment not found", status_code=404)
		
	if not check_portal_permission(comment_doc.page, "can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	client = FacebookGraphClient(page_id=comment_doc.page)
	res = client.reply_to_comment(comment_doc.comment_id, reply_message)
	
	if res and "id" in res:
		comment_doc.reply_message = reply_message
		comment_doc.replied_time = datetime.now()
		comment_doc.replied_by = frappe.session.user
		comment_doc.save(ignore_permissions=True)
		return api_response(success=True, data=comment_doc.as_dict())
		
	return api_response(success=False, message="Failed to send reply to Facebook")


@frappe.whitelist()
def hide_comment(comment_name, hide=True):
	"""Hide or unhide a comment."""
	try:
		comment_doc = frappe.get_doc("Facebook Comment", comment_name)
	except frappe.DoesNotExistError:
		return api_response(success=False, message="Comment not found", status_code=404)
		
	if not check_portal_permission(comment_doc.page, "can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	client = FacebookGraphClient(page_id=comment_doc.page)
	res = client.hide_comment(comment_doc.comment_id) if hide else client.unhide_comment(comment_doc.comment_id)
	
	if res and res.get("success"):
		comment_doc.is_hidden = 1 if hide else 0
		comment_doc.save(ignore_permissions=True)
		return api_response(success=True, data=comment_doc.as_dict())
		
	return api_response(success=False, message="Failed to toggle comment visibility")


# ── Messenger Endpoints ───────────────────────────────────────────────

@frappe.whitelist()
def get_conversations(page_id, status=None, page=1, limit=20):
	"""Get conversation threads grouped by user."""
	if not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	# Find unique conversation_ids
	filters = {"page": page_id}
	if status:
		filters["conversation_status"] = status
		
	limit_start = (int(page) - 1) * int(limit)
	
	# Fetch the latest message for each unique conversation thread
	threads = frappe.db.sql(
		"""
		SELECT 
			conversation_id,
			sender_name,
			sender_id,
			MAX(timestamp) as last_message_time,
			SUM(CASE WHEN is_read = 0 AND direction = 'Incoming' THEN 1 ELSE 0 END) as unread_count,
			conversation_status,
			assigned_agent
		FROM `tabFacebook Messenger Chat`
		WHERE page = %(page_id)s
		GROUP BY conversation_id, sender_name, sender_id, conversation_status, assigned_agent
		ORDER BY last_message_time DESC
		LIMIT %(limit_start)s, %(limit)s
		""",
		{"page_id": page_id, "limit_start": limit_start, "limit": int(limit)},
		as_dict=True
	)
	
	# For each thread, get the content of the last message
	for thread in threads:
		last_msg = frappe.get_all(
			"Facebook Messenger Chat",
			filters={"conversation_id": thread.conversation_id},
			fields=["message", "direction"],
			order_by="timestamp desc",
			limit=1
		)
		if last_msg:
			thread["last_message"] = last_msg[0].message
			thread["last_message_direction"] = last_msg[0].direction
			
	total_count = frappe.db.sql(
		"SELECT COUNT(DISTINCT conversation_id) FROM `tabFacebook Messenger Chat` WHERE page = %s",
		(page_id,)
	)[0][0]
	
	return api_response(success=True, data=threads, total_count=total_count)


@frappe.whitelist()
def get_messages(conversation_id, page=1, limit=50):
	"""Get all messages in a conversation thread."""
	# Check permissions on first message page
	sample_msg = frappe.get_all("Facebook Messenger Chat", filters={"conversation_id": conversation_id}, fields=["page"], limit=1)
	if not sample_msg or not check_portal_permission(sample_msg[0].page, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	limit_start = (int(page) - 1) * int(limit)
	
	messages = frappe.get_all(
		"Facebook Messenger Chat",
		filters={"conversation_id": conversation_id},
		fields=["name", "sender_name", "sender_id", "direction", "timestamp", "message", "is_read", "attachments"],
		order_by="timestamp asc",
		limit_start=limit_start,
		limit_page_length=limit
	)
	
	# Mark as read
	frappe.db.set_value(
		"Facebook Messenger Chat",
		{"conversation_id": conversation_id, "direction": "Incoming", "is_read": 0},
		"is_read", 1,
		update_modified=False
	)
	
	return api_response(success=True, data=messages)


@frappe.whitelist()
def send_message(page_id, recipient_id, message_text):
	"""Send a message to a customer via Messenger."""
	if not check_portal_permission(page_id, "can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	client = FacebookGraphClient(page_id=page_id)
	res = client.send_message(recipient_id, message_text)
	
	if res and "message_id" in res:
		# Save message to DB
		msg_doc = frappe.get_doc({
			"doctype": "Facebook Messenger Chat",
			"sender_id": page_id,
			"sender_name": client.get_page_info().get("name", "Page"),
			"page": page_id,
			"conversation_id": f"t_{recipient_id}",
			"direction": "Outgoing",
			"message": message_text,
			"timestamp": datetime.now(),
			"is_read": 1
		})
		msg_doc.insert(ignore_permissions=True)
		
		# Also log in the log table
		try:
			log_doc = frappe.get_doc({
				"doctype": "Facebook Message Log",
				"instance": page_id,
				"direction": "Outbound",
				"status": "Sent",
				"timestamp": datetime.now(),
				"sender_psid": page_id,
				"recipient_psid": recipient_id,
				"message_id": res["message_id"],
				"message_text": message_text
			})
			log_doc.insert(ignore_permissions=True)
		except Exception:
			pass
			
		return api_response(success=True, data=msg_doc.as_dict())
		
	return api_response(success=False, message="Failed to send message via Messenger")


@frappe.whitelist()
def update_conversation_status(conversation_id, status):
	"""Update conversation thread status (Open/Pending/Resolved)."""
	# Check sample message to verify page permission
	sample_msg = frappe.get_all("Facebook Messenger Chat", filters={"conversation_id": conversation_id}, fields=["page"], limit=1)
	if not sample_msg or not check_portal_permission(sample_msg[0].page, "can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	frappe.db.set_value(
		"Facebook Messenger Chat",
		{"conversation_id": conversation_id},
		"conversation_status", status
	)
	
	return api_response(success=True, message=f"Status updated to {status}")


# ── Leads Endpoints ───────────────────────────────────────────────────

@frappe.whitelist()
def get_leads(page_id=None, status=None, page=1, limit=50):
	"""Get captured leads."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	filters = {}
	if page_id:
		filters["page"] = page_id
	if status:
		filters["status"] = status
		
	limit_start = (int(page) - 1) * int(limit)
	
	leads = frappe.get_all(
		"Facebook Lead",
		filters=filters,
		fields=["name", "facebook_lead_id", "lead_form_id", "page", "page_name", "full_name", "email", "phone", "ad_name", "campaign_name", "created_at", "erpnext_lead", "crm_lead", "status", "duplicate_status", "notes"],
		order_by="created_at desc",
		limit_start=limit_start,
		limit_page_length=limit
	)
	
	total_count = frappe.db.count("Facebook Lead", filters=filters)
	return api_response(success=True, data=leads, total_count=total_count)


@frappe.whitelist()
def convert_lead_to_erpnext(lead_name):
	"""Trigger conversion of captured Facebook Lead to ERPNext Lead."""
	try:
		lead_doc = frappe.get_doc("Facebook Lead", lead_name)
	except frappe.DoesNotExistError:
		return api_response(success=False, message="Lead not found", status_code=404)
		
	if not check_portal_permission(lead_doc.page, "can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	# Call local lead conversion method
	from social_media.facebook.leads import create_erpnext_lead
	erpnext_lead_name = create_erpnext_lead(lead_doc)
	
	if erpnext_lead_name:
		lead_doc.erpnext_lead = erpnext_lead_name
		lead_doc.status = "Converted"
		lead_doc.save(ignore_permissions=True)
		return api_response(success=True, data={"erpnext_lead": erpnext_lead_name})
		
	return api_response(success=False, message="Failed to create Lead in ERPNext")


# ── Insights & Ads ────────────────────────────────────────────────────

@frappe.whitelist()
def get_page_insights_data(page_id, date_from=None, date_to=None):
	"""Get page insights for analytics charts."""
	if not check_portal_permission(page_id, "can_insights"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	filters = {"page": page_id}
	if date_from and date_to:
		filters["date"] = ["between", [date_from, date_to]]
		
	insights = frappe.get_all(
		"Facebook Insight",
		filters=filters,
		fields=["date", "metric_name", "metric_value", "period"],
		order_by="date asc"
	)
	
	return api_response(success=True, data=insights)


@frappe.whitelist()
def get_ad_campaigns(page_id=None, page=1, limit=50):
	"""Get campaign data for connected Ad Accounts."""
	if page_id and not check_portal_permission(page_id, "can_ads"):
		return api_response(success=False, message="Permission denied", status_code=403)

	filters = {}
	if page_id:
		filters["page"] = page_id
		
	limit_start = (int(page) - 1) * int(limit)
	
	campaigns = frappe.get_all(
		"Facebook Ad Campaign",
		filters=filters,
		fields=["name", "campaign_id", "campaign_name", "ad_account", "page", "objective", "status", "daily_budget", "lifetime_budget", "start_date", "end_date", "impressions", "clicks", "spend", "reach"],
		order_by="campaign_name asc",
		limit_start=limit_start,
		limit_page_length=limit
	)
	
	total_count = frappe.db.count("Facebook Ad Campaign", filters=filters)
	return api_response(success=True, data=campaigns, total_count=total_count)


# ── Settings & Team Roles ─────────────────────────────────────────────

@frappe.whitelist()
def get_portal_settings():
	"""Get Facebook settings details (excluding passwords)."""
	if not check_portal_permission(permission_type="can_settings"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	settings = frappe.get_single("Facebook Settings")
	
	# Exclude secrets
	settings_dict = settings.as_dict()
	settings_dict.pop("app_secret", None)
	settings_dict.pop("page_access_token", None)
	settings_dict.pop("user_access_token", None)
	settings_dict.pop("webhook_signature_secret", None)
	settings_dict.pop("ai_api_key", None)
	
	return api_response(success=True, data=settings_dict)
