"""
Facebook Lead Ads Integration
Handles lead generation from Facebook Lead Forms
"""

import frappe
import json
import requests
from datetime import datetime
from .utils import create_facebook_lead, make_graph_request


@frappe.whitelist(allow_guest=True)
def webhook():
    """
    Webhook endpoint for Facebook Lead Ads.
    Handles both verification (GET) and lead data (POST).
    """
    # Handle GET request for webhook verification
    if frappe.request.method == "GET":
        return handle_verification()
    
    # Handle POST request for lead data
    if frappe.request.method != "POST":
        return
    
    try:
        data = frappe.request.get_json()
        if not data:
            return
        
        object_type = data.get("object")
        
        if object_type == "page":
            handle_lead_event(data)
        
        return "OK"
        
    except Exception as e:
        frappe.log_error(
            title="Facebook Lead Webhook Error",
            message=str(e)
        )
        return "Error"


def handle_verification():
    """Handle webhook verification request from Facebook."""
    verify_token = frappe.request.args.get("hub.verify_token")
    mode = frappe.request.args.get("hub.mode")
    challenge = frappe.request.args.get("hub.challenge")
    
    if mode and challenge:
        settings = frappe.get_single("Facebook Settings")
        if verify_token == settings.messenger_verify_token:
            return challenge
    
    return "Invalid request"


def handle_lead_event(data):
    """Handle lead generation events from Facebook."""
    entry = data.get("entry", [])
    
    for entry_data in entry:
        changes = entry_data.get("changes", [])
        
        for change in changes:
            if change.get("field") == "lead_generation":
                value = change.get("value", {})
                leadgen_id = value.get("leadgen_id")
                form_id = value.get("form_id")
                
                if leadgen_id:
                    # Fetch full lead details
                    lead_details = get_lead_details(leadgen_id)
                    
                    if lead_details:
                        # Create Facebook Lead record
                        create_facebook_lead(lead_details)
                        
                        # Auto-create ERPNext Lead if enabled
                        if frappe.get_single("Facebook Settings").enable_lead_ads:
                            create_erpnext_lead(lead_details)


def get_lead_details(lead_id):
    """
    Fetch full lead details from Facebook.
    
    Args:
        lead_id: Facebook lead ID
    
    Returns:
        dict: Lead details or None on error
    """
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return None
    
    params = {
        "access_token": settings.page_access_token,
        "fields": "id,form_id,created_time,field_data,ad_id,ad_name,campaign_id,campaign_name"
    }
    
    url = f"https://graph.facebook.com/v18.0/{lead_id}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        if response.status_code != 200 or "error" in result:
            frappe.log_error(f"Lead fetch failed: {result}", "Facebook Leads")
            return None
        
        # Parse field_data
        field_data = result.get("field_data", [])
        parsed_data = parse_field_data(field_data)
        result.update(parsed_data)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Lead fetch error: {str(e)}", "Facebook Leads")
        return None


def parse_field_data(field_data):
    """
    Parse Facebook lead field_data into a flat dictionary.
    
    Args:
        field_data: List of field objects from Facebook
    
    Returns:
        dict: Parsed field data
    """
    parsed = {}
    
    for field in field_data:
        name = field.get("name", "")
        values = field.get("values", [])
        
        if values:
            parsed[name] = values[0] if len(values) == 1 else values
    
    return parsed


def create_erpnext_lead(lead_data):
    """
    Create ERPNext Lead from Facebook lead data.
    
    Args:
        lead_data: Facebook lead details
    """
    try:
        # Check if customer already exists
        email = lead_data.get("email", "")
        phone = lead_data.get("phone", "")
        
        existing_customer = None
        
        if email:
            existing_customer = frappe.db.get_value(
                "Customer",
                {"email_id": email},
                "name"
            )
        
        if not existing_customer and phone:
            existing_customer = frappe.db.get_value(
                "Customer",
                {"phone_no": phone},
                "name"
            )
        
        # Create or update customer
        if existing_customer:
            customer = frappe.get_doc("Customer", existing_customer)
        else:
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": lead_data.get("full_name", "Unknown"),
                "email_id": email,
                "phone_no": phone,
                "customer_type": "Individual"
            })
            customer.insert(ignore_permissions=True)
        
        # Create Lead
        lead = frappe.get_doc({
            "doctype": "Lead",
            "lead_name": lead_data.get("full_name", "Unknown"),
            "email_id": email,
            "phone": phone,
            "company_name": lead_data.get("company", ""),
            "source": "Facebook Lead Ad",
            "facebook_lead_id": lead_data.get("id"),
            "lead_owner": frappe.session.user
        })
        
        lead.insert(ignore_permissions=True)
        
        # Update Facebook Lead with ERPNext Lead reference
        frappe.db.set_value(
            "Facebook Lead",
            {"facebook_lead_id": lead_data.get("id")},
            "erpnext_lead",
            lead.name
        )
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error creating ERPNext lead: {str(e)}", "Facebook Leads")


