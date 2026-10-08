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
    """Handle webhook verification request from Facebook Meta."""
    verify_token = frappe.request.args.get("hub.verify_token") or frappe.request.args.get("verify_token")
    mode = frappe.request.args.get("hub.mode") or frappe.request.args.get("mode")
    challenge = frappe.request.args.get("hub.challenge") or frappe.request.args.get("challenge")
    
    if mode == "subscribe" and challenge:
        settings = frappe.get_single("Facebook Settings")
        expected_token = getattr(settings, "messenger_verify_token", None) or getattr(settings, "webhook_verify_token", None)
        
        if not expected_token or verify_token == expected_token:
            frappe.local.response["type"] = "raw"
            frappe.local.response["response"] = str(challenge)
            frappe.local.response["http_status_code"] = 200
            return
        else:
            frappe.log_error(f"Verification token mismatch: received {verify_token}", "Facebook Messenger Webhook")

    frappe.local.response["type"] = "raw"
    frappe.local.response["response"] = str(challenge or "Invalid Request")
    frappe.local.response["http_status_code"] = 200
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
    
    if not getattr(settings, "is_connected", False):
        return "Unknown"
    
    page_access_token = getattr(settings, "page_access_token", None) or settings.get_password("page_access_token", raise_exception=False)
    params = {
        "access_token": page_access_token,
        "fields": "first_name,last_name,name"
    }
    
    from social_media.facebook.utils import get_graph_api_version
    url = f"https://graph.facebook.com/{get_graph_api_version()}/{sender_psid}"
    
    try:
        response = requests.get(url, params=params, timeout=15)
        result = response.json()
        
        if response.status_code == 200:
            return result.get("name", "Unknown")
        
    except Exception:
        pass
    
    return "Unknown"


def find_customer_by_psid(psid):
    """Find customer by PSID safely."""
    if not psid:
        return None
    try:
        if frappe.db.has_column("Customer", "facebook_psid"):
            return frappe.db.get_value("Customer", {"facebook_psid": psid}, "name")
    except Exception:
        pass
    return None



def auto_reply(sender_psid, message_text):
    """Auto-reply to incoming message."""
    settings = frappe.get_doc("Facebook Settings")
    
    if not getattr(settings, "is_connected", False):
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
    
    if not getattr(settings, "is_connected", False):
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
    
    if not getattr(settings, "is_connected", False):
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


# ── Sync Old Messages ─────────────────────────────────────────────

