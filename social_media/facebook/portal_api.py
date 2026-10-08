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


def resolve_page_ids(page_id=None):
	"""
	Given a page_id (which could be doc.name or numeric page_id),
	returns a list of candidate strings to match against DB `page` columns.
	If page_id is None, empty, 'all', 'undefined', or 'null', returns None.
	"""
	if not page_id or str(page_id).strip().lower() in ("all", "undefined", "null", "none", ""):
		return None

	candidate_ids = {str(page_id).strip()}
	
	try:
		pages = frappe.get_all("Facebook Page", filters=[
			["Facebook Page", "name", "=", page_id]
		], fields=["name", "page_id"], ignore_permissions=True)
		
		if not pages:
			pages = frappe.get_all("Facebook Page", filters=[
				["Facebook Page", "page_id", "=", page_id]
			], fields=["name", "page_id"], ignore_permissions=True)

		for p in pages:
			if p.get("name"):
				candidate_ids.add(str(p.get("name")).strip())
			if p.get("page_id"):
				candidate_ids.add(str(p.get("page_id")).strip())
	except Exception:
		pass

	return list(candidate_ids)


def check_portal_permission(page_id=None, permission_type="can_view"):
	"""
	Check if the current logged-in user has permission for a specific page.
	Permissions map to team roles defined in Facebook Settings.
	"""
	if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
		return True

	settings = frappe.get_single("Facebook Settings")
	roles = settings.get("team_roles") or []
	if not roles:
		return True

	page_ids = resolve_page_ids(page_id) if page_id else None

	for role in roles:
		if role.user == frappe.session.user:
			if page_ids and role.page not in page_ids and role.page != page_id:
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
		fields=["name", "page_id", "page_name", "status", "page_category", "followers_count", "fan_count", "profile_picture_url"],
		ignore_permissions=True
	)
	
	allowed_pages = []
	for p in pages:
		if check_portal_permission(p.name, "can_view"):
			allowed_pages.append(p)

	if not allowed_pages:
		try:
			settings = frappe.get_single("Facebook Settings")
			if settings.page_id:
				allowed_pages.append({
					"name": settings.page_id,
					"page_id": settings.page_id,
					"page_name": settings.page_name or "Paperware Factory",
					"status": "Active" if settings.is_connected else "Inactive",
					"page_category": "Business",
					"followers_count": 0,
					"fan_count": 0,
					"profile_picture_url": ""
				})
		except Exception:
			pass
			
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
			setattr(doc, "followers_count", info.get("followers_count", 0))
			setattr(doc, "fan_count", info.get("fan_count", 0))
			if "picture" in info and "data" in info["picture"]:
				setattr(doc, "profile_picture_url", info["picture"]["data"].get("url"))
			if "cover" in info:
				setattr(doc, "cover_photo_url", info["cover"].get("source"))
			doc.save(ignore_permissions=True)
		except Exception:
			pass
			
		return api_response(success=True, data=info)
		
	# Fallback to local DB if Graph API fails
	try:
		doc = frappe.get_doc("Facebook Page", page_id)
		return api_response(success=True, data=doc.as_dict())
	except frappe.DoesNotExistError:
		try:
			settings = frappe.get_single("Facebook Settings")
			return api_response(success=True, data={
				"name": settings.page_id or page_id,
				"page_name": settings.page_name or "Paperware Factory",
				"followers_count": 0,
				"fan_count": 0
			})
		except Exception:
			return api_response(success=False, message="Page not found", status_code=404)


# ── Posts Endpoints ───────────────────────────────────────────────────

@frappe.whitelist()
def get_posts(page_id=None, status=None, page=1, limit=20):
	"""Get posts for a page."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	page_ids = resolve_page_ids(page_id)
	filters = []
	if page_ids:
		filters.append(["Facebook Post", "page", "in", page_ids])
	if status:
		filters.append(["Facebook Post", "status", "=", status])
		
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
		
		publisher_doc.set("content_calendar", cal_doc.name)
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
		
	page_name = getattr(pub_doc, "facebook_page", None)
	if not check_portal_permission(page_name, "can_post"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	success = pub_doc.publish_now()
	
	if success:
		return api_response(success=True, message="Post published successfully")
	return api_response(success=False, message="Failed to publish post")


@frappe.whitelist()
def get_calendar_entries(page_id=None, start_date=None, end_date=None):
	"""Get content calendar entries for a given date range."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	page_ids = resolve_page_ids(page_id)
	filters = []
	if page_ids:
		filters.append(["Facebook Content Calendar", "page", "in", page_ids])
	if start_date and end_date:
		filters.append(["Facebook Content Calendar", "scheduled_date", "between", [start_date, end_date]])
		
	entries = frappe.get_all(
		"Facebook Content Calendar",
		filters=filters,
		fields=["name", "title", "scheduled_date", "scheduled_time", "status", "post", "color_tag", "content_preview"]
	)
	
	return api_response(success=True, data=entries)


# ── Comments Endpoints ────────────────────────────────────────────────

