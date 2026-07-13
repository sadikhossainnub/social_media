import frappe

def execute():
	"""
	Sets default graph_api_version = 'v21.0' in Facebook Settings if not set.
	"""
	if not frappe.db.exists("DocType", "Facebook Settings"):
		return

	try:
		doc = frappe.get_doc("Facebook Settings")
		if not doc.graph_api_version:
			doc.graph_api_version = "v21.0"
			doc.save(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(f"Error setting default Graph API version: {str(e)}", "Migration Patch")
