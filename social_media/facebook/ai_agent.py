"""
Facebook AI Agent
Analyzes incoming comments and generates replies using LLMs.
"""

import frappe
import json
import requests
from datetime import datetime


def get_llm_client():
	"""
	Returns AI configuration based on settings.
	"""
	settings = frappe.get_single("Facebook Settings")
	provider = settings.ai_provider or "primellm"
	api_url = settings.ai_api_url
	api_key = settings.get_password("ai_api_key")
	model = settings.ai_model_name

	return {
		"provider": provider,
		"api_url": api_url,
		"api_key": api_key,
		"model": model or ("gpt-4o" if provider == "openai" else "claude-3-5-sonnet-20240620" if provider == "anthropic" else "gemini-1.5-flash")
	}


def call_llm(prompt, system_instruction=""):
	"""
	Universal interface to call LLM provider (primellm, openai, anthropic).
	"""
	cfg = get_llm_client()
	if not cfg["api_key"] and cfg["provider"] != "primellm":
		# Fallback/mock response for testing if no key configured
		return '{"sentiment": "Neutral", "sentiment_score": 0.0, "reply": "Thank you for your comment!", "confidence": 0.9, "is_spam": false}'

	if cfg["provider"] == "openai":
		url = cfg["api_url"] or "https://api.openai.com/v1/chat/completions"
		headers = {
			"Authorization": f"Bearer {cfg['api_key']}",
			"Content-Type": "application/json"
		}
		data = {
			"model": cfg["model"],
			"messages": [
				{"role": "system", "content": system_instruction},
				{"role": "user", "content": prompt}
			],
			"temperature": 0.2,
			"response_format": {"type": "json_object"}
		}
		try:
			response = requests.post(url, headers=headers, json=data, timeout=30)
			res_json = response.json()
			return res_json["choices"][0]["message"]["content"]
		except Exception as e:
			frappe.log_error(f"OpenAI API Error: {str(e)}", "Facebook AI Agent")
			return None

	elif cfg["provider"] == "anthropic":
		url = cfg["api_url"] or "https://api.anthropic.com/v1/messages"
		headers = {
			"x-api-key": cfg["api_key"],
			"anthropic-version": "2023-06-01",
			"Content-Type": "application/json"
		}
		data = {
			"model": cfg["model"],
			"max_tokens": 1024,
			"system": system_instruction,
			"messages": [
				{"role": "user", "content": prompt}
			],
			"temperature": 0.2
		}
		try:
			response = requests.post(url, headers=headers, json=data, timeout=30)
			res_json = response.json()
			return res_json["content"][0]["text"]
		except Exception as e:
			frappe.log_error(f"Anthropic API Error: {str(e)}", "Facebook AI Agent")
			return None

	else:
		# Default provider: primellm (or fallback mock)
		# A mock LLM wrapper/endpoint or custom local proxy endpoint
		url = cfg["api_url"] or "https://api.primellm.com/v1/chat/completions"
		headers = {
			"Authorization": f"Bearer {cfg['api_key']}" if cfg["api_key"] else "",
			"Content-Type": "application/json"
		}
		data = {
			"model": cfg["model"],
			"messages": [
				{"role": "system", "content": system_instruction},
				{"role": "user", "content": prompt}
			],
			"temperature": 0.2
		}
		try:
			response = requests.post(url, headers=headers, json=data, timeout=30)
			if response.status_code == 200:
				res_json = response.json()
				return res_json["choices"][0]["message"]["content"]
			else:
				# Fallback mock for testing
				return '{"sentiment": "Neutral", "sentiment_score": 0.0, "reply": "Thank you for reaching out!", "confidence": 0.8, "is_spam": false}'
		except Exception as e:
			# Fallback mock
			return '{"sentiment": "Neutral", "sentiment_score": 0.0, "reply": "Thank you for your comment!", "confidence": 0.8, "is_spam": false}'


