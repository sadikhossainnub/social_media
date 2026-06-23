"""
Facebook Messenger Integration
Handles Messenger webhook and messaging
"""

import frappe
import requests
import json
from datetime import datetime
from .utils import make_graph_request, create_messenger_chat


@frappe.whitelist(allow_guest=True)
def webhook():
    """
    Webhook endpoint for Facebook Messenger.
    Handles both verification (GET) and messages (POST).
    """
    # Handle GET request for webhook verification
    if frappe.request.method == "GET":
        return handle_verification()
    
    # Handle POST request for messages
    if frappe.request.method != "POST":
        return
    
    try:
        data = frappe.request.get_json()
        if not data:
            return
        
        object_type = data.get("object")
        
        if object_type == "page":
            handle_messaging_event(data)
        
        return "OK"
        
    except Exception as e:
        frappe.log_error(
            title="Facebook Messenger Webhook Error",
            message=str(e)
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
            frappe.response["filecontent"] = str(challenge).encode('utf-8')
            frappe.response["filename"] = "challenge.txt"
            return
        else:
            frappe.log_error("Verification token mismatch", "Facebook Messenger Webhook")
            frappe.throw("Token mismatch", frappe.PermissionError)
    
    frappe.response["type"] = "binary"
    frappe.response["filecontent"] = b"Invalid request"
    frappe.response["filename"] = "error.txt"
    return


def handle_messaging_event(data):
    """Handle messaging events from Facebook."""
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
            elif event.get("delivery"):
                handle_delivery(event, sender_psid, recipient_psid)
            elif event.get("read"):
                handle_read(event, sender_psid, recipient_psid)


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
    create_messenger_chat(
        sender_id=sender_psid,
        sender_name=sender_name,
        message=text,
        direction="Incoming",
        customer=customer
    )
    
    # Auto-reply if configured
    if text:
        auto_reply(sender_psid, text)


def handle_postback(event, sender_psid, recipient_psid):
    """Handle postback events (button clicks)."""
    postback = event.get("postback", {})
    payload = postback.get("payload")
    
    sender_name = get_sender_name(sender_psid)
    
    create_messenger_chat(
        sender_id=sender_psid,
        sender_name=sender_name,
        message=f"POSTBACK: {payload or 'No payload'}",
        direction="Incoming"
    )


def handle_delivery(event, sender_psid, recipient_psid):
    """Handle message delivery confirmations."""
    delivery = event.get("delivery", {})
    mids = delivery.get("mids")
    
    create_messenger_chat(
        sender_id=sender_psid,
        sender_name="System",
        message=f"Delivered: {mids}",
        direction="Outbound"
    )


def handle_read(event, sender_psid, recipient_psid):
    """Handle message read confirmations."""
    read = event.get("read", {})
    watermark = read.get("watermark")
    
    create_messenger_chat(
        sender_id=sender_psid,
        sender_name="System",
        message=f"Read: Watermark {watermark}",
        direction="Outbound"
    )


def get_sender_name(sender_psid):
    """Get sender's name from Facebook."""
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return "Unknown"
    
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
    # Check if customer exists with PSID
    customer = frappe.db.get_value(
        "Customer",
        {"facebook_psid": psid},
        "name"
    )
    
    return customer


def auto_reply(sender_psid, message_text):
    """Auto-reply to incoming message."""
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return
    
    # Simple keyword-based auto-reply
    message_lower = message_text.lower()
    
    if "price" in message_lower or "cost" in message_lower or "rate" in message_lower:
        reply = "Our pricing information is available at our website. Would you like me to send you a catalog?"
    elif "hello" in message_lower or "hi" in message_lower or "hey" in message_lower:
        reply = "Hello! How can I help you today?"
    elif "thank" in message_lower:
        reply = "You're welcome! Is there anything else I can help you with?"
    else:
        reply = "Thank you for your message. We'll get back to you shortly."
    
    send_message(sender_psid, reply)


@frappe.whitelist()
def send_message(recipient_id, message_text, quick_replies=None):
    """
    Send a message to a Facebook user.
    
    Args:
        recipient_id: Facebook user ID (PSID)
        message_text: Message content
        quick_replies: Optional list of quick reply objects
    
    Returns:
        dict: Send result with message_id or error
    """
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return {"success": False, "error": "Facebook not connected"}
    
    # Build message payload
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    }
    
    # Add quick replies if provided
    if quick_replies:
        payload["message"]["quick_replies"] = quick_replies
    
    # Make API call
    result = make_graph_request("/me/messages", method="POST", data=payload)
    
    if not result:
        return {"success": False, "error": "Failed to send message"}
    
    # Create chat record
    create_messenger_chat(
        sender_id=recipient_id,
        sender_name="System",
        message=message_text,
        direction="Outgoing"
    )
    
    return {
        "success": True,
        "message_id": result.get("message_id"),
        "fb_message_id": result.get("message_id")
    }


@frappe.whitelist()
def send_quick_reply(recipient_id, message_text, options):
    """
    Send a message with quick replies.
    
    Args:
        recipient_id: Facebook user ID
        message_text: Message content
        options: List of quick reply options
    
    Returns:
        dict: Send result
    """
    # Build quick replies
    quick_replies = []
    
    for option in options:
        quick_replies.append({
            "content_type": "text",
            "title": option,
            "payload": f"QUICK_REPLY_{option.upper().replace(' ', '_')}"
        })
    
    return send_message(recipient_id, message_text, quick_replies)


@frappe.whitelist()
def send_typing_indicator(recipient_id):
    """
    Show typing indicator to user.
    
    Args:
        recipient_id: Facebook user ID
    
    Returns:
        dict: Result
    """
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return {"success": False, "error": "Facebook not connected"}
    
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "sender_action": "typing_on"
    }
    
    result = make_graph_request("/me/messages", method="POST", data=payload)
    
    if result:
        return {"success": True}
    else:
        return {"success": False, "error": "Failed to show typing indicator"}


@frappe.whitelist()
def get_chat_history(sender_id=None, limit=50):
    """
    Get chat history.
    
    Args:
        sender_id: Filter by sender ID
        limit: Number of records to return
    
    Returns:
        list: Chat records
    """
    filters = {}
    
    if sender_id:
        filters["sender_id"] = sender_id
    
    chats = frappe.get_all(
        "Facebook Messenger Chat",
        filters=filters,
        fields=["*"],
        order_by="timestamp desc",
        limit=limit
    )
    
    return chats


@frappe.whitelist()
def send_template_message(recipient_id, template_name, language="en", components=None):
    """
    Send a template message.
    
    Args:
        recipient_id: Facebook user ID
        template_name: Template name
        language: Language code
        components: Template components
    
    Returns:
        dict: Send result
    """
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "template": {
                "name": template_name,
                "language": {
                    "code": language
                }
            }
        }
    }
    
    if components:
        payload["message"]["template"]["components"] = components
    
    result = make_graph_request("/me/messages", method="POST", data=payload)
    
    if result:
        return {
            "success": True,
            "message_id": result.get("message_id")
        }
    else:
        return {"success": False, "error": "Failed to send template message"}