@frappe.whitelist()
def get_comments(page_id=None, post_id=None, sentiment=None, is_hidden=None, page=1, limit=50):
	"""List comments with advanced filters (sentiment, status)."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	page_ids = resolve_page_ids(page_id)
	filters = []
	if page_ids:
		filters.append(["Facebook Comment", "page", "in", page_ids])
	if post_id:
		filters.append(["Facebook Comment", "post", "=", post_id])
	if sentiment:
		filters.append(["Facebook Comment", "sentiment", "=", sentiment])
	if is_hidden is not None:
		filters.append(["Facebook Comment", "is_hidden", "=", int(is_hidden)])
		
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
		
	comment_page = getattr(comment_doc, "page", None)
	if not check_portal_permission(comment_page, "can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	comment_id = getattr(comment_doc, "comment_id", "")
	client = FacebookGraphClient(page_id=comment_page)
	res = client.reply_to_comment(comment_id, reply_message)
	
	if res and "id" in res:
		setattr(comment_doc, "reply_message", reply_message)
		setattr(comment_doc, "replied_time", datetime.now())
		setattr(comment_doc, "replied_by", frappe.session.user)
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
		
	comment_page = getattr(comment_doc, "page", None)
	if not check_portal_permission(comment_page, "can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	comment_id = getattr(comment_doc, "comment_id", "")
	client = FacebookGraphClient(page_id=comment_page)
	res = client.hide_comment(comment_id) if hide else client.unhide_comment(comment_id)
	
	if res and res.get("success"):
		setattr(comment_doc, "is_hidden", 1 if hide else 0)
		comment_doc.save(ignore_permissions=True)
		return api_response(success=True, data=comment_doc.as_dict())
		
	return api_response(success=False, message="Failed to toggle comment visibility")


# ── Messenger Endpoints ───────────────────────────────────────────────

@frappe.whitelist()
def get_conversations(page_id=None, status=None, page=1, limit=20):
	"""Get conversation threads grouped by user (optimized single SQL query)."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	page_ids = resolve_page_ids(page_id)
	where_clauses = []
	params = {}

	if page_ids:
		where_clauses.append("(page IN %(page_ids)s OR page IS NULL OR page = '')")
		params["page_ids"] = tuple(page_ids)
	if status:
		where_clauses.append("conversation_status = %(status)s")
		params["status"] = status

	where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
	limit_start = (int(page) - 1) * int(limit)
	params["limit_start"] = limit_start
	params["limit"] = int(limit)

	# High-performance single SQL query
	query = f"""
		SELECT 
			c.conversation_id,
			c.message AS last_message,
			c.direction AS last_message_direction,
			c.timestamp AS last_message_time,
			COALESCE(
				NULLIF(cust.sender_name, ''),
				CASE WHEN c.direction = 'Incoming' AND c.sender_name NOT IN ('Paperware Factory', 'Page Admin', 'Page') THEN c.sender_name ELSE NULL END,
				'Facebook Customer'
			) AS sender_name,
			COALESCE(cust.sender_id, CASE WHEN c.conversation_id LIKE 't_%%' THEN SUBSTRING(c.conversation_id, 3) ELSE c.sender_id END) AS sender_id,
			COALESCE(unr.unread_count, 0) AS unread_count,
			c.conversation_status,
			c.assigned_agent,
			c.is_complaint,
			c.page
		FROM `tabFacebook Messenger Chat` c
		INNER JOIN (
			SELECT conversation_id, MAX(timestamp) AS max_time
			FROM `tabFacebook Messenger Chat`
			{where_sql}
			GROUP BY conversation_id
		) latest ON c.conversation_id = latest.conversation_id AND c.timestamp = latest.max_time
		LEFT JOIN (
			SELECT conversation_id, SUM(CASE WHEN is_read = 0 AND direction = 'Incoming' THEN 1 ELSE 0 END) AS unread_count
			FROM `tabFacebook Messenger Chat`
			{where_sql}
			GROUP BY conversation_id
		) unr ON c.conversation_id = unr.conversation_id
		LEFT JOIN (
			SELECT conversation_id, MAX(sender_name) AS sender_name, MAX(sender_id) AS sender_id
			FROM `tabFacebook Messenger Chat`
			WHERE direction = 'Incoming' AND sender_name IS NOT NULL AND sender_name != '' AND sender_name NOT IN ('Paperware Factory', 'Page Admin', 'Page')
			GROUP BY conversation_id
		) cust ON c.conversation_id = cust.conversation_id
		GROUP BY c.conversation_id
		ORDER BY c.timestamp DESC
		LIMIT %(limit_start)s, %(limit)s
	"""

	threads = frappe.db.sql(query, params, as_dict=True)

	for t in threads:
		if not t.get("sender_name") or t["sender_name"] in ("Paperware Factory", "Page Admin", "Facebook Page", "Page", "Facebook Customer"):
			# Try to get incoming sender_name
			inc_name = frappe.db.get_value("Facebook Messenger Chat", {"conversation_id": t["conversation_id"], "direction": "Incoming"}, "sender_name")
			if inc_name and inc_name not in ("Paperware Factory", "Page Admin", "Page"):
				t["sender_name"] = inc_name
			else:
				lead_name = frappe.db.get_value("Lead", {"facebook_psid": t["sender_id"]}, "lead_name")
				if lead_name:
					t["sender_name"] = lead_name

	count_query = f"SELECT COUNT(DISTINCT conversation_id) FROM `tabFacebook Messenger Chat` {where_sql}"
	total_count = frappe.db.sql(count_query, params)[0][0] or 0

	return api_response(success=True, data=threads, total_count=total_count)


