# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from social_media.whatsapp.utils import (
	send_text,
	send_media,
	send_audio,
	send_location,
	send_contact,
	find_messages,
	check_whatsapp_number
)


class WhatsappChat(Document):

	@frappe.whitelist()
	def send_message(self):
		"""Send message based on message_type."""
		if not self.instance:
			frappe.throw("Please select a WhatsApp Instance.")
		if not self.recipient_number:
			frappe.throw("Please enter a recipient number.")

		try:
			response = None

			if self.message_type == "Text":
				if not self.message:
					frappe.throw("Please enter a message.")
				response = send_text(self.instance, self.recipient_number, self.message)

			elif self.message_type == "Media":
				if not self.media_url:
					frappe.throw("Please enter a media URL.")
				response = send_media(
					self.instance,
					self.recipient_number,
					self.media_url,
					mediatype=self.media_type or "image",
					caption=self.caption or ""
				)

			elif self.message_type == "Audio":
				if not self.media_url:
					frappe.throw("Please enter an audio URL.")
				response = send_audio(self.instance, self.recipient_number, self.media_url)

			elif self.message_type == "Location":
				if not self.latitude or not self.longitude:
					frappe.throw("Please enter latitude and longitude.")
				response = send_location(
					self.instance,
					self.recipient_number,
					self.location_name or "",
					self.location_address or "",
					self.latitude,
					self.longitude
				)

			elif self.message_type == "Contact":
				frappe.throw("Contact sending requires contact data. Use the API directly.")

			# Log the message
			if response:
				message_id = ""
				if isinstance(response, dict):
					key = response.get("key", {})
					message_id = key.get("id", "")

				# Create message log
				log = frappe.get_doc({
					"doctype": "Whatsapp Message Log",
					"instance": self.instance,
					"direction": "Outbound",
					"status": "Sent",
					"recipient_number": self.recipient_number,
					"message_id": message_id,
					"message_body": self._get_message_summary()
				})
				log.insert(ignore_permissions=True)

				self.status = "Sent"
				self.save()
				frappe.db.commit()

			return response

		except Exception as e:
			self.status = "Failed"
			self.save()
			frappe.db.commit()
			frappe.throw(f"Failed to send: {str(e)}")

	@frappe.whitelist()
	def send_quick_text(self, text):
		"""Send a quick text message from the chat input."""
		if not self.instance:
			frappe.throw("Please select a WhatsApp Instance first.")
		if not self.recipient_number:
			frappe.throw("Please enter a recipient number first.")
		if not text:
			frappe.throw("Please enter a message.")

		try:
			response = send_text(self.instance, self.recipient_number, text)

			message_id = ""
			if isinstance(response, dict):
				key = response.get("key", {})
				message_id = key.get("id", "")

			# Log the message
			log = frappe.get_doc({
				"doctype": "Whatsapp Message Log",
				"instance": self.instance,
				"direction": "Outbound",
				"status": "Sent",
				"recipient_number": self.recipient_number,
				"message_id": message_id,
				"message_body": text
			})
			log.insert(ignore_permissions=True)
			frappe.db.commit()

			return {"status": "sent", "message_id": message_id}

		except Exception as e:
			frappe.throw(f"Failed to send: {str(e)}")

	@frappe.whitelist()
	def load_chat_history(self):
		"""Load chat history from Message Log for this number."""
		if not self.instance or not self.recipient_number:
			return []

		# Clean number for matching
		number = self.recipient_number.strip()

		messages = frappe.get_all(
			"Whatsapp Message Log",
			filters={
				"instance": self.instance,
				"recipient_number": ["like", f"%{number}%"]
			},
			fields=["direction", "message_body", "status", "timestamp", "message_id", "creation"],
			order_by="creation asc",
			limit_page_length=100
		)

		return messages

	@frappe.whitelist()
	def verify_number(self):
		"""Check if the recipient number is on WhatsApp."""
		if not self.instance or not self.recipient_number:
			frappe.throw("Please set instance and number first.")

		try:
			result = check_whatsapp_number(self.instance, [self.recipient_number])
			return result
		except Exception as e:
			frappe.throw(f"Number check failed: {str(e)}")

	def _get_message_summary(self):
		"""Get a summary of the message for logging."""
		if self.message_type == "Text":
			return self.message or ""
		elif self.message_type == "Media":
			return f"[{self.media_type or 'Media'}] {self.caption or self.media_url or ''}"
		elif self.message_type == "Audio":
			return f"[Audio] {self.media_url or ''}"
		elif self.message_type == "Location":
			return f"[Location] {self.location_name or ''} ({self.latitude}, {self.longitude})"
		elif self.message_type == "Contact":
			return "[Contact]"
		return ""
