# Copyright (c) 2026, Prime Technology and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FacebookAd(Document):
	def before_save(self):
		"""Auto-fill campaign and ad_account from ad_set."""
		if self.ad_set:
			adset_doc = frappe.get_doc("Facebook Ad Set", self.ad_set)
			if not self.campaign:
				self.campaign = adset_doc.campaign
			if not self.ad_account:
				self.ad_account = adset_doc.ad_account
