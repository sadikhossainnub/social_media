"""
Facebook Post Management
Handles posting to Facebook pages
"""

import frappe
from datetime import datetime
from .utils import make_graph_request, create_post_log


@frappe.whitelist()
def post_to_page(message, link=None, image_url=None, page_id=None):
    """
    Post a message to a Facebook page.
    
    Args:
        message: Post message text
        link: Optional link to attach
        image_url: Optional image URL to attach
        page_id: Optional page ID (uses default if not provided)
    
    Returns:
        dict: Post result with post_id or error
    """
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return {"success": False, "error": "Facebook not connected"}
    
    # Use provided page_id or default
    target_page_id = page_id or settings.page_id
    
    if not target_page_id:
        return {"success": False, "error": "No page ID configured"}
    
    # Build post data
    post_data = {
        "message": message
    }
    
    if link:
        post_data["link"] = link
    
    if image_url:
        post_data["picture"] = image_url
    
    # Make API call
    result = make_graph_request(f"/{target_page_id}/feed", method="POST", data=post_data)
    
    if not result:
        return {"success": False, "error": "Failed to post to Facebook"}
    
    # Create post log
    create_post_log(
        reference_doctype="Facebook Settings",
        reference_name=settings.name,
        post_id=result.get("id"),
        message=message,
        status="Posted"
    )
    
    return {
        "success": True,
        "post_id": result.get("id"),
        "message": "Post successful"
    }


@frappe.whitelist()
def post_from_sales_invoice(doc, method=None):
    """
    Auto-post on Sales Invoice submit.
    Triggered by doc_events hook.
    
    Args:
        doc: Sales Invoice document
        method: Event method (not used)
    """
    settings = frappe.get_doc("Facebook Settings")
    
    # Check if auto-post is enabled
    if not settings.enable_auto_post or not settings.is_connected:
        return
    
    try:
        # Build post message
        message = (
            f"New sale! Invoice #{doc.name} — "
            f"Total: {frappe.utils.fmt_money(doc.grand_total, currency=doc.currency)} — "
            f"Customer: {doc.customer_name}"
        )
        
        # Post to Facebook
        result = post_to_page(message)
        
        if result.get("success"):
            frappe.msgprint(f"Posted to Facebook: {result.get('post_id')}")
        else:
            frappe.log_error(
                f"Failed to post invoice {doc.name}: {result.get('error')}",
                "Facebook Auto Post"
            )
            
    except Exception as e:
        frappe.log_error(f"Error posting invoice {doc.name}: {str(e)}", "Facebook Auto Post")


@frappe.whitelist()
def post_from_sales_order(doc, method=None):
    """
    Auto-post on Sales Order submit.
    Triggered by doc_events hook.
    
    Args:
        doc: Sales Order document
        method: Event method (not used)
    """
    settings = frappe.get_doc("Facebook Settings")
    
    # Check if auto-post is enabled
    if not settings.enable_auto_post or not settings.is_connected:
        return
    
    try:
        # Build post message
        message = (
            f"New order! Order #{doc.name} — "
            f"Total: {frappe.utils.fmt_money(doc.grand_total, currency=doc.currency)} — "
            f"Customer: {doc.customer_name}"
        )
        
        # Post to Facebook
        result = post_to_page(message)
        
        if result.get("success"):
            frappe.msgprint(f"Posted to Facebook: {result.get('post_id')}")
        else:
            frappe.log_error(
                f"Failed to post order {doc.name}: {result.get('error')}",
                "Facebook Auto Post"
            )
            
    except Exception as e:
        frappe.log_error(f"Error posting order {doc.name}: {str(e)}", "Facebook Auto Post")


@frappe.whitelist()
def test_post():
    """
    Test post to Facebook.
    Used for testing the connection.
    """
    result = post_to_page("Test post from ERPNext!")
    
    if result.get("success"):
        return {
            "success": True,
            "message": f"Test post successful! ID: {result.get('post_id')}"
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error")
        }


@frappe.whitelist()
def get_post_logs(reference_doctype=None, reference_name=None):
    """
    Get Facebook post logs.
    
    Args:
        reference_doctype: Filter by doctype
        reference_name: Filter by document name
    
    Returns:
        list: Post log entries
    """
    filters = {}
    
    if reference_doctype:
        filters["reference_doctype"] = reference_doctype
    
    if reference_name:
        filters["reference_name"] = reference_name
    
    posts = frappe.get_all(
        "Facebook Post Log",
        filters=filters,
        fields=["*"],
        order_by="posted_at desc"
    )
    
    return posts


@frappe.whitelist()
def delete_post(post_id):
    """
    Delete a post from Facebook.
    
    Args:
        post_id: Facebook post ID
    
    Returns:
        dict: Delete result
    """
    settings = frappe.get_doc("Facebook Settings")
    
    if not settings.is_connected:
        return {"success": False, "error": "Facebook not connected"}
    
    # Make API call to delete
    result = make_graph_request(f"/{post_id}", method="DELETE")
    
    if not result:
        return {"success": False, "error": "Failed to delete post"}
    
    # Update post log
    frappe.db.set_value(
        "Facebook Post Log",
        {"post_id": post_id},
        "status",
        "Deleted"
    )
    
    return {
        "success": True,
        "message": "Post deleted successfully"
    }
