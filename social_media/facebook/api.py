"""
Facebook API Integration
Main webhook handler for Facebook events
"""

import frappe
import requests
import json


@frappe.whitelist(allow_guest=True)
def webhook():
    """
    Main webhook endpoint for Facebook events.
    Routes to appropriate handlers based on event type.
    """
    # Handle GET request for webhook verification
    if frappe.request.method == "GET":
        return handle_verification()

    if frappe.request.method != "POST":
        return

    try:
        data = frappe.request.get_json()
        if not data:
            return

        object_type = data.get("object")

        if object_type == "page":
            handle_page_event(data)
        elif object_type == "standby":
            handle_standby(data)

        return "OK"
    except Exception as e:
        frappe.log_error(
            title="Facebook Webhook Error",
            message=f"Event: {data.get('object') if data else 'N/A'}\n{str(e)}"
        )
        return "Error"


def handle_verification():
    """Handle webhook verification request from Facebook."""
    verify_token = frappe.request.args.get("hub.verify_token")
    mode = frappe.request.args.get("hub.mode")
    challenge = frappe.request.args.get("hub.challenge")

    if mode == "subscribe" and challenge:
        settings = frappe.get_single("Facebook Settings")
        if verify_token == settings.messenger_verify_token:
            frappe.response["type"] = "binary"
            frappe.response["response"] = str(challenge).encode('utf-8')
            frappe.response["headers"] = {"Content-Type": "text/plain"}
            return
        else:
            frappe.log_error("Verification token mismatch", "Facebook Webhook")
            frappe.throw("Token mismatch", frappe.PermissionError)

    frappe.response["type"] = "binary"
    frappe.response["response"] = b"Invalid request"
    frappe.response["headers"] = {"Content-Type": "text/plain"}
    return


def handle_page_event(data):
    """Handle page events from Facebook."""
    entry = data.get("entry", [])

    for entry_data in entry:
        messaging = entry_data.get("messaging", [])
        changes = entry_data.get("changes", [])

        # Handle messaging events (Messenger)
        for event in messaging:
            sender_psid = event.get("sender", {}).get("id")
            recipient_psid = event.get("recipient", {}).get("id")

            if event.get("message"):
                handle_message(event, sender_psid, recipient_psid)
            elif event.get("postback"):
                handle_postback(event, sender_psid, recipient_psid)
            elif event.get("delivery"):
                handle_delivery(event, sender_psid, recipient_psid)
            elif event.get("read"):
                handle_read(event, sender_psid, recipient_psid)

        # Handle changes events (Lead Ads, Comments, etc.)
        for change in changes:
            field = change.get("field")
            value = change.get("value", {})

            if field == "lead_generation":
                handle_lead_generation(value)
            elif field == "feed" and value.get("comment_id"):
                handle_comment(value)
            elif field == "comments" and value.get("comment_id"):
                handle_comment_reply(value)


