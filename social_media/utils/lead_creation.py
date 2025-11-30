import frappe
from frappe import _


def create_lead_from_message(message_doc):
	"""Create Lead from social media message"""
	
	# Check if lead already exists for this contact
	existing_lead = None
	
	if message_doc.doctype == "WhatsApp Message":
		existing_lead = frappe.db.exists("Lead", {"whatsapp_no": message_doc.phone_number})
		if not existing_lead:
			existing_lead = frappe.db.exists("Lead", {"mobile_no": message_doc.phone_number})
	
	elif message_doc.doctype in ["Facebook Message", "Instagram Message"]:
		# Check by sender_id or create custom field for social media IDs
		pass
	
	if existing_lead:
		return existing_lead
	
	# Create new lead
	lead = frappe.new_doc("Lead")
	
	# Set basic info based on message type
	if message_doc.doctype == "WhatsApp Message":
		lead.update({
			"first_name": message_doc.contact_name or "WhatsApp Contact",
			"whatsapp_no": message_doc.phone_number,
			"mobile_no": message_doc.phone_number,
			"source": "WhatsApp"
		})
	
	elif message_doc.doctype == "Facebook Message":
		lead.update({
			"first_name": f"Facebook User {message_doc.sender_id}",
			"source": "Facebook"
		})
	
	elif message_doc.doctype == "Instagram Message":
		lead.update({
			"first_name": f"Instagram User {message_doc.sender_id}",
			"source": "Instagram"
		})
	
	# Common fields
	lead.update({
		"status": "Lead",
		"lead_owner": frappe.session.user,
		"company": frappe.defaults.get_user_default("Company")
	})
	
	lead.insert(ignore_permissions=True)
	
	# Link message to lead
	message_doc.db_set("lead", lead.name)
	
	return lead.name


@frappe.whitelist()
def auto_create_leads_from_messages():
	"""Background job to create leads from unprocessed messages"""
	
	# Get unprocessed WhatsApp messages
	wa_messages = frappe.get_all(
		"WhatsApp Message",
		filters={"lead": ["is", "not set"]},
		fields=["name"]
	)
	
	for msg in wa_messages:
		message_doc = frappe.get_doc("WhatsApp Message", msg.name)
		try:
			create_lead_from_message(message_doc)
		except Exception as e:
			frappe.log_error(f"Auto lead creation failed for {msg.name}: {str(e)}")
	
	# Get unprocessed Facebook messages
	fb_messages = frappe.get_all(
		"Facebook Message",
		filters={"lead": ["is", "not set"]},
		fields=["name"]
	)
	
	for msg in fb_messages:
		message_doc = frappe.get_doc("Facebook Message", msg.name)
		try:
			create_lead_from_message(message_doc)
		except Exception as e:
			frappe.log_error(f"Auto lead creation failed for {msg.name}: {str(e)}")
	
	# Get unprocessed Instagram messages
	ig_messages = frappe.get_all(
		"Instagram Message",
		filters={"lead": ["is", "not set"]},
		fields=["name"]
	)
	
	for msg in ig_messages:
		message_doc = frappe.get_doc("Instagram Message", msg.name)
		try:
			create_lead_from_message(message_doc)
		except Exception as e:
			frappe.log_error(f"Auto lead creation failed for {msg.name}: {str(e)}")
	
	return {"success": True, "message": "Auto lead creation completed"}