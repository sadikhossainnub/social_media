import frappe
from frappe import _


def get_context(context):
	context.title = _("Send Message")
	context.platforms = ["Facebook", "Instagram", "WhatsApp"]
	context.message_types = ["text", "image", "video", "audio"]
	
	return context