@frappe.whitelist()
def get_messages(conversation_id, page=1, limit=50):
	"""Get all messages in a conversation thread."""
	sample_msg = frappe.get_all("Facebook Messenger Chat", filters={"conversation_id": conversation_id}, fields=["page"], limit=1)
	if sample_msg and sample_msg[0].page and not check_portal_permission(sample_msg[0].page, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	limit_start = (int(page) - 1) * int(limit)
	
	messages = frappe.get_all(
		"Facebook Messenger Chat",
		filters={"conversation_id": conversation_id},
		fields=["name", "sender_name", "sender_id", "direction", "timestamp", "message", "is_delivered", "is_read", "attachments"],
		order_by="timestamp asc",
		limit_start=limit_start,
		limit_page_length=limit
	)
	
	frappe.db.set_value(
		"Facebook Messenger Chat",
		{"conversation_id": conversation_id, "direction": "Incoming", "is_read": 0},
		"is_read", 1,
		update_modified=False
	)
	
	return api_response(success=True, data=messages)


@frappe.whitelist()
def send_message(page_id=None, recipient_id=None, message_text=None, page=None, message=None, **kwargs):
	"""Send a message to a customer via Messenger."""
	actual_page_id = page_id or page
	actual_message_text = message_text or message
	actual_recipient_id = recipient_id

	if not actual_message_text or not actual_recipient_id:
		return api_response(success=False, message="Message text and recipient ID are required", status_code=400)

	# 1. Resolve actual page_id if page_id is None, 'all', 'undefined', or doc name
	if not actual_page_id or str(actual_page_id).strip().lower() in ("all", "undefined", "null", "none", ""):
		# Try to find page from existing chat record with this recipient
		sample = frappe.get_all("Facebook Messenger Chat", filters={"conversation_id": f"t_{actual_recipient_id}"}, fields=["page"], limit=1)
		if sample and sample[0].page:
			actual_page_id = sample[0].page
		else:
			pages = get_pages()
			if pages.get("data") and len(pages["data"]) > 0:
				actual_page_id = pages["data"][0].get("name") or pages["data"][0].get("page_id")

	if not actual_page_id:
		return api_response(success=False, message="No active Facebook Page found for sending message", status_code=400)

	if not check_portal_permission(actual_page_id, "can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	client = FacebookGraphClient(page_id=actual_page_id)
	res = client.send_message(actual_recipient_id, actual_message_text)
	
	if res and ("message_id" in res or "recipient_id" in res or res.get("success")):
		page_info = client.get_page_info() or {}
		msg_doc = frappe.get_doc({
			"doctype": "Facebook Messenger Chat",
			"sender_id": str(client.page_id or actual_page_id),
			"sender_name": page_info.get("name", "Page"),
			"page": str(actual_page_id),
			"conversation_id": f"t_{actual_recipient_id}",
			"direction": "Outgoing",
			"message": actual_message_text,
			"timestamp": datetime.now(),
			"is_read": 1
		})
		msg_doc.insert(ignore_permissions=True)
		
		# Explicitly publish realtime event
		try:
			from social_media.facebook.realtime import publish_new_message
			publish_new_message(msg_doc)
		except Exception:
			pass

		try:
			log_doc = frappe.get_doc({
				"doctype": "Facebook Message Log",
				"instance": str(actual_page_id),
				"direction": "Outbound",
				"status": "Sent",
				"timestamp": datetime.now(),
				"sender_psid": str(client.page_id or actual_page_id),
				"recipient_psid": recipient_id,
				"message_id": res.get("message_id", ""),
				"message_text": message_text
			})
			log_doc.insert(ignore_permissions=True)
		except Exception:
			pass
			
		return api_response(success=True, data=msg_doc.as_dict())
		
	return api_response(success=False, message="Failed to send message via Messenger Graph API")


@frappe.whitelist()
def update_conversation_status(conversation_id, status):
	"""Update conversation thread status (Open/Pending/Resolved)."""
	sample_msg = frappe.get_all("Facebook Messenger Chat", filters={"conversation_id": conversation_id}, fields=["page"], limit=1)
	if sample_msg and sample_msg[0].page and not check_portal_permission(sample_msg[0].page, "can_message"):
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
		
	page_ids = resolve_page_ids(page_id)
	filters = []
	if page_ids:
		filters.append(["Facebook Lead", "page", "in", page_ids])
	if status:
		filters.append(["Facebook Lead", "status", "=", status])
		
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
		
	lead_page = getattr(lead_doc, "page", None)
	if not check_portal_permission(lead_page, "can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	from social_media.facebook.leads import create_erpnext_lead
	erpnext_lead_name = create_erpnext_lead(lead_doc)
	
	if erpnext_lead_name:
		setattr(lead_doc, "erpnext_lead", erpnext_lead_name)
		setattr(lead_doc, "status", "Converted")
		lead_doc.save(ignore_permissions=True)
		return api_response(success=True, data={"erpnext_lead": erpnext_lead_name})
		
	return api_response(success=False, message="Failed to create Lead in ERPNext")


# ── Insights & Ads ────────────────────────────────────────────────────

@frappe.whitelist()
def get_page_insights_data(page_id=None, date_from=None, date_to=None):
	"""Get page insights for analytics charts."""
	if page_id and not check_portal_permission(page_id, "can_insights"):
		return api_response(success=False, message="Permission denied", status_code=403)
		
	page_ids = resolve_page_ids(page_id)
	filters = []
	if page_ids:
		filters.append(["Facebook Insight", "page", "in", page_ids])
	if date_from and date_to:
		filters.append(["Facebook Insight", "date", "between", [date_from, date_to]])
		
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

	page_ids = resolve_page_ids(page_id)
	filters = []
	if page_ids:
		filters.append(["Facebook Ad Campaign", "page", "in", page_ids])
		
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
	
	return api_response(success=True, data={
		"graph_api_version": settings.graph_api_version or "v21.0",
		"ai_provider": getattr(settings, "ai_provider", "primellm"),
		"ai_api_url": getattr(settings, "ai_api_url", ""),
		"ai_model_name": getattr(settings, "ai_model_name", ""),
		"enable_auto_post": settings.enable_auto_post,
		"enable_messenger": settings.enable_messenger,
		"enable_ads_management": settings.enable_ads_management,
		"is_connected": settings.is_connected,
	})


@frappe.whitelist()
def save_portal_settings(graph_api_version=None, ai_provider=None, ai_api_url=None, ai_model_name=None, ai_api_key=None):
	"""Save portal settings back to Facebook Settings doctype."""
	if not check_portal_permission(permission_type="can_settings"):
		return api_response(success=False, message="Permission denied", status_code=403)

	try:
		settings = frappe.get_single("Facebook Settings")
		if graph_api_version is not None and hasattr(settings, "graph_api_version"):
			settings.graph_api_version = graph_api_version
		if ai_provider is not None and hasattr(settings, "ai_provider"):
			settings.ai_provider = ai_provider
		if ai_api_url is not None and hasattr(settings, "ai_api_url"):
			settings.ai_api_url = ai_api_url
		if ai_model_name is not None and hasattr(settings, "ai_model_name"):
			settings.ai_model_name = ai_model_name
		if ai_api_key and hasattr(settings, "ai_api_key"):
			settings.ai_api_key = ai_api_key
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		return api_response(success=True, message="Settings saved successfully")
	except Exception as e:
		frappe.log_error("Portal Settings Save Error", str(e))
		return api_response(success=False, message=str(e))


@frappe.whitelist()
def get_media_library(page_id=None, media_type=None, page=1, limit=40):
	"""Get uploaded files/media from Frappe File manager for use in posts."""
	if not check_portal_permission(permission_type="can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)

	filters = {"is_folder": 0}
	if media_type == "Image":
		filters["file_type"] = ("in", ["image/jpeg", "image/png", "image/gif", "image/webp", "jpg", "jpeg", "png", "gif", "webp"])
	elif media_type == "Video":
		filters["file_type"] = ("in", ["video/mp4", "video/webm", "mp4", "webm"])

	limit_start = (int(page) - 1) * int(limit)

	try:
		files = frappe.get_all(
			"File",
			filters=filters,
			fields=["name", "file_name", "file_url", "file_size", "file_type", "creation", "attached_to_doctype"],
			order_by="creation desc",
			limit_start=limit_start,
			limit_page_length=limit,
			ignore_permissions=True
		)

		result = []
		for f in files:
			media_t = "Image"
			if f.file_type and f.file_type.lower() in ("mp4", "webm", "video/mp4", "video/webm"):
				media_t = "Video"
			result.append({
				"name": f.name,
				"title": f.file_name or f.name,
				"file": f.file_url,
				"media_type": media_t,
				"tags": "",
				"usage_count": 0,
				"created": str(f.creation)
			})

		total_count = frappe.db.count("File", filters=filters)
		return api_response(success=True, data=result, total_count=total_count)
	except Exception as e:
		frappe.log_error("Portal Media Library Error", str(e))
		return api_response(success=False, message=str(e))


# ── Ads Management Portal APIs ────────────────────────────────────────────────

@frappe.whitelist()
def get_ads_dashboard(ad_account_id=None):
	"""
	Get aggregated ads dashboard data for the portal.
	Returns summary metrics + campaign list.
	"""
	if not check_portal_permission(permission_type="can_view"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import get_ads_dashboard_data
	result = get_ads_dashboard_data(ad_account_id=ad_account_id)
	return api_response(success=result.get("success", False), data=result)


@frappe.whitelist()
def portal_sync_ad_accounts():
	"""Sync Facebook Ad Accounts from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import sync_ad_accounts
	result = sync_ad_accounts()
	return api_response(success=result.get("success", False), message=result.get("message", ""), data=result)


@frappe.whitelist()
def portal_sync_campaigns(ad_account_id):
	"""Sync campaigns for a given Ad Account from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import sync_campaigns
	result = sync_campaigns(ad_account_id=ad_account_id)
	return api_response(success=result.get("success", False), message=result.get("message", ""), data=result)


@frappe.whitelist()
def portal_create_campaign(ad_account_id, campaign_name, objective,
							daily_budget=None, lifetime_budget=None,
							start_date=None, end_date=None,
							bid_strategy="LOWEST_COST_WITHOUT_CAP",
							special_ad_categories=None):
	"""Create a new campaign from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import create_campaign
	result = create_campaign(
		ad_account_id=ad_account_id,
		campaign_name=campaign_name,
		objective=objective,
		daily_budget=daily_budget,
		lifetime_budget=lifetime_budget,
		start_date=start_date,
		end_date=end_date,
		bid_strategy=bid_strategy,
		special_ad_categories=special_ad_categories,
	)
	return api_response(
		success=result.get("success", False),
		message=result.get("message", result.get("error", "")),
		data=result
	)


@frappe.whitelist()
def portal_pause_campaign(campaign_id):
	"""Pause a campaign from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import pause_campaign
	result = pause_campaign(campaign_id=campaign_id)
	return api_response(success=result.get("success", False), message=result.get("message", result.get("error", "")))


@frappe.whitelist()
def portal_activate_campaign(campaign_id):
	"""Activate a campaign from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import activate_campaign
	result = activate_campaign(campaign_id=campaign_id)
	return api_response(success=result.get("success", False), message=result.get("message", result.get("error", "")))


@frappe.whitelist()
def portal_sync_campaign_insights(campaign_id, date_preset="last_30d"):
	"""Sync campaign insights from the portal."""
	if not check_portal_permission(permission_type="can_view"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import sync_campaign_insights
	result = sync_campaign_insights(campaign_id=campaign_id, date_preset=date_preset)
	return api_response(success=result.get("success", False), message=result.get("message", result.get("error", "")))


@frappe.whitelist()
def portal_get_ad_sets(campaign_id):
	"""Get ad sets for a campaign from the portal."""
	if not check_portal_permission(permission_type="can_view"):
		return api_response(success=False, message="Permission denied")

	adsets = frappe.get_all(
		"Facebook Ad Set",
		filters={"campaign": campaign_id},
		fields=["adset_id", "adset_name", "status", "optimization_goal",
				"billing_event", "daily_budget", "lifetime_budget",
				"targeting_summary", "impressions", "clicks", "spend",
				"cpc", "ctr", "last_synced"]
	)
	return api_response(success=True, data=adsets)


@frappe.whitelist()
def portal_create_ad_set(campaign_id, adset_name, optimization_goal,
						  billing_event, daily_budget=None, lifetime_budget=None,
						  targeting=None):
	"""Create a new ad set from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import create_ad_set
	result = create_ad_set(
		campaign_id=campaign_id,
		adset_name=adset_name,
		optimization_goal=optimization_goal,
		billing_event=billing_event,
		daily_budget=daily_budget,
		lifetime_budget=lifetime_budget,
		targeting=targeting,
	)
	return api_response(
		success=result.get("success", False),
		message=result.get("message", result.get("error", "")),
		data=result
	)


@frappe.whitelist()
def portal_get_ads(adset_id):
	"""Get ads for an ad set from the portal."""
	if not check_portal_permission(permission_type="can_view"):
		return api_response(success=False, message="Permission denied")

	ads = frappe.get_all(
		"Facebook Ad",
		filters={"ad_set": adset_id},
		fields=["ad_id", "ad_name", "status", "creative_type",
				"headline", "body_text", "image_url", "call_to_action",
				"impressions", "clicks", "spend", "cpc", "ctr",
				"conversions", "cost_per_conversion", "last_synced"]
	)
	return api_response(success=True, data=ads)


@frappe.whitelist()
def portal_create_ad(adset_id, ad_name, headline, body_text, destination_url,
					  image_url=None, call_to_action="LEARN_MORE", creative_type="Image"):
	"""Create a new ad from the portal."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied")

	from social_media.facebook.ads import create_ad
	result = create_ad(
		adset_id=adset_id,
		ad_name=ad_name,
		headline=headline,
		body_text=body_text,
		destination_url=destination_url,
		image_url=image_url,
		call_to_action=call_to_action,
		creative_type=creative_type,
	)
	return api_response(
		success=result.get("success", False),
		message=result.get("message", result.get("error", "")),
		data=result
	)


@frappe.whitelist()
def trigger_background_sync(page_id=None):
	"""Trigger background sync of old Facebook Messenger messages."""
	if page_id and str(page_id).strip().lower() in ("all", "undefined", "null", "none", ""):
		page_id = None

	if page_id and not check_portal_permission(page_id, "can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	from social_media.facebook.messenger import enqueue_sync_old_messages
	result = enqueue_sync_old_messages(page_id=page_id)
	return api_response(success=True, message="Background message sync queued successfully", data=result)


@frappe.whitelist()
def get_dashboard_summary(page_id=None):
	"""Get aggregated KPIs and summary data for the portal executive dashboard."""
	if page_id and not check_portal_permission(page_id, "can_view"):
		return api_response(success=False, message="Permission denied", status_code=403)

	page_ids = resolve_page_ids(page_id)

	page_info = {}
	if page_id:
		try:
			doc = frappe.get_doc("Facebook Page", page_id)
			page_info = {
				"page_name": getattr(doc, "page_name", ""),
				"followers_count": getattr(doc, "followers_count", 0) or 0,
				"fan_count": getattr(doc, "fan_count", 0) or 0,
				"profile_picture_url": getattr(doc, "profile_picture_url", None),
				"cover_photo_url": getattr(doc, "cover_photo_url", None)
			}
		except Exception:
			pass
			
	if not page_info:
		try:
			settings = frappe.get_single("Facebook Settings")
			if settings.page_id:
				page_info = {
					"page_name": settings.page_name or "Paperware Factory",
					"followers_count": 0,
					"fan_count": 0,
					"profile_picture_url": None,
					"cover_photo_url": None
				}
		except Exception:
			pass

	post_filters = [["Facebook Post", "page", "in", page_ids]] if page_ids else []
	total_posts = frappe.db.count("Facebook Post", filters=post_filters)

	scheduled_filters = {"publish_status": "Scheduled"}
	if page_ids:
		scheduled_filters["facebook_page"] = ["in", page_ids]
	scheduled_posts = frappe.db.count("Facebook Auto Post Publisher", filters=scheduled_filters)

	lead_filters = [["Facebook Lead", "page", "in", page_ids]] if page_ids else []
	total_leads = frappe.db.count("Facebook Lead", filters=lead_filters)

	new_lead_filters = [["Facebook Lead", "page", "in", page_ids], ["Facebook Lead", "status", "=", "New"]] if page_ids else {"status": "New"}
	new_leads = frappe.db.count("Facebook Lead", filters=new_lead_filters)

	msg_where = "WHERE (page IN %(page_ids)s OR page IS NULL OR page = '') AND is_read = 0 AND direction = 'Incoming'" if page_ids else "WHERE is_read = 0 AND direction = 'Incoming'"
	msg_params = {"page_ids": tuple(page_ids)} if page_ids else {}
	unread_messages = frappe.db.sql(f"SELECT COUNT(*) FROM `tabFacebook Messenger Chat` {msg_where}", msg_params)[0][0] or 0

	conv_where = "WHERE (page IN %(page_ids)s OR page IS NULL OR page = '')" if page_ids else ""
	total_conversations = frappe.db.sql(f"SELECT COUNT(DISTINCT conversation_id) FROM `tabFacebook Messenger Chat` {conv_where}", msg_params)[0][0] or 0

	sent_where = "WHERE (page IN %(page_ids)s OR page IS NULL OR page = '')" if page_ids else ""
	sentiment_data = frappe.db.sql(f"""
		SELECT sentiment, COUNT(*) as count 
		FROM `tabFacebook Comment`
		{sent_where}
		GROUP BY sentiment
	""", msg_params, as_dict=True)

	sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
	for s in sentiment_data:
		if s.sentiment in sentiments:
			sentiments[s.sentiment] = s.count

	camp_filters = [["Facebook Ad Campaign", "page", "in", page_ids], ["Facebook Ad Campaign", "status", "=", "ACTIVE"]] if page_ids else {"status": "ACTIVE"}
	active_campaigns = frappe.db.count("Facebook Ad Campaign", filters=camp_filters)

	spend_where = "WHERE (page IN %(page_ids)s OR page IS NULL OR page = '')" if page_ids else ""
	total_spend_res = frappe.db.sql(f"SELECT SUM(spend) FROM `tabFacebook Ad Campaign` {spend_where}", msg_params)[0][0] or 0.0

	summary = {
		"page_info": page_info,
		"total_posts": total_posts,
		"scheduled_posts": scheduled_posts,
		"total_leads": total_leads,
		"new_leads": new_leads,
		"unread_messages": unread_messages,
		"total_conversations": total_conversations,
		"sentiments": sentiments,
		"active_campaigns": active_campaigns,
		"total_ad_spend": round(float(total_spend_res), 2)
	}

	return api_response(success=True, data=summary)


@frappe.whitelist()
def generate_ai_caption(topic, tone="engaging"):
	"""Generate a Facebook post caption using AI based on a topic."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied", status_code=403)

	prompt = f"Write an engaging, professional Facebook post caption for a business page about: '{topic}'. Tone: {tone}. Include relevant hashtags and emojis."
	try:
		from social_media.facebook.ai_agent import call_llm
		result = call_llm(prompt, system_instruction="You are an expert social media manager writing Facebook post captions.")
		if not result:
			result = f"🚀 Exciting news about {topic}! Stay tuned for more updates. #Business #Facebook #Innovation"
		return api_response(success=True, data={"caption": result})
	except Exception as e:
		fallback = f"✨ Discover how {topic} can transform your experience! Learn more today. #Facebook #Update"
		return api_response(success=True, data={"caption": fallback})


@frappe.whitelist()
def generate_ai_chat_reply(customer_message, sender_name="Customer"):
	"""Generate a smart AI suggestion for customer Messenger messages."""
	if not check_portal_permission(permission_type="can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	prompt = f"Customer '{sender_name}' sent the following message: '{customer_message}'. Generate a helpful, friendly, professional reply for our Facebook customer support agent."
	try:
		from social_media.facebook.ai_agent import call_llm
		result = call_llm(prompt, system_instruction="You are a helpful customer support agent for a Facebook business page.")
		if not result:
			result = f"Hello {sender_name}! Thank you for reaching out. How can I help you further?"
		return api_response(success=True, data={"reply": result})
	except Exception as e:
		fallback = f"Hi {sender_name}, thanks for messaging us! How can we assist you today?"
		return api_response(success=True, data={"reply": fallback})


def send_message_internal(page_id, recipient_id, message_text):
	"""Internal helper to send Messenger message and create doc record."""
	from social_media.facebook.graph_client import FacebookGraphClient
	client = FacebookGraphClient(page_id=page_id)
	res = client.send_message(recipient_id, message_text)
	
	if res and "message_id" in res:
		chat_doc = frappe.get_doc({
			"doctype": "Facebook Messenger Chat",
			"sender_id": recipient_id,
			"sender_name": "Page Admin",
			"page": page_id or "all",
			"conversation_id": f"t_{recipient_id}",
			"message": message_text,
			"direction": "Outgoing",
			"is_read": 1
		})
		chat_doc.insert(ignore_permissions=True)
		frappe.db.commit()
		
		try:
			from social_media.facebook.realtime import publish_new_message
			publish_new_message(chat_doc)
		except Exception:
			pass
		return True
	return False


# ── Complaint Handling Endpoints ─────────────────────────────────────

@frappe.whitelist()
def get_complaints(page_id=None, status=None):
	"""Get all customer complaints flagged by AI or team."""
	if not check_portal_permission(page_id, "can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	filters = [["Facebook Messenger Chat", "is_complaint", "=", 1]]
	page_ids = resolve_page_ids(page_id)
	if page_ids:
		filters.append(["Facebook Messenger Chat", "page", "in", page_ids])

	if status and str(status).strip() and str(status).lower() != "all":
		filters.append(["Facebook Messenger Chat", "complaint_status", "=", status])

	complaints = frappe.get_all(
		"Facebook Messenger Chat",
		filters=filters,
		fields=[
			"name", "sender_id", "sender_name", "page", "conversation_id",
			"message", "timestamp", "is_complaint", "complaint_status",
			"priority", "assigned_agent", "tags"
		],
		order_by="timestamp desc",
		ignore_permissions=True
	)

	return api_response(success=True, data=complaints)


@frappe.whitelist()
def update_complaint_status(chat_name, complaint_status="Open", priority=None, assigned_agent=None):
	"""Update complaint status, priority, or assigned agent."""
	if not check_portal_permission(permission_type="can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	try:
		doc = frappe.get_doc("Facebook Messenger Chat", chat_name)
		doc.complaint_status = complaint_status
		if priority:
			doc.priority = priority
		if assigned_agent is not None:
			doc.assigned_agent = assigned_agent
		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return api_response(success=True, message=f"Complaint updated to {complaint_status}")
	except Exception as e:
		return api_response(success=False, message=str(e), status_code=500)


# ── Agent & Moderator Management Endpoints ───────────────────────────

@frappe.whitelist()
def get_team_members():
	"""Fetch team members, their Facebook Page assignments, and system users."""
	if not check_portal_permission(permission_type="can_settings"):
		return api_response(success=False, message="Permission denied", status_code=403)

	settings = frappe.get_single("Facebook Settings")
	roles = settings.get("team_roles") or []

	team_members = []
	for r in roles:
		user_fullname = frappe.utils.get_fullname(r.user)
		team_members.append({
			"name": r.name,
			"user": r.user,
			"user_fullname": user_fullname,
			"page": r.page,
			"can_post": getattr(r, "can_post", 0),
			"can_comment": getattr(r, "can_comment", 0),
			"can_message": getattr(r, "can_message", 0),
			"can_ads": getattr(r, "can_ads", 0),
			"can_insights": getattr(r, "can_insights", 0),
			"can_settings": getattr(r, "can_settings", 0)
		})

	# Get all active system users for selection dropdown
	system_users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "email"],
		order_by="full_name asc",
		ignore_permissions=True
	)

	return api_response(success=True, data={
		"team_members": team_members,
		"system_users": system_users
	})


@frappe.whitelist()
def save_team_member(user, page, can_post=0, can_comment=0, can_message=0, can_ads=0, can_insights=0, can_settings=0):
	"""Add or update an agent/moderator page role in Facebook Settings."""
	if not check_portal_permission(permission_type="can_settings"):
		return api_response(success=False, message="Permission denied", status_code=403)

	if not user or not page:
		return api_response(success=False, message="User and Page are required", status_code=400)

	settings = frappe.get_single("Facebook Settings")
	roles = settings.get("team_roles") or []

	# Check if role entry already exists for user + page
	existing = None
	for r in roles:
		if r.user == user and r.page == page:
			existing = r
			break

	if existing:
		existing.can_post = int(can_post)
		existing.can_comment = int(can_comment)
		existing.can_message = int(can_message)
		existing.can_ads = int(can_ads)
		existing.can_insights = int(can_insights)
		existing.can_settings = int(can_settings)
	else:
		settings.append("team_roles", {
			"user": user,
			"page": page,
			"can_post": int(can_post),
			"can_comment": int(can_comment),
			"can_message": int(can_message),
			"can_ads": int(can_ads),
			"can_insights": int(can_insights),
			"can_settings": int(can_settings)
		})

	settings.save(ignore_permissions=True)
	frappe.db.commit()

	return api_response(success=True, message="Agent & Moderator role saved successfully")


@frappe.whitelist()
def remove_team_member(user, page):
	"""Remove a user's page assignment."""
	if not check_portal_permission(permission_type="can_settings"):
		return api_response(success=False, message="Permission denied", status_code=403)

	settings = frappe.get_single("Facebook Settings")
	roles = settings.get("team_roles") or []

	new_roles = [r for r in roles if not (r.user == user and r.page == page)]
	settings.set("team_roles", new_roles)
	settings.save(ignore_permissions=True)
	frappe.db.commit()

	return api_response(success=True, message="Team member role removed")


@frappe.whitelist()
def flag_chat_as_complaint(conversation_id, priority="High"):
	"""Flag an entire conversation as a complaint."""
	if not check_portal_permission(permission_type="can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	frappe.db.sql("""
		UPDATE `tabFacebook Messenger Chat`
		SET is_complaint = 1, complaint_status = 'Open', priority = %s
		WHERE conversation_id = %s
	""", (priority, conversation_id))
	frappe.db.commit()

	return api_response(success=True, message="Conversation flagged as Complaint")


@frappe.whitelist()
def create_lead_from_chat(sender_id, sender_name="Facebook Customer"):
	"""Create a new ERPNext Lead from a Messenger conversation."""
	if not check_portal_permission(permission_type="can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	try:
		# Check if Lead already exists
		existing_lead = frappe.db.get_value("Lead", {"facebook_psid": sender_id}, "name")
		if not existing_lead:
			existing_lead = frappe.db.get_value("Lead", {"lead_name": sender_name}, "name")

		if existing_lead:
			return api_response(success=True, data={"erpnext_lead": existing_lead}, message="Lead already exists in ERPNext")

		lead_doc = {
			"doctype": "Lead",
			"lead_name": sender_name,
			"source": "Facebook Messenger"
		}
		if frappe.db.has_column("Lead", "facebook_psid"):
			lead_doc["facebook_psid"] = sender_id

		lead = frappe.get_doc(lead_doc)
		lead.insert(ignore_permissions=True)
		frappe.db.commit()

		return api_response(success=True, data={"erpnext_lead": lead.name}, message="ERPNext Lead created successfully")
	except Exception as e:
		return api_response(success=False, message=str(e), status_code=500)


@frappe.whitelist()
def get_session():
	"""Get current session user info, CSRF token, and permissions."""
	user = frappe.session.user
	if user == "Guest":
		return api_response(success=False, message="Not logged in", status_code=401)

	full_name = frappe.db.get_value("User", user, "full_name") or user
	user_image = frappe.db.get_value("User", user, "user_image") or ""
	roles = frappe.get_roles(user)
	is_admin = "System Manager" in roles or user == "Administrator"

	csrf_token = None
	try:
		csrf_token = frappe.sessions.get_csrf_token()
	except Exception:
		pass

	return api_response(success=True, data={
		"user": user,
		"full_name": full_name,
		"user_image": user_image,
		"roles": roles,
		"is_admin": is_admin,
		"csrf_token": csrf_token
	})


@frappe.whitelist()
def assign_conversation(sender_id, assigned_agent=None):
	"""Assign all messages in a conversation / sender_id to a specific agent."""
	if not check_portal_permission(permission_type="can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	frappe.db.sql("""
		UPDATE `tabFacebook Messenger Chat`
		SET assigned_agent = %s
		WHERE sender_id = %s OR conversation_id = %s
	""", (assigned_agent, sender_id, sender_id))
	frappe.db.commit()

	return api_response(success=True, message=f"Conversation assigned to {assigned_agent or 'Unassigned'}")


@frappe.whitelist()
def mark_read_by_sender(sender_id):
	"""Mark all incoming messages from a sender as read."""
	if not check_portal_permission(permission_type="can_message"):
		return api_response(success=False, message="Permission denied", status_code=403)

	frappe.db.sql("""
		UPDATE `tabFacebook Messenger Chat`
		SET is_read = 1
		WHERE sender_id = %s AND direction = 'Incoming'
	""", (sender_id,))
	frappe.db.commit()

	return api_response(success=True, message="Messages marked as read")


@frappe.whitelist()
def approve_ai_reply(name):
	"""Approve an AI-generated comment reply and publish it."""
	if not check_portal_permission(permission_type="can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)

	try:
		reply_doc = frappe.get_doc("Facebook AI Comment Reply", name)
		reply_doc.approval_status = "Approved"
		reply_doc.approved_by = frappe.session.user
		reply_doc.save(ignore_permissions=True)

		try:
			from social_media.facebook.ai_agent import publish_approved_reply
			publish_approved_reply(reply_doc)
		except Exception:
			pass

		frappe.db.commit()
		return api_response(success=True, message="AI Reply approved")
	except Exception as e:
		return api_response(success=False, message=str(e), status_code=500)


@frappe.whitelist()
def reject_ai_reply(name):
	"""Reject an AI-generated comment reply."""
	if not check_portal_permission(permission_type="can_comment"):
		return api_response(success=False, message="Permission denied", status_code=403)

	try:
		reply_doc = frappe.get_doc("Facebook AI Comment Reply", name)
		reply_doc.approval_status = "Rejected"
		reply_doc.save(ignore_permissions=True)
		frappe.db.commit()
		return api_response(success=True, message="AI Reply rejected")
	except Exception as e:
		return api_response(success=False, message=str(e), status_code=500)


@frappe.whitelist()
def get_ai_replies(comment_id=None, approval_status=None):
	"""Get list of Facebook AI Comment Reply docs."""
	filters = {}
	if comment_id:
		filters["comment_id"] = comment_id
	if approval_status:
		filters["approval_status"] = approval_status

	replies = frappe.get_all(
		"Facebook AI Comment Reply",
		fields=["name", "comment_id", "original_comment", "comment_author", "post_id", "ai_model", "sentiment", "sentiment_score", "confidence_score", "generated_reply", "approval_status", "approved_by", "is_published", "creation"],
		filters=filters,
		order_by="creation desc"
	)
	return api_response(success=True, data=replies)


@frappe.whitelist()
def schedule_post(name, scheduled_datetime):
	"""Schedule or reschedule a Content Calendar post or Auto Post Publisher."""
	if not check_portal_permission(permission_type="can_post"):
		return api_response(success=False, message="Permission denied", status_code=403)

	try:
		if frappe.db.exists("Facebook Content Calendar", name):
			cal_doc = frappe.get_doc("Facebook Content Calendar", name)
			dt_parts = str(scheduled_datetime).split(" ")
			cal_doc.scheduled_date = dt_parts[0]
			if len(dt_parts) > 1:
				cal_doc.scheduled_time = dt_parts[1]
			cal_doc.status = "Scheduled"
			cal_doc.save(ignore_permissions=True)

			if cal_doc.post:
				publisher = frappe.get_doc("Facebook Auto Post Publisher", cal_doc.post)
				publisher.schedule_datetime = scheduled_datetime
				publisher.publish_status = "Scheduled"
				publisher.save(ignore_permissions=True)

		elif frappe.db.exists("Facebook Auto Post Publisher", name):
			publisher = frappe.get_doc("Facebook Auto Post Publisher", name)
			publisher.schedule_datetime = scheduled_datetime
			publisher.publish_status = "Scheduled"
			publisher.save(ignore_permissions=True)

		frappe.db.commit()
		return api_response(success=True, message="Post scheduled successfully")
	except Exception as e:
		return api_response(success=False, message=str(e), status_code=500)


@frappe.whitelist()
def get_ads_tree(account=None):
	"""Get hierarchical tree of Campaigns -> Ad Sets -> Ads."""
	if not check_portal_permission(permission_type="can_ads"):
		return api_response(success=False, message="Permission denied", status_code=403)

	campaign_filters = {}
	if account:
		campaign_filters["ad_account"] = account

	campaigns = frappe.get_all(
		"Facebook Ad Campaign",
		fields=["name", "campaign_id", "campaign_name", "ad_account", "status", "objective", "daily_budget", "lifetime_budget", "impressions", "clicks", "spend", "cpc", "ctr"],
		filters=campaign_filters,
		order_by="creation desc"
	)

	for camp in campaigns:
		adsets = frappe.get_all(
			"Facebook Ad Set",
			fields=["name", "adset_id", "adset_name", "campaign", "status", "daily_budget", "impressions", "clicks", "spend", "cpc", "ctr"],
			filters={"campaign": camp["name"]}
		)
		for adset in adsets:
			ads = frappe.get_all(
				"Facebook Ad",
				fields=["name", "ad_id", "ad_name", "ad_set", "campaign", "status", "creative_type", "headline", "body_text", "image_url", "impressions", "clicks", "spend", "conversions"],
				filters={"ad_set": adset["name"]}
			)
			adset["ads"] = ads
		camp["ad_sets"] = adsets

	return api_response(success=True, data=campaigns)

