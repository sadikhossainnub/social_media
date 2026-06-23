# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.facebook.utils import (
	get_lead_form_details,
	get_lead_form_leads
)


class FacebookLeadForm(Document):
    def after_insert(self):
        """Fetch form details when form is created."""
        self.fetch_form_details()

    @frappe.whitelist()
    def fetch_form_details(self):
        """Fetch form details from Facebook."""
        try:
            response = get_lead_form_details(
                form_id=self.form_id,
                access_token=self.get_page_access_token()
            )
            if response:
                import json
                self.form_fields = json.dumps(response.get("questions", []), indent=2)
                self.created_time = response.get("created_time")
                self.updated_time = response.get("updated_time")
                self.save()
                frappe.msgprint("Form details fetched")
        except Exception as e:
            frappe.msgprint(f"Failed to fetch form details: {str(e)}")

    def get_page_access_token(self):
        """Get access token for the associated page."""
        return frappe.db.get_value("Facebook Page", self.page, "access_token")

    @frappe.whitelist()
    def sync_leads(self):
        """Sync leads from this form."""
        try:
            leads = get_lead_form_leads(
                form_id=self.form_id,
                access_token=self.get_page_access_token()
            )
            if leads and leads.get("data"):
                for lead in leads["data"]:
                    self.create_lead_from_facebook(lead)
                self.last_synced_on = frappe.utils.now()
                self.sync_count = (self.sync_count or 0) + len(leads["data"])
                self.save()
                frappe.msgprint(f"Synced {len(leads['data'])} leads")
        except Exception as e:
            frappe.msgprint(f"Failed to sync leads: {str(e)}")

    def create_lead_from_facebook(self, lead_data):
        """Create an ERPNext Lead from Facebook lead data."""
        try:
            # Get field mappings
            name_field = self.lead_name_field or "full_name"
            mobile_field = self.mobile_field or "mobile_number"
            email_field = self.email_field or "email"

            # Extract values from lead data
            lead_data_dict = lead_data.get("field_data", [])
            values = {}
            for item in lead_data_dict:
                field_name = item.get("name", "")
                value = item.get("values", [])[0] if item.get("values") else ""
                values[field_name] = value

            # Create lead
            lead = frappe.new_doc("Lead")
            lead.lead_name = values.get(name_field, "Facebook Lead")
            lead.mobile_no = values.get(mobile_field, "")
            lead.email_id = values.get(email_field, "")
            lead.source = "Facebook Ads"
            lead.facebook_lead_form = self.name
            lead.facebook_lead_id = lead_data.get("id")

            # Map other fields
            for mapping in self.other_fields:
                fb_field = mapping.facebook_field
                erp_field = mapping.erpnext_field
                if fb_field in values:
                    setattr(lead, erp_field, values[fb_field])

            lead.insert(ignore_permissions=True)
            frappe.db.commit()
            return lead.name
        except Exception as e:
            frappe.log_error(
                title="Facebook Lead Form Create Lead Error",
                message=f"Lead: {lead_data.get('id')}\n{str(e)}"
            )
            return None


class FacebookLeadFormFieldMapping(Document):
    pass
