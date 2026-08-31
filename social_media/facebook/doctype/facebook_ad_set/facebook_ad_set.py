# Copyright (c) 2026, Prime Technology and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FacebookAdSet(Document):
	def before_save(self):
		"""Auto-set ad_account from campaign if not set."""
		if self.campaign and not self.ad_account:
			self.ad_account = frappe.db.get_value(
				"Facebook Ad Campaign", self.campaign, "ad_account"
			)
