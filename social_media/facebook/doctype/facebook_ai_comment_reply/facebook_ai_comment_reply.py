import frappe
from frappe.model.document import Document
import json
import re


class FacebookAICommentReply(Document):
	"""Handles AI-powered comment replies for Facebook posts"""

	def validate(self):
		"""Validate AI comment reply configuration"""
		if not self.original_comment:
			frappe.throw("Original comment text is required")

	def on_submit(self):
		"""Called when document is submitted"""
		self.analyze_sentiment()
		self.generate_ai_reply()

	def analyze_sentiment(self):
		"""
		Analyze the sentiment of the comment using AI
		Updates sentiment and sentiment_score fields
		"""
		try:
			import anthropic
			
			client = anthropic.Anthropic()
			
			prompt = f"""Analyze the sentiment of this Facebook comment and respond with JSON format only:
Comment: "{self.original_comment}"

Respond with this exact JSON format (no other text):
{{"sentiment": "Positive|Neutral|Negative", "score": 0.5}}

Where score is between -1 (very negative) and 1 (very positive)."""
			
			response = client.messages.create(
				model="claude-3-5-sonnet-20241022",
				max_tokens=200,
				messages=[
					{"role": "user", "content": prompt}
				]
			)
			
			# Parse the JSON response
			response_text = response.content[0].text
			try:
				# Extract JSON from response
				json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
				if json_match:
					sentiment_data = json.loads(json_match.group())
					self.sentiment = sentiment_data.get("sentiment", "Neutral")
					self.sentiment_score = sentiment_data.get("score", 0)
			except json.JSONDecodeError:
				frappe.log_error(f"Failed to parse sentiment response: {response_text}", "Facebook AI Comment Reply")
				self.sentiment = "Neutral"
				self.sentiment_score = 0
		
		except Exception as e:
			frappe.log_error(f"Error analyzing sentiment: {str(e)}", "Facebook AI Comment Reply")
			self.sentiment = "Neutral"

	def generate_ai_reply(self):
		"""
		Generate an AI-powered reply to the comment
		"""
		try:
			import anthropic
			
			client = anthropic.Anthropic()
			
			# Build the prompt based on sentiment and tone
			tone_instructions = self._get_tone_instructions()
			
			prompt = f"""You are a helpful brand representative for a fashion ecommerce store.
A customer left this comment on a social media post:
"{self.original_comment}"

Comment author: {self.comment_author}
Detected sentiment: {self.sentiment}

Reply tone: {self.reply_tone or 'Professional'}
{tone_instructions}

Generate a thoughtful, engaging reply (1-3 sentences max) that:
1. Acknowledges their comment
2. Shows genuine interest
3. Offers value or resolution if needed
4. Uses appropriate Bangla-English mix language (Banglish) when relevant
5. Matches the brand voice

Reply:"""
			
			response = client.messages.create(
				model="claude-3-5-sonnet-20241022",
				max_tokens=300,
				messages=[
					{"role": "user", "content": prompt}
				]
			)
			
			self.generated_reply = response.content[0].text
			self.approval_status = "Pending"
			
			if self.require_admin_approval:
				self._notify_admin_for_approval()
		
		except Exception as e:
			frappe.log_error(f"Error generating AI reply: {str(e)}", "Facebook AI Comment Reply")
			self.generated_reply = "Thank you for your comment! We appreciate your feedback."

	def _get_tone_instructions(self):
		"""Get tone-specific instructions for the AI"""
		tone_map = {
			"Professional": "Keep a professional, business-like tone.",
			"Friendly": "Be warm, friendly and approachable.",
			"Humorous": "Use light humor where appropriate to engage.",
			"Brand Voice": "Match the brand's unique personality and voice."
		}
		return tone_map.get(self.reply_tone, "Keep a professional, friendly tone.")

	def publish_reply(self):
		"""
		Publish the AI-generated reply to Facebook
		"""
		if self.is_published:
			frappe.throw("This reply has already been published")
		
		if self.approval_status not in ["Approved", "Pending"] and self.require_admin_approval:
			frappe.throw(f"Cannot publish reply with status: {self.approval_status}")
		
		try:
			# Here you would integrate with Facebook API
			# For now, just log the action
			frappe.log_error(
				f"Publishing reply to comment {self.comment_id}: {self.generated_reply}",
				"Facebook AI Comment Reply Debug"
			)
			
			self.is_published = 1
			self.approval_status = "Published"
			self.save()
			
			# Create audit log
			self._create_audit_log("published")
		
		except Exception as e:
			frappe.log_error(f"Error publishing reply: {str(e)}", "Facebook AI Comment Reply")
			frappe.throw(f"Failed to publish reply: {str(e)}")

	def reject_reply(self, reason=""):
		"""Reject the AI-generated reply"""
		if self.is_published:
			frappe.throw("Cannot reject an already published reply")
		
		self.approval_status = "Rejected"
		self.save()
		self._create_audit_log("rejected", reason)

	def _notify_admin_for_approval(self):
		"""Send notification to admin for reply approval"""
		try:
			# Get admin users
			admin_users = frappe.get_all(
				"User",
				filters={"roles": "Administrator"},
				fields=["name", "email"]
			)
			
			subject = f"AI Comment Reply Pending Approval - {self.comment_author}"
			message = f"""
A new AI-generated comment reply is pending your approval:

Comment: {self.original_comment[:100]}...
From: {self.comment_author}
Sentiment: {self.sentiment}

Generated Reply:
{self.generated_reply}

Please review and approve/reject this reply.
Link: {frappe.utils.get_url()}/app/facebook-ai-comment-reply/{self.name}
"""
			
			for user in admin_users:
				if user.email:
					frappe.sendmail(
						recipients=[user.email],
						subject=subject,
						message=message
					)
		
		except Exception as e:
			frappe.log_error(f"Error sending approval notification: {str(e)}", "Facebook AI Comment Reply")

	def _create_audit_log(self, action, details=""):
		"""Create an audit log for actions taken"""
		try:
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Facebook AI Comment Reply",
				"reference_name": self.name,
				"comment_email": frappe.session.user,
				"comment_by": frappe.session.user,
				"content": f"Action: {action} | Details: {details}"
			}).insert()
		except Exception as e:
			frappe.log_error(f"Error creating audit log: {str(e)}", "Facebook AI Comment Reply")


def process_new_comment(comment_data):
	"""
	Process a new Facebook comment and generate AI reply
	Called by webhook handler
	
	Args:
		comment_data: Dictionary with comment details
			- comment_id: Facebook comment ID
			- post_id: Facebook post ID
			- comment_text: The comment text
			- author_name: Comment author's name
			- page_id: Facebook page ID
	"""
	try:
		# Create new AI comment reply document
		doc = frappe.get_doc({
			"doctype": "Facebook AI Comment Reply",
			"facebook_page": comment_data.get("page_id"),
			"comment_id": comment_data.get("comment_id"),
			"original_comment": comment_data.get("comment_text"),
			"comment_author": comment_data.get("author_name"),
			"post_id": comment_data.get("post_id"),
			"ai_model": "Claude 3.5 Sonnet",
			"reply_tone": "Brand Voice"
		})
		doc.insert()
		doc.submit()
		
		# Auto-publish if configured
		if not doc.require_admin_approval:
			doc.publish_reply()
	
	except Exception as e:
		frappe.log_error(f"Error processing new comment: {str(e)}", "Facebook AI Comment Reply")
