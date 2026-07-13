import frappe

def execute():
	"""
	Migrates access_token field type in Facebook Page DocType (if data exists).
	"""
	# In Frappe, changing field type from Small Text to Password encrypts it during save.
	# We just need to load the documents and save them to force encryption if they aren't already.
	if not frappe.db.table_exists("Facebook Page"):
		return

	pages = frappe.get_all("Facebook Page", fields=["name", "access_token"])
	for page in pages:
		if page.access_token and not page.access_token.startswith("★"):
			# Load document and save to encrypt the token
			try:
				doc = frappe.get_doc("Facebook Page", page.name)
				# Resetting it forces encryption because the field type is now Password
				doc.access_token = page.access_token
				doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error encrypting access token for page {page.name}: {str(e)}", "Migration Patch")
