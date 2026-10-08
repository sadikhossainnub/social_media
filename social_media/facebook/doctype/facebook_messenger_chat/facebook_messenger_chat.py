# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FacebookMessengerChat(Document):
	def after_insert(self):
		try:
			from social_media.facebook.realtime import publish_new_message
			publish_new_message(self)
		except Exception:
			pass