@frappe.whitelist()
def sync_leads(form_id=None):
    """
    Manually sync leads from Facebook.
    
    Args:
        form_id: Optional form ID to sync specific form
    
    Returns:
        dict: Sync result
    """
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return {"success": False, "error": "Facebook not connected"}
    
    try:
        # Get all lead forms or specific form
        if form_id:
            forms = [{"id": form_id}]
        else:
            forms_result = make_graph_request("/me/leadgen_forms", method="GET")
            forms = forms_result.get("data", []) if forms_result else []
        
        total_leads = 0
        
        for form in forms:
            form_id = form.get("id")
            
            # Get leads for this form
            leads_result = make_graph_request(f"/{form_id}/leads", method="GET")
            
            if not leads_result:
                continue
            
            leads = leads_result.get("data", [])
            
            for lead in leads:
                # Check if lead already exists
                existing = frappe.db.get_value(
                    "Facebook Lead",
                    {"facebook_lead_id": lead.get("id")}
                )
                
                if not existing:
                    create_facebook_lead(lead)
                    total_leads += 1
        
        return {
            "success": True,
            "message": f"Synced {total_leads} new leads",
            "total_leads": total_leads
        }
        
    except Exception as e:
        frappe.log_error(f"Lead sync error: {str(e)}", "Facebook Leads")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_leads(form_id=None, status=None):
    """
    Get Facebook leads.
    
    Args:
        form_id: Filter by form ID
        status: Filter by status
    
    Returns:
        list: Lead records
    """
    filters = {}
    
    if form_id:
        filters["lead_form_id"] = form_id
    
    if status:
        filters["status"] = status
    
    leads = frappe.get_all(
        "Facebook Lead",
        filters=filters,
        fields=["*"],
        order_by="created_at desc"
    )
    
    return leads


@frappe.whitelist()
def convert_lead(facebook_lead_id, customer=None):
    """
    Convert Facebook Lead to ERPNext Lead.
    
    Args:
        facebook_lead_id: Facebook lead ID
        customer: Optional existing customer
    
    Returns:
        dict: Conversion result
    """
    try:
        # Get Facebook lead
        lead_doc = frappe.get_doc("Facebook Lead", {"facebook_lead_id": facebook_lead_id})
        
        if not lead_doc:
            return {"success": False, "error": "Lead not found"}
        
        # Parse raw data
        raw_data = json.loads(lead_doc.raw_data)
        field_data = raw_data.get("field_data", [])
        parsed_data = parse_field_data(field_data)
        
        # Create or update customer
        if not customer:
            email = parsed_data.get("email", "")
            phone = parsed_data.get("phone", "")
            
            if email:
                customer = frappe.db.get_value("Customer", {"email_id": email}, "name")
            
            if not customer and phone:
                customer = frappe.db.get_value("Customer", {"phone_no": phone}, "name")
        
        if customer:
            customer_doc = frappe.get_doc("Customer", customer)
        else:
            customer_doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": parsed_data.get("full_name", "Unknown"),
                "email_id": parsed_data.get("email", ""),
                "phone_no": parsed_data.get("phone", ""),
                "customer_type": "Individual"
            })
            customer_doc.insert(ignore_permissions=True)
        
        # Create Lead
        lead = frappe.get_doc({
            "doctype": "Lead",
            "lead_name": parsed_data.get("full_name", "Unknown"),
            "email_id": parsed_data.get("email", ""),
            "phone": parsed_data.get("phone", ""),
            "company_name": parsed_data.get("company", ""),
            "source": "Facebook Lead Ad",
            "facebook_lead_id": facebook_lead_id,
            "lead_owner": frappe.session.user
        })
        lead.insert(ignore_permissions=True)
        
        # Update Facebook Lead
        frappe.db.set_value(
            "Facebook Lead",
            lead_doc.name,
            {
                "erpnext_lead": lead.name,
                "status": "Converted"
            }
        )
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Lead converted successfully",
            "lead_name": lead.lead_name,
            "lead_id": lead.name
        }
        
    except Exception as e:
        frappe.log_error(f"Lead conversion error: {str(e)}", "Facebook Leads")
        return {"success": False, "error": str(e)}