@frappe.whitelist()
def sync_old_messages(page_id=None, max_conversations=0, max_messages_per_conversation=0):
    """
    Fetch all old conversations and messages from Facebook Page inbox
    and save them to Facebook Messenger Chat doctype.

    Args:
        page_id: Facebook Page doctype name (optional, uses default from settings)
        max_conversations: Max conversations to fetch (0 = all)
        max_messages_per_conversation: Max messages per conversation (0 = all)

    Returns:
        dict: Summary with counts of synced conversations and messages
    """
    from social_media.facebook.graph_client import FacebookGraphClient

    if page_id and str(page_id).strip().lower() in ("all", "undefined", "null", "none", ""):
        page_id = None

    if not page_id:
        try:
            pages = frappe.get_all("Facebook Page", filters={"status": "Active"}, fields=["name", "page_id"], ignore_permissions=True)
            if not pages:
                pages = frappe.get_all("Facebook Page", fields=["name", "page_id"], ignore_permissions=True)
            if pages:
                page_id = pages[0].name
        except Exception:
            pass

    max_conversations = int(max_conversations or 0)
    max_messages_per_conversation = int(max_messages_per_conversation or 0)

    client = FacebookGraphClient(page_id=page_id)

    if not client.access_token:
        error_msg = f"Facebook Page '{page_id}' is not connected or has no access token configured."
        frappe.log_error(error_msg, "Facebook Old Message Sync Error")
        return {"success": False, "error": error_msg}

    total_conversations = 0
    total_messages = 0
    skipped_messages = 0
    errors = []

    try:
        # Step 1: Fetch conversations with pagination
        conversations_data = client.get_conversations(page_id=None, limit=25)

        if conversations_data is None:
            err_msg = f"Failed to connect to Meta Graph API for page '{page_id}'. Check access token validity or Error Log."
            frappe.log_error(err_msg, "Facebook Old Message Sync Error")
            return {"success": False, "error": err_msg}

        if isinstance(conversations_data, dict) and "error" in conversations_data:
            err_obj = conversations_data.get("error", {})
            err_msg = err_obj.get("message", "Unknown Meta API error") if isinstance(err_obj, dict) else str(err_obj)
            frappe.log_error(f"Meta API Error during sync: {err_msg}", "Facebook Old Message Sync Error")
            return {"success": False, "error": err_msg}

        while isinstance(conversations_data, dict):
            items = conversations_data.get("data", [])
            if not isinstance(items, list) or not items:
                frappe.log_error(f"Meta Graph API returned 0 conversations for page '{page_id}'. Raw response: {json.dumps(conversations_data)[:1000]}", "Facebook Old Message Sync Info")
                break

            for conv in items:
                if not isinstance(conv, dict):
                    continue

                if max_conversations and total_conversations >= max_conversations:
                    break

                conv_id = conv.get("id")
                if not conv_id:
                    continue

                # Get participant info
                participants_obj = conv.get("participants", {})
                participants = participants_obj.get("data", []) if isinstance(participants_obj, dict) else []
                participant_names = {}
                if isinstance(participants, list):
                    participant_names = {p.get("id"): p.get("name", "Unknown") for p in participants if isinstance(p, dict)}

                # Step 2: Fetch all messages in this conversation with pagination
                msg_count_in_conv = 0
                messages_data = client.get_conversation_messages(conv_id, limit=50)

                while isinstance(messages_data, dict):
                    msg_items = messages_data.get("data", [])
                    if not isinstance(msg_items, list) or not msg_items:
                        break

                    for msg in msg_items:
                        if not isinstance(msg, dict):
                            continue

                        if max_messages_per_conversation and msg_count_in_conv >= max_messages_per_conversation:
                            break

                        fb_msg_id = msg.get("id")
                        if not fb_msg_id:
                            continue

                        # Skip if already synced (check by conversation_id + message + timestamp)
                        msg_text = msg.get("message", "") or ""
                        created_time_raw = msg.get("created_time", "")

                        existing = frappe.db.exists("Facebook Messenger Chat", {
                            "conversation_id": conv_id,
                            "message": msg_text,
                            "timestamp": created_time_raw
                        })
                        if existing:
                            skipped_messages += 1
                            msg_count_in_conv += 1
                            continue

                        # Determine direction and sender info
                        from_data = msg.get("from", {})
                        if isinstance(from_data, dict):
                            sender_id = from_data.get("id", "")
                            sender_name = from_data.get("name", "")
                        else:
                            sender_id = ""
                            sender_name = ""

                        # If sender is the page itself, direction is Outgoing
                        page_fb_id = client.page_id
                        direction = "Outgoing" if sender_id == page_fb_id else "Incoming"

                        # If sender name not in from_data, try participants
                        if not sender_name and sender_id in participant_names:
                            sender_name = participant_names[sender_id]

                        # Parse attachments
                        attachments_obj = msg.get("attachments", {})
                        attachments = attachments_obj.get("data", []) if isinstance(attachments_obj, dict) else []
                        attachment_json = json.dumps(attachments) if attachments else "[]"

                        # Parse created_time
                        created_time = created_time_raw
                        if created_time:
                            try:
                                from dateutil import parser as dt_parser
                                parsed_dt = dt_parser.parse(created_time)
                                # Convert to naive datetime (strip timezone) for MariaDB
                                created_time = parsed_dt.replace(tzinfo=None)
                            except Exception:
                                created_time = datetime.now()

                        try:
                            doc = frappe.get_doc({
                                "doctype": "Facebook Messenger Chat",
                                "sender_id": sender_id,
                                "sender_name": sender_name or "Unknown",
                                "message": msg_text,
                                "direction": direction,
                                "conversation_id": conv_id,
                                "timestamp": created_time,
                                "attachments": attachment_json,
                                "is_read": 1
                            })
                            doc.insert(ignore_permissions=True)
                            total_messages += 1
                            msg_count_in_conv += 1
                        except Exception as e:
                            errors.append(f"Message {fb_msg_id}: {str(e)}")
                            msg_count_in_conv += 1

                    # Check message limit
                    if max_messages_per_conversation and msg_count_in_conv >= max_messages_per_conversation:
                        break

                    # Next page of messages (pagination)
                    paging = messages_data.get("paging", {}) if isinstance(messages_data, dict) else {}
                    next_url = paging.get("next") if isinstance(paging, dict) else None
                    if next_url:
                        messages_data = _fetch_next_page(next_url)
                    else:
                        break

                total_conversations += 1
                # Commit after each conversation to avoid losing progress
                frappe.db.commit()

                # Publish progress for realtime updates
                frappe.publish_realtime(
                    "sync_old_messages_progress",
                    {
                        "conversations": total_conversations,
                        "messages": total_messages,
                        "skipped": skipped_messages
                    },
                    user=frappe.session.user
                )

            # Check conversation limit
            if max_conversations and total_conversations >= max_conversations:
                break

            # Next page of conversations (pagination)
            paging = conversations_data.get("paging", {}) if isinstance(conversations_data, dict) else {}
            next_url = paging.get("next") if isinstance(paging, dict) else None
            if next_url:
                conversations_data = _fetch_next_page(next_url)
            else:
                break

    except Exception as e:
        frappe.log_error(
            title="Facebook Sync Old Messages Error",
            message=f"{str(e)}\n{frappe.get_traceback()}"
        )
        errors.append(str(e))

    result = {
        "success": True,
        "conversations_synced": total_conversations,
        "messages_synced": total_messages,
        "messages_skipped": skipped_messages,
        "errors": errors[:20] if errors else []
    }

    frappe.msgprint(
        f"Sync Complete: {total_conversations} conversations, "
        f"{total_messages} new messages synced, {skipped_messages} already existed.",
        title="Facebook Message Sync",
        indicator="green"
    )

    return result


