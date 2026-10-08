import frappe
import json
import os


def get_context(context):
	# Redirect guests to login
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/facebook_portal"
		raise frappe.Redirect

	# Gather server data
	is_admin = "System Manager" in frappe.get_roles() or frappe.session.user == "Administrator"

	pages = []
	permissions = {}

	if is_admin:
		pages = frappe.get_all("Facebook Page", fields=["name", "page_name", "profile_picture_url", "followers_count", "fan_count"], ignore_permissions=True)
		for p in pages:
			permissions[p.name] = {
				"can_post": 1,
				"can_comment": 1,
				"can_message": 1,
				"can_ads": 1,
				"can_insights": 1,
				"can_settings": 1
			}
	else:
		try:
			settings = frappe.get_single("Facebook Settings")
			roles = settings.get("team_roles") or []
			if not roles:
				pages = frappe.get_all("Facebook Page", fields=["name", "page_name", "profile_picture_url", "followers_count", "fan_count"], ignore_permissions=True)
				for p in pages:
					permissions[p.name] = {
						"can_post": 1,
						"can_comment": 1,
						"can_message": 1,
						"can_ads": 1,
						"can_insights": 1,
						"can_settings": 1
					}
			else:
				for r in roles:
					if r.user == frappe.session.user:
						permissions[r.page] = {
							"can_post": r.can_post,
							"can_comment": r.can_comment,
							"can_message": r.can_message,
							"can_ads": r.can_ads,
							"can_insights": r.can_insights,
							"can_settings": r.can_settings
						}
				allowed_names = list(permissions.keys())
				if allowed_names:
					pages = frappe.get_all(
						"Facebook Page",
						filters={"name": ["in", allowed_names]},
						fields=["name", "page_name", "profile_picture_url", "followers_count", "fan_count"],
						ignore_permissions=True
					)
		except Exception:
			pages = frappe.get_all("Facebook Page", fields=["name", "page_name", "profile_picture_url", "followers_count", "fan_count"], ignore_permissions=True)

	# Fallback: use Facebook Settings connected page if no Facebook Page records
	if not pages:
		try:
			settings = frappe.get_single("Facebook Settings")
			if settings.page_id:
				pages = [{
					"name": settings.page_id,
					"page_name": settings.page_name or "Paperware Factory",
					"profile_picture_url": "",
					"followers_count": 0,
					"fan_count": 0
				}]
				permissions[settings.page_id] = {
					"can_post": 1,
					"can_comment": 1,
					"can_message": 1,
					"can_ads": 1,
					"can_insights": 1,
					"can_settings": 1
				}
		except Exception:
			pass

	portal_data = {
		"userFullName": frappe.utils.get_fullname(frappe.session.user),
		"userEmail": frappe.session.user,
		"csrfToken": frappe.local.session.data.csrf_token if frappe.local.session else "",
		"pages": [dict(p) for p in pages],
		"permissions": permissions,
		"isAdmin": is_admin
	}

	context.no_cache = 1
	context.safe_render = False
	context.portal_data_json = json.dumps(portal_data, ensure_ascii=False, default=str)