def handle_message(event, sender_psid, recipient_psid):
    """Handle incoming messages."""
    message = event.get("message", {})
    message_id = message.get("mid")
    text = message.get("text", "")
    attachments = message.get("attachments", [])

    # Get sender name
    sender_name = get_sender_name(sender_psid)

    # Find customer by PSID
    customer = find_customer_by_psid(sender_psid)

    # Create chat record
    frappe.get_doc({
        "doctype": "Facebook Messenger Chat",
        "sender_id": sender_psid,
        "sender_name": sender_name,
        "message": text,
        "direction": "Incoming",
        "customer": customer,
        "is_read": 0
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def handle_postback(event, sender_psid, recipient_psid):
    """Handle postback events (button clicks)."""
    postback = event.get("postback", {})
    payload = postback.get("payload")

    sender_name = get_sender_name(sender_psid)

    frappe.get_doc({
        "doctype": "Facebook Messenger Chat",
        "sender_id": sender_psid,
        "sender_name": sender_name,
        "message": f"POSTBACK: {payload or 'No payload'}",
        "direction": "Incoming"
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def handle_delivery(event, sender_psid, recipient_psid):
    """Handle message delivery confirmations."""
    delivery = event.get("delivery", {})
    mids = delivery.get("mids")
    watermark = delivery.get("watermark")

    frappe.get_doc({
        "doctype": "Facebook Messenger Chat",
        "sender_id": sender_psid,
        "sender_name": "System",
        "message": f"Delivered: {mids}, Watermark: {watermark}",
        "direction": "Outgoing"
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def handle_read(event, sender_psid, recipient_psid):
    """Handle message read confirmations."""
    read = event.get("read", {})
    watermark = read.get("watermark")

    frappe.get_doc({
        "doctype": "Facebook Messenger Chat",
        "sender_id": sender_psid,
        "sender_name": "System",
        "message": f"Read: Watermark {watermark}",
        "direction": "Outgoing"
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def handle_standby(data):
    """Handle standby events (when user is not active)."""
    entry = data.get("entry", [])

    for entry_data in entry:
        messaging = entry_data.get("messaging", [])

        for event in messaging:
            sender_psid = event.get("sender", {}).get("id")
            recipient_psid = event.get("recipient", {}).get("id")

            if event.get("message"):
                handle_message(event, sender_psid, recipient_psid)
            elif event.get("postback"):
                handle_postback(event, sender_psid, recipient_psid)


def handle_lead_generation(value):
    """Handle lead generation events from Facebook Lead Ads."""
    leadgen_id = value.get("leadgen_id")
    form_id = value.get("form_id")

    if leadgen_id:
        # Fetch full lead details
        lead_details = get_lead_details(leadgen_id)

        if lead_details:
            # Create Facebook Lead record
            from social_media.facebook.leads import create_facebook_lead
            create_facebook_lead(lead_details)

            # Auto-create ERPNext Lead if enabled
            settings = frappe.get_single("Facebook Settings")
            if settings.enable_lead_ads:
                from social_media.facebook.leads import create_erpnext_lead
                create_erpnext_lead(lead_details)

            frappe.db.commit()


def handle_comment(value):
    """Handle new comments on posts."""
    comment_id = value.get("comment_id")
    message = value.get("message", "")
    post_id = value.get("post_id")
    created_time = value.get("created_time")

    # Get page info from settings
    settings = frappe.get_single("Facebook Settings")

    frappe.get_doc({
        "doctype": "Facebook Comment",
        "comment_id": comment_id,
        "page": settings.page_id,
        "post_id": post_id,
        "message": message,
        "created_time": created_time
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def handle_comment_reply(value):
    """Handle comment replies."""
    comment_id = value.get("comment_id")
    message = value.get("message", "")
    created_time = value.get("created_time")

    settings = frappe.get_single("Facebook Settings")

    frappe.get_doc({
        "doctype": "Facebook Comment",
        "comment_id": comment_id,
        "page": settings.page_id,
        "message": message,
        "created_time": created_time
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def get_sender_name(sender_psid):
    """Get sender's name from Facebook."""
    settings = frappe.get_single("Facebook Settings")

    if not settings.is_connected:
        return "Unknown"

    import requests
    params = {
        "access_token": settings.page_access_token,
        "fields": "first_name,last_name,name"
    }

    url = f"https://graph.facebook.com/v18.0/{sender_psid}"

    try:
        response = requests.get(url, params=params, timeout=15)
        result = response.json()

        if response.status_code == 200:
            return result.get("name", "Unknown")

    except Exception:
        pass

    return "Unknown"


def find_customer_by_psid(psid):
    """Find customer by PSID."""
    customer = frappe.db.get_value(
        "Customer",
        {"facebook_psid": psid},
        "name"
    )

    return customer


def get_lead_details(lead_id):
    """
    Fetch full lead details from Facebook.
    """
    settings = frappe.get_single("Facebook Settings")

    if not settings.is_connected:
        return None

    import requests
    params = {
        "access_token": settings.page_access_token,
        "fields": "id,form_id,created_time,field_data,ad_id,ad_name,campaign_id,campaign_name"
    }

    url = f"https://graph.facebook.com/v18.0/{lead_id}"

    try:
        response = requests.get(url, params=params, timeout=15)
        result = response.json()

        if response.status_code == 200:
            # Parse field_data
            field_data = result.get("field_data", [])
            parsed_data = parse_field_data(field_data)
            result.update(parsed_data)
            return result

    except Exception:
        pass

    return None


def parse_field_data(field_data):
    """Parse Facebook lead field_data into a flat dictionary."""
    parsed = {}

    for field in field_data:
        name = field.get("name", "")
        values = field.get("values", [])

        if values:
            parsed[name] = values[0] if len(values) == 1 else values

    return parsed
