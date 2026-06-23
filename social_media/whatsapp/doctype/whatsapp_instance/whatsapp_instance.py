# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.whatsapp.utils import (
	create_instance,
	connect_instance,
	restart_instance,
	send_text,
	set_webhook,
	logout_instance,
	delete_instance,
	connection_state
)


class WhatsappInstance(Document):
	def before_insert(self):
		# API key will be generated from the create response hash
		# Pre-generate a UUID only as fallback for manual/sync-created instances
		if not self.apikey:
			import uuid
			self.apikey = str(uuid.uuid4()).upper()

	def after_insert(self):
		# Skip provisioning if this was created by sync
		if getattr(self, '_skip_provision', False):
			return
		if not self.status or self.status == "Disconnected":
			self.provision_instance()

	def provision_instance(self):
		try:
			response = create_instance(
				self.instance_name,
				token=self.apikey,
				number=self.number,
				integration=self.integration or "WHATSAPP-BAILEYS"
			)
			if response:
				instance_info = response.get("instance", {})
				qrcode_info = response.get("qrcode", {})

				# Save the hash as apikey — this is the real instance API key
				if response.get("hash"):
					self.apikey = response["hash"]

				if instance_info:
					self.external_instance_id = instance_info.get("instanceId")
					raw_status = instance_info.get("status") or instance_info.get("connectionStatus")
					if raw_status == "open":
						self.status = "Connected"
					elif raw_status == "connecting":
						self.status = "Connecting"
					else:
						self.status = "Disconnected"

				if qrcode_info and qrcode_info.get("base64"):
					self.qr_code_base64 = qrcode_info["base64"]
					self.status = "Connecting"

				self.save()

		except Exception as e:
			frappe.msgprint(f"Failed to provision instance: {str(e)}")

	@frappe.whitelist()
	def connect(self):
		"""Connect instance and get QR code for pairing."""
		data = connect_instance(self.instance_name)
		if data:
			if "base64" in data:
				self.qr_code_base64 = data["base64"]
				self.status = "Connecting"
				self.save()
			elif "qrcode" in data and data["qrcode"].get("base64"):
				self.qr_code_base64 = data["qrcode"]["base64"]
				self.status = "Connecting"
				self.save()
			elif data.get("instance", {}).get("state") == "open":
				self.status = "Connected"
				self.qr_code_base64 = ""
				self.save()
				frappe.msgprint("Already connected! No QR needed.")
			else:
				frappe.msgprint(f"API response: {str(data)[:300]}")

	@frappe.whitelist()
	def refresh_status(self):
		"""Get current connection state from API."""
		data = connection_state(self.instance_name)
		if data:
			state = data.get("instance", {}).get("state") or data.get("state")
			if state == "open":
				self.status = "Connected"
				self.qr_code_base64 = ""
			elif state == "connecting":
				self.status = "Connecting"
			else:
				self.status = "Disconnected"
			self.save()
			frappe.msgprint(f"Status: {self.status}")

	@frappe.whitelist()
	def restart(self):
		"""Restart the instance."""
		try:
			restart_instance(self.instance_name)
			frappe.msgprint("Instance restarted successfully.")
		except Exception as e:
			frappe.throw(f"Failed to restart: {str(e)}")

	@frappe.whitelist()
	def send_test_message(self, number, message):
		try:
			response = send_text(self.instance_name, number, message)
			return response
		except Exception as e:
			frappe.throw(f"Failed to send test message: {str(e)}")

	@frappe.whitelist()
	def configure_webhook(self):
		site_url = frappe.utils.get_url()
		webhook_url = f"{site_url}/api/method/social_media.whatsapp.api.webhook"

		try:
			response = set_webhook(self.instance_name, webhook_url)
			frappe.msgprint(f"Webhook configured: {webhook_url}")
			return response
		except Exception as e:
			frappe.throw(f"Failed to configure webhook: {str(e)}")

	@frappe.whitelist()
	def logout(self):
		try:
			logout_instance(self.instance_name)
			self.status = "Disconnected"
			self.qr_code_base64 = ""
			self.save()
			return True
		except Exception as e:
			frappe.throw(f"Failed to logout: {str(e)}")

	@frappe.whitelist()
	def delete_remote(self):
		try:
			delete_instance(self.instance_name)
			return True
		except Exception as e:
			frappe.throw(f"Failed to delete remote instance: {str(e)}")

	@property
	def qr_code_html(self):
		if self.qr_code_base64:
			return f'<img src="{self.qr_code_base64}" style="width: 300px; height: 300px;" />'
		return "<div>No QR Code available</div>"
