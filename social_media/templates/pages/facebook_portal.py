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
		pages = frappe.get_all("Facebook Page", fields=["name", "page_name", "profile_picture_url"])
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
					fields=["name", "page_name", "profile_picture_url"]
				)
		except Exception:
			pass

	portal_data = {
		"userFullName": frappe.utils.get_fullname(frappe.session.user),
		"userEmail": frappe.session.user,
		"csrfToken": frappe.local.session.data.csrf_token,
		"pages": [dict(p) for p in pages],
		"permissions": permissions,
		"isAdmin": is_admin
	}

	# Read the static HTML file (no Jinja syntax inside)
	html_path = os.path.join(
		os.path.dirname(__file__),
		"facebook_portal_app.html"
	)

	if not os.path.exists(html_path):
		frappe.throw("Portal HTML file not found: facebook_portal_app.html")

	with open(html_path, "r", encoding="utf-8") as f:
		html = f.read()

	# Inject server data as a JS global before </head>
	portal_data_json = json.dumps(portal_data, ensure_ascii=False)
	inject_script = f"<script>\nwindow.fbPortalData = {portal_data_json};\n</script>\n</head>"
	html = html.replace("</head>", inject_script, 1)

	# Serve raw HTML, bypassing Jinja2 entirely
	frappe.local.response["type"] = "page"
	frappe.local.response["page_content"] = html
	context.no_cache = 1