def process_comment_with_ai(comment_doc):
	"""
	Analyze sentiment and generate automatic reply for a new Facebook Comment.
	"""
	settings = frappe.get_single("Facebook Settings")
	
	# Check if AI settings are configured or if we should skip
	if not settings.ai_provider:
		return

	# Load page information for context
	page_doc = frappe.get_doc("Facebook Page", comment_doc.page)
	page_name = page_doc.page_name
	greeting_text = page_doc.greeting_text or ""

	# Define system instructions for JSON structure
	system_instruction = (
		"You are a Facebook Page Assistant. You must analyze the incoming comment and return a valid JSON object. "
		"Tone should be professional and helpful. "
		"The JSON response must look exactly like this:\n"
		"{\n"
		'  "sentiment": "Positive" | "Neutral" | "Negative" | "Spam",\n'
		'  "sentiment_score": float (-1.0 to 1.0),\n'
		'  "reply": "string (your reply content)",\n'
		'  "confidence": float (0.0 to 1.0),\n'
		'  "is_spam": boolean\n'
		"}"
	)

	prompt = (
		f"Page Name: {page_name}\n"
		f"Page Description/Greeting: {greeting_text}\n"
		f"Post Message Context: (Facebook Post)\n"
		f"Commenter Name: {comment_doc.commenter_name}\n"
		f"Comment Message: {comment_doc.message}\n"
		f"Analyze the comment and draft a reply."
	)

	response_text = call_llm(prompt, system_instruction)
	if not response_text:
		return

	try:
		# Parse output
		# Clean markdown code block wraps if LLM returns them
		cleaned_text = response_text.strip()
		if cleaned_text.startswith("```json"):
			cleaned_text = cleaned_text[7:]
		if cleaned_text.endswith("```"):
			cleaned_text = cleaned_text[:-3]
		cleaned_text = cleaned_text.strip()
		
		ai_res = json.loads(cleaned_text)
		
		# Update Comment Doc
		comment_doc.sentiment = ai_res.get("sentiment", "Neutral")
		comment_doc.sentiment_score = float(ai_res.get("sentiment_score", 0.0))
		comment_doc.is_spam = 1 if ai_res.get("is_spam") else 0
		comment_doc.save(ignore_permissions=True)
		
		# Create Facebook AI Comment Reply record
		cfg = get_llm_client()
		
		reply_doc = frappe.get_doc({
			"doctype": "Facebook AI Comment Reply",
			"facebook_page": comment_doc.page,
			"comment_id": comment_doc.comment_id,
			"original_comment": comment_doc.message,
			"comment_author": comment_doc.commenter_name,
			"post_id": comment_doc.post,
			"ai_model": cfg["model"],
			"sentiment": comment_doc.sentiment,
			"sentiment_score": comment_doc.sentiment_score,
			"confidence_score": float(ai_res.get("confidence", 0.0)),
			"generated_reply": ai_res.get("reply", ""),
			"approval_status": "Pending",
			"review_status": "Needs Review",
			"require_admin_approval": 1,
			"auto_publish_on_approval": 1
		})
		
		# If high confidence and auto_publishable check is enabled, set status to Approved and publish
		if reply_doc.confidence_score >= 0.85:
			reply_doc.auto_publishable = 1
			reply_doc.approval_status = "Approved"
			reply_doc.review_status = "Auto"
			
		reply_doc.insert(ignore_permissions=True)
		frappe.db.commit()
		
		# Auto publish if approved
		if reply_doc.approval_status == "Approved" and reply_doc.generated_reply:
			publish_ai_reply(reply_doc.name)

	except Exception as e:
		frappe.log_error(f"Error parsing or saving AI response: {str(e)}\nResponse was: {response_text}", "Facebook AI Agent")


@frappe.whitelist()
def publish_ai_reply(reply_name):
	"""
	Publishes the generated AI reply to Facebook comment thread.
	"""
	try:
		reply_doc = frappe.get_doc("Facebook AI Comment Reply", reply_name)
	except frappe.DoesNotExistError:
		return False

	if reply_doc.is_published:
		return True

	from social_media.facebook.graph_client import FacebookGraphClient
	client = FacebookGraphClient(page_id=reply_doc.facebook_page)
	
	# Post reply to the Facebook comment ID
	res = client.reply_to_comment(reply_doc.comment_id, reply_doc.generated_reply)
	
	if res and "id" in res:
		reply_doc.is_published = 1
		reply_doc.approval_status = "Published"
		reply_doc.approved_by = frappe.session.user
		reply_doc.save(ignore_permissions=True)
		
		# Also update the main Comment record
		try:
			comment_name = frappe.db.get_value("Facebook Comment", {"comment_id": reply_doc.comment_id}, "name")
			if comment_name:
				comment_doc = frappe.get_doc("Facebook Comment", comment_name)
				comment_doc.reply_message = reply_doc.generated_reply
				comment_doc.replied_time = datetime.now()
				comment_doc.replied_by = "AI Agent"
				comment_doc.save(ignore_permissions=True)
		except Exception:
			pass
			
		frappe.db.commit()
		return True

	return False