def _fetch_next_page(next_url):
    """
    Fetch next page of paginated results using the full URL from Facebook.
    """
    try:
        response = requests.get(next_url, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        frappe.log_error(f"Pagination fetch error: {str(e)}", "Facebook Sync")
    return None


@frappe.whitelist()
def enqueue_sync_old_messages(page_id=None, max_conversations=0, max_messages_per_conversation=0):
    """
    Enqueue sync_old_messages as a background job for large syncs.
    This prevents timeout for pages with many conversations.
    """
    frappe.enqueue(
        "social_media.facebook.messenger.sync_old_messages",
        queue="long",
        timeout=3600,
        page_id=page_id,
        max_conversations=int(max_conversations or 0),
        max_messages_per_conversation=int(max_messages_per_conversation or 0)
    )

    return {
        "success": True,
        "message": "Old message sync has been queued in the background. You will be notified when it completes."
    }


# ── Conversation View APIs ────────────────────────────────────────

@frappe.whitelist()
def get_conversation_thread(conversation_id):
    """
    Get all messages in a conversation, ordered by timestamp (oldest first).

    Args:
        conversation_id: The Facebook conversation ID

    Returns:
        list: Messages in chronological order
    """
    if not conversation_id:
        return []

    messages = frappe.db.sql("""
        SELECT sender_id, sender_name, message, direction, timestamp, 
               attachments, is_read, name
        FROM `tabFacebook Messenger Chat`
        WHERE conversation_id = %s
        ORDER BY timestamp ASC
    """, (conversation_id,), as_dict=True)

    return messages


@frappe.whitelist()
def get_all_conversations(limit=50):
    """
    Get all conversations grouped by conversation_id, with participant info
    and last message preview. Shows like a WhatsApp conversation list.

    Args:
        limit: Max conversations to return (default 50)

    Returns:
        list: Conversations with participant name, last message, count, timestamp
    """
    limit = int(limit or 50)

    conversations = frappe.db.sql("""
        SELECT 
            conversation_id,
            COUNT(*) as message_count,
            MAX(timestamp) as last_timestamp,
            MIN(timestamp) as first_timestamp
        FROM `tabFacebook Messenger Chat`
        WHERE conversation_id IS NOT NULL AND conversation_id != ''
        GROUP BY conversation_id
        ORDER BY last_timestamp DESC
        LIMIT %s
    """, (limit,), as_dict=True)

    result = []
    for conv in conversations:
        # Get the participant name (the non-page sender)
        participant = frappe.db.sql("""
            SELECT sender_name 
            FROM `tabFacebook Messenger Chat`
            WHERE conversation_id = %s AND direction = 'Incoming'
            LIMIT 1
        """, (conv.conversation_id,), as_dict=True)

        participant_name = participant[0].sender_name if participant else "Unknown"

        # Get the last message
        last_msg = frappe.db.sql("""
            SELECT message, direction, sender_name
            FROM `tabFacebook Messenger Chat`
            WHERE conversation_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """, (conv.conversation_id,), as_dict=True)

        last_message = last_msg[0].message if last_msg else ""
        last_direction = last_msg[0].direction if last_msg else ""

        # Prefix with "You: " if outgoing
        if last_direction == "Outgoing" and last_message:
            last_message = f"You: {last_message}"

        result.append({
            "conversation_id": conv.conversation_id,
            "participant_name": participant_name,
            "message_count": conv.message_count,
            "last_message": last_message,
            "last_timestamp": str(conv.last_timestamp) if conv.last_timestamp else "",
            "first_timestamp": str(conv.first_timestamp) if conv.first_timestamp else ""
        })

    return result
