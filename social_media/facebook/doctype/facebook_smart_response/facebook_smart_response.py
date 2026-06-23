import frappe
from frappe.model.document import Document
import json


class FacebookSmartResponse(Document):
	"""Generates smart response suggestions using AI"""

	def validate(self):
		"""Validate smart response configuration"""
		if not self.user_query:
			frappe.throw("User Query is required")

	def on_submit(self):
		"""Generate response options when submitted"""
		self.generate_response_options()

	def generate_response_options(self):
		"""
		Generate multiple response options using AI
		"""
		try:
			import anthropic
			
			client = anthropic.Anthropic()
			
			# Build system prompt
			system_prompt = self.system_prompt or self._get_default_system_prompt()
			
			# Build the user prompt
			context_info = f"Conversation Context:\n{self.conversation_context}" if self.conversation_context else ""
			
			prompt = f"""You are a helpful customer service representative for an ecommerce store.

{context_info}

Customer Query: {self.user_query}

Generate 3 different response options that:
1. Are professional and helpful
2. Maintain the brand voice
3. Vary in tone and approach
4. Can include product suggestions if relevant
5. Use Banglish (Bengali + English mix) when appropriate

Format your response as a JSON object with this exact structure:
{{
  "options": [
    {{"text": "First response option here", "tone": "professional|friendly|urgent"}},
    {{"text": "Second response option here", "tone": "professional|friendly|urgent"}},
    {{"text": "Third response option here", "tone": "professional|friendly|urgent"}}
  ]
}}"""
			
			response = client.messages.create(
				model="claude-3-5-sonnet-20241022",
				max_tokens=self.max_tokens,
				temperature=self.temperature,
				system=system_prompt,
				messages=[
					{"role": "user", "content": prompt}
				]
			)
			
			response_text = response.content[0].text
			
			# Parse JSON response
			try:
				import re
				json_match = re.search(r'\{[\s\S]*\}', response_text)
				if json_match:
					response_data = json.loads(json_match.group())
					options = response_data.get("options", [])
					
					if len(options) > 0:
						self.option_1 = options[0].get("text", "")
						self.option_1_score = 0.9
					if len(options) > 1:
						self.option_2 = options[1].get("text", "")
						self.option_2_score = 0.8
					if len(options) > 2:
						self.option_3 = options[2].get("text", "")
						self.option_3_score = 0.7
					
					# Auto-select the best option
					self.selected_option = "Option 1"
			
			except json.JSONDecodeError:
				frappe.log_error(f"Failed to parse response: {response_text}", "Facebook Smart Response")
				self._set_fallback_responses()
		
		except Exception as e:
			frappe.log_error(f"Error generating response options: {str(e)}", "Facebook Smart Response")
			self._set_fallback_responses()

	def _get_default_system_prompt(self):
		"""Get the default system prompt for response generation"""
		return """You are a helpful, professional customer service representative for a fashion ecommerce business.

Your responsibilities:
- Provide accurate and helpful information
- Maintain a friendly yet professional tone
- Use the brand voice appropriately
- Include relevant product information when applicable
- Offer solutions and alternatives when needed
- Show genuine interest in customer satisfaction
- Use Banglish (Bengali + English mix) naturally when appropriate

Always prioritize customer satisfaction and brand reputation."""

	def _set_fallback_responses(self):
		"""Set fallback responses if AI generation fails"""
		self.option_1 = "Thank you for reaching out! We appreciate your inquiry. How can we assist you further?"
		self.option_1_score = 0.5
		self.option_2 = "We'd love to help! Could you provide more details about your question?"
		self.option_2_score = 0.5
		self.option_3 = "Thanks for getting in touch! Our team is here to support you."
		self.option_3_score = 0.5

	def use_response(self, option_number):
		"""
		Use a selected response option
		
		Args:
			option_number: 1, 2, or 3
		"""
		valid_options = {
			1: self.option_1,
			2: self.option_2,
			3: self.option_3
		}
		
		if option_number not in valid_options:
			frappe.throw(f"Invalid option number: {option_number}")
		
		selected_text = valid_options[option_number]
		self.selected_option = f"Option {option_number}"
		self.save()
		
		return {
			"success": True,
			"response": selected_text,
			"message": f"Response option {option_number} selected"
		}

	def get_score_percentages(self):
		"""Get scores as percentages for UI display"""
		return {
			"option_1": f"{(self.option_1_score or 0) * 100:.0f}%",
			"option_2": f"{(self.option_2_score or 0) * 100:.0f}%",
			"option_3": f"{(self.option_3_score or 0) * 100:.0f}%"
		}

	def regenerate_options(self):
		"""Regenerate response options"""
		self.option_1 = None
		self.option_2 = None
		self.option_3 = None
		self.generate_response_options()
		self.save()


@frappe.whitelist()
def generate_smart_response(page_id, query, context="", response_type="General Question"):
	"""
	API endpoint to generate smart responses
	
	Args:
		page_id: Facebook page ID
		query: User query/question
		context: Conversation context (optional)
		response_type: Type of response needed
	
	Returns:
		Dictionary with response options
	"""
	try:
		doc = frappe.get_doc({
			"doctype": "Facebook Smart Response",
			"facebook_page": page_id,
			"user_query": query,
			"conversation_context": context,
			"response_type": response_type,
			"ai_model": "Claude 3.5 Sonnet",
			"temperature": 0.7,
			"max_tokens": 500
		})
		doc.insert()
		doc.submit()
		
		return {
			"success": True,
			"doc_name": doc.name,
			"options": [
				{"text": doc.option_1, "score": doc.option_1_score},
				{"text": doc.option_2, "score": doc.option_2_score},
				{"text": doc.option_3, "score": doc.option_3_score}
			]
		}
	
	except Exception as e:
		frappe.log_error(f"Error generating smart response: {str(e)}", "Facebook Smart Response")
		return {
			"success": False,
			"error": str(e)
		}
