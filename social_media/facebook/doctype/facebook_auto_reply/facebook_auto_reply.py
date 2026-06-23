import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import json


class FacebookAutoReply(Document):
	"""Handles automatic reply configuration for Facebook messages"""

	def validate(self):
		"""Validate auto reply configuration"""
		if self.use_ai and not self.ai_prompt_template:
			frappe.throw("AI Prompt Template is required when using AI")
		
		if self.trigger_type == "Keyword Match" and not self.keywords:
			frappe.throw("Keywords are required for Keyword Match trigger type")

	def send_auto_reply(self, message_data):
		"""
		Send automatic reply to a Facebook message
		
		Args:
			message_data: Dictionary containing message details
				- sender_id: Facebook user ID
				- message_text: Original message text
				- message_id: Facebook message ID
				- page_id: Facebook page ID
		"""
		if not self.enabled:
			return
		
		try:
			# Check trigger conditions
			if not self._check_trigger(message_data):
				return
			
			# Generate or get reply text
			reply_text = self._get_reply_text(message_data)
			if not reply_text:
				return
			
			# Apply delay if configured
			if self.delay_seconds:
				frappe.enqueue(
					self._send_message_delayed,
					message_data,
					reply_text,
					job_name=f"fb_autoreply_{message_data.get('message_id')}"
				)
			else:
				self._send_message_delayed(message_data, reply_text)
		
		except Exception as e:
			frappe.log_error(f"Error sending auto reply: {str(e)}", "Facebook Auto Reply")

	def _check_trigger(self, message_data):
		"""Check if message triggers this auto reply"""
		if self.trigger_type == "All Messages":
			return True
		
		elif self.trigger_type == "Keyword Match":
			keywords = [k.strip().lower() for k in self.keywords.split(",")]
			message_text = message_data.get("message_text", "").lower()
			return any(keyword in message_text for keyword in keywords)
		
		elif self.trigger_type == "Message Sentiment":
			# In production, use an NLP library for sentiment analysis
			positive_words = ["thanks", "love", "good", "great", "amazing"]
			message_text = message_data.get("message_text", "").lower()
			return any(word in message_text for word in positive_words)
		
		elif self.trigger_type == "Image Detected":
			return message_data.get("has_image", False)
		
		return False

	def _get_reply_text(self, message_data):
		"""Get the reply text (AI generated or template)"""
		if self.use_ai:
			return self._generate_ai_reply(message_data)
		else:
			return self.reply_text

	def _generate_ai_reply(self, message_data):
		"""Generate AI-powered reply using Claude API"""
		try:
			import anthropic
			
			client = anthropic.Anthropic()
			
			# Prepare the prompt with template and message context
			prompt = self.ai_prompt_template.format(
				message_text=message_data.get("message_text", ""),
				sender_name=message_data.get("sender_name", "Customer")
			)
			
			message = client.messages.create(
				model=self.ai_model.lower().replace(" ", "-"),
				max_tokens=300,
				messages=[
					{"role": "user", "content": prompt}
				]
			)
			
			return message.content[0].text
		
		except Exception as e:
			frappe.log_error(f"AI Reply Generation Error: {str(e)}", "Facebook Auto Reply")
			return self.reply_text  # Fallback to template

	def _send_message_delayed(self, message_data, reply_text):
		"""Send the message after delay"""
		if self.delay_seconds:
			# This would be called by the job queue after delay
			pass
		
		# Send the reply (would integrate with Facebook API)
		self._send_facebook_message(
			page_id=message_data.get("page_id"),
			recipient_id=message_data.get("sender_id"),
			message_text=reply_text,
			image_url=self.reply_image if self.message_type in ["Image + Text", "Template"] else None
		)
		
		# Log the interaction
		self._create_message_log(message_data, reply_text)

	def _send_facebook_message(self, page_id, recipient_id, message_text, image_url=None):
		"""Send message via Facebook API"""
		# This integrates with the Facebook API
		# Implementation would use the facebook app's API integration
		frappe.log_error(
			f"Sending message to {recipient_id}: {message_text}",
			"Facebook Auto Reply Debug"
		)

	def _create_message_log(self, message_data, reply_text):
		"""Create a log entry for the auto reply"""
		try:
			log = frappe.get_doc({
				"doctype": "Facebook Message Log",
				"facebook_page": self.facebook_page,
				"message_type": "Outgoing",
				"sender_id": self.facebook_page,
				"recipient_id": message_data.get("sender_id"),
				"message_text": reply_text,
				"is_auto_reply": 1,
				"auto_reply_config": self.name,
				"status": "Sent"
			})
			log.insert()
		except Exception as e:
			frappe.log_error(f"Error creating message log: {str(e)}", "Facebook Auto Reply")


def process_incoming_message(message_data):
	"""
	Process incoming Facebook message and trigger auto replies
	Called by webhook handler
	"""
	try:
		auto_replies = frappe.get_all(
			"Facebook Auto Reply",
			filters={
				"facebook_page": message_data.get("page_id"),
				"enabled": 1
			}
		)
		
		for reply_config in auto_replies:
			doc = frappe.get_doc("Facebook Auto Reply", reply_config.name)
			doc.send_auto_reply(message_data)
	
	except Exception as e:
		frappe.log_error(f"Error processing incoming message: {str(e)}", "Facebook Auto Reply")
