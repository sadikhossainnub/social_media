import frappe

def execute():
	"""Create Facebook roles if they do not exist."""
	roles = ["Facebook Manager", "Facebook Agent", "Facebook Viewer"]
	for role_name in roles:
		if not frappe.db.exists("Role", role_name):
			role = frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1
			})
			role.insert(ignore_permissions=True)
