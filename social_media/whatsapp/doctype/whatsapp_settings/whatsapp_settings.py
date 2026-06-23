import frappe
from frappe.model.document import Document
from social_media.whatsapp.utils import fetch_instances


class WhatsappSettings(Document):
	def on_load(self):
		"""Generate webhook URL on page load"""
		self.generate_webhook_url()
	
	def generate_webhook_url(self):
		"""Generate webhook URL from current domain"""
		try:
			# Get the base URL from request
			site_url = frappe.utils.get_url()
			webhook_url = f"{site_url}/api/whatsapp/webhook"
			self.webhook_url = webhook_url
		except Exception as e:
			frappe.log_error(f"Error generating webhook URL: {str(e)}")
			self.webhook_url = "[Unable to generate URL - check domain settings]"
	
	def on_update(self):
		if self.evolution_api_endpoint and self.api_key:
			frappe.enqueue(
				"social_media.whatsapp.doctype.whatsapp_settings.whatsapp_settings.sync_instances",
				now=frappe.flags.in_test
			)


@frappe.whitelist()
def sync_instances():
	try:
		instances = fetch_instances()
	except Exception as e:
		frappe.msgprint(f"Evolution API Error: {str(e)}", indicator="red", alert=True)
		return 0

	if not instances:
		frappe.msgprint("No instances found. Check your API URL and Global API Key.", indicator="orange")
		return 0

	# Handle both list and dict responses
	if isinstance(instances, dict):
		instances = instances.get("instances", [])

	if not instances:
		frappe.msgprint("Got a response but it contains no instances.")
		return 0

	new_count = 0
	total_count = 0
	for inst in instances:
		total_count += 1

		# v2.3: instance data can be nested under "instance" key
		instance_data = inst.get("instance", inst)
		instance_name = instance_data.get("instanceName") or instance_data.get("name")
		if not instance_name:
			continue

		# Status mapping
		raw_status = instance_data.get("status") or instance_data.get("connectionStatus")
		status = "Disconnected"
		if raw_status == "open":
			status = "Connected"
		elif raw_status == "connecting":
			status = "Connecting"

		# Phone number and external ID
		phone = instance_data.get("owner") or instance_data.get("number") or instance_data.get("ownerJid")
		external_id = instance_data.get("instanceId") or instance_data.get("id")
		integration = instance_data.get("integration", "WHATSAPP-BAILEYS")

		if not frappe.db.exists("Whatsapp Instance", instance_name):
			doc = frappe.get_doc({
				"doctype": "Whatsapp Instance",
				"instance_name": instance_name,
				"external_instance_id": external_id,
				"status": status,
				"phone_number": phone,
				"integration": integration
			})
			# Skip auto-provisioning — this instance already exists on API
			doc._skip_provision = True
			doc.insert(ignore_permissions=True)
			new_count += 1
		else:
			frappe.db.set_value("Whatsapp Instance", instance_name, {
				"status": status,
				"phone_number": phone,
				"external_instance_id": external_id
			})

	msg = f"Total {total_count} instance(s) found."
	if new_count > 0:
		msg += f" {new_count} new instance(s) added."
	else:
		msg += " Existing instances updated."

	frappe.msgprint(msg, indicator="green")
	return total_count
