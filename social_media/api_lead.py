import frappe
from frappe import _
from social_media.utils.lead_creation import create_lead_from_message, auto_create_leads_from_messages


@frappe.whitelist()
def create_lead_from_social_message(message_type, message_id):
	"""Manually create lead from social media message"""
	
	try:
		message_doc = frappe.get_doc(message_type, message_id)
		lead_name = create_lead_from_message(message_doc)
		
		return {
			"success": True,
			"message": f"Lead {lead_name} created successfully",
			"lead_name": lead_name
		}
		
	except Exception as e:
		frappe.log_error(f"Manual lead creation failed: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_lead_stats():
	"""Get lead creation statistics"""
	
	stats = {}
	
	# WhatsApp leads
	stats["whatsapp"] = {
		"total_messages": frappe.db.count("WhatsApp Message"),
		"leads_created": frappe.db.count("WhatsApp Message", {"lead": ["!=", ""]}),
		"pending": frappe.db.count("WhatsApp Message", {"lead": ["is", "not set"]})
	}
	
	# Facebook leads
	stats["facebook"] = {
		"total_messages": frappe.db.count("Facebook Message"),
		"leads_created": frappe.db.count("Facebook Message", {"lead": ["!=", ""]}),
		"pending": frappe.db.count("Facebook Message", {"lead": ["is", "not set"]})
	}
	
	# Instagram leads
	stats["instagram"] = {
		"total_messages": frappe.db.count("Instagram Message"),
		"leads_created": frappe.db.count("Instagram Message", {"lead": ["!=", ""]}),
		"pending": frappe.db.count("Instagram Message", {"lead": ["is", "not set"]})
	}
	
	return stats


@frappe.whitelist()
def run_auto_lead_creation():
	"""Manually trigger auto lead creation"""
	return auto_create_leads_from_messages()