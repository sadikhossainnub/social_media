import frappe
from frappe import _
from social_media.connectors.meta.facebook import FacebookConnector


@frappe.whitelist()
def publish_social_post(post_id):
	"""Publish social media post across platforms"""
	
	try:
		post_doc = frappe.get_doc("Social Post", post_id)
		
		if post_doc.status != "Draft":
			return {"success": False, "error": "Post is not in draft status"}
		
		post_doc.status = "Publishing"
		post_doc.save()
		
		results = []
		
		for platform in post_doc.platforms:
			channel_doc = frappe.get_doc("Social Media Channel", platform.channel)
			account_doc = frappe.get_doc("Social Account", {"channel": channel_doc.name})
			
			# Get appropriate connector
			connector = get_connector(channel_doc.platform, account_doc)
			
			if connector:
				result = connector.publish_post(post_doc)
				
				if result["success"]:
					platform.status = "Published"
					platform.platform_post_id = result.get("post_id")
					platform.post_url = result.get("post_url")
					platform.published_at = frappe.utils.now()
				else:
					platform.status = "Failed"
					platform.error_message = result.get("error")
				
				results.append({
					"platform": channel_doc.platform,
					"success": result["success"],
					"result": result
				})
		
		# Update overall post status
		if all(r["success"] for r in results):
			post_doc.status = "Published"
			post_doc.published_on = frappe.utils.now()
		elif any(r["success"] for r in results):
			post_doc.status = "Partially Published"
		else:
			post_doc.status = "Failed"
		
		post_doc.save()
		
		return {
			"success": True,
			"message": f"Post published to {len([r for r in results if r['success']])} platforms",
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Social post publish error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def schedule_social_post(post_id, scheduled_time):
	"""Schedule social media post"""
	
	try:
		post_doc = frappe.get_doc("Social Post", post_id)
		post_doc.scheduled_time = scheduled_time
		post_doc.status = "Scheduled"
		post_doc.save()
		
		# Enqueue publishing job
		frappe.enqueue(
			"social_media.api_social.publish_social_post",
			post_id=post_id,
			queue="long",
			at_time=scheduled_time
		)
		
		return {
			"success": True,
			"message": f"Post scheduled for {scheduled_time}"
		}
		
	except Exception as e:
		frappe.log_error(f"Social post schedule error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_social_analytics(channel=None, date_range=None):
	"""Get social media analytics"""
	
	try:
		if channel:
			channel_doc = frappe.get_doc("Social Media Channel", channel)
			account_doc = frappe.get_doc("Social Account", {"channel": channel})
			
			connector = get_connector(channel_doc.platform, account_doc)
			
			if connector:
				return connector.get_analytics(date_range=date_range)
		
		# Get analytics for all channels
		channels = frappe.get_all("Social Media Channel", {"status": "Active"})
		analytics = {}
		
		for ch in channels:
			channel_doc = frappe.get_doc("Social Media Channel", ch.name)
			account_doc = frappe.get_doc("Social Account", {"channel": ch.name})
			
			connector = get_connector(channel_doc.platform, account_doc)
			
			if connector:
				analytics[ch.name] = connector.get_analytics(date_range=date_range)
		
		return {"success": True, "analytics": analytics}
		
	except Exception as e:
		frappe.log_error(f"Social analytics error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_social_messages(channel=None):
	"""Sync messages from social platforms"""
	
	try:
		if channel:
			channels = [channel]
		else:
			channels = frappe.get_all("Social Media Channel", {"status": "Active"}, pluck="name")
		
		total_messages = 0
		
		for ch in channels:
			channel_doc = frappe.get_doc("Social Media Channel", ch)
			account_doc = frappe.get_doc("Social Account", {"channel": ch})
			
			connector = get_connector(channel_doc.platform, account_doc)
			
			if connector:
				messages = connector.fetch_messages(since=channel_doc.last_sync)
				
				for msg in messages:
					# Create conversation and message records
					create_conversation_from_message(msg, channel_doc)
				
				total_messages += len(messages)
				
				# Update last sync time
				channel_doc.last_sync = frappe.utils.now()
				channel_doc.save()
		
		return {
			"success": True,
			"message": f"Synced {total_messages} messages from {len(channels)} channels"
		}
		
	except Exception as e:
		frappe.log_error(f"Social sync error: {str(e)}")
		return {"success": False, "error": str(e)}


def get_connector(platform, account_doc):
	"""Get appropriate connector for platform"""
	
	connectors = {
		"Facebook": FacebookConnector,
		"Instagram": FacebookConnector,  # Instagram uses Facebook Graph API
		# Add more connectors here
	}
	
	connector_class = connectors.get(platform)
	
	if connector_class:
		return connector_class(account_doc)
	
	return None


def create_conversation_from_message(message_data, channel_doc):
	"""Create conversation and message records from platform message"""
	
	try:
		# Check if conversation exists
		conversation = frappe.db.exists("Conversation", {
			"channel": channel_doc.name,
			"external_id": message_data.get("conversation_id")
		})
		
		if not conversation:
			# Create new conversation
			conv_doc = frappe.new_doc("Conversation")
			conv_doc.update({
				"channel": channel_doc.name,
				"external_id": message_data.get("conversation_id"),
				"participants": message_data.get("participants", ""),
				"status": "Open",
				"last_message_time": message_data.get("created_time")
			})
			conv_doc.insert()
			conversation = conv_doc.name
		
		# Create message record (reuse existing message DocTypes)
		if channel_doc.platform == "Facebook":
			msg_doc = frappe.new_doc("Facebook Message")
		elif channel_doc.platform == "Instagram":
			msg_doc = frappe.new_doc("Instagram Message")
		elif channel_doc.platform == "WhatsApp":
			msg_doc = frappe.new_doc("WhatsApp Message")
		
		if msg_doc:
			msg_doc.update({
				"message_id": message_data.get("id"),
				"sender_id": message_data.get("from", {}).get("id"),
				"message_content": message_data.get("message"),
				"timestamp": message_data.get("created_time"),
				"conversation_id": conversation,
				"status": "received"
			})
			msg_doc.insert()
		
	except Exception as e:
		frappe.log_error(f"Create conversation error: {str(e)}")


@frappe.whitelist(allow_guest=True)
def webhook_receiver(platform):
	"""Receive webhooks from social platforms"""
	
	try:
		data = frappe.local.form_dict
		
		# Verify webhook signature (platform-specific)
		if not verify_webhook_signature(platform, data):
			frappe.throw("Invalid webhook signature")
		
		# Get connector and process webhook
		channels = frappe.get_all("Social Media Channel", {"platform": platform, "status": "Active"})
		
		for ch in channels:
			channel_doc = frappe.get_doc("Social Media Channel", ch.name)
			account_doc = frappe.get_doc("Social Account", {"channel": ch.name})
			
			connector = get_connector(platform, account_doc)
			
			if connector:
				result = connector.process_webhook(data)
				
				if not result.get("success"):
					frappe.log_error(f"Webhook processing failed: {result.get('error')}")
		
		return {"success": True}
		
	except Exception as e:
		frappe.log_error(f"Webhook receiver error: {str(e)}")
		return {"success": False, "error": str(e)}


def verify_webhook_signature(platform, data):
	"""Verify webhook signature for security"""
	# Platform-specific signature verification
	# This is a simplified version - implement proper verification
	return True