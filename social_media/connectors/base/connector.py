import frappe
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import requests
import time


class BaseConnector(ABC):
	"""Base class for all social media connectors"""
	
	def __init__(self, account_doc):
		self.account = account_doc
		self.channel = frappe.get_doc("Social Media Channel", account_doc.channel)
		self.rate_limiter = RateLimiter(self.channel.platform)
	
	@abstractmethod
	def publish_post(self, post_doc) -> Dict[str, Any]:
		"""Publish a post to the platform"""
		pass
	
	@abstractmethod
	def schedule_post(self, post_doc, scheduled_time) -> Dict[str, Any]:
		"""Schedule a post for later publishing"""
		pass
	
	@abstractmethod
	def fetch_messages(self, since=None) -> List[Dict]:
		"""Fetch new messages/comments"""
		pass
	
	@abstractmethod
	def process_webhook(self, event_data) -> Dict[str, Any]:
		"""Process incoming webhook event"""
		pass
	
	@abstractmethod
	def get_analytics(self, post_id=None, date_range=None) -> Dict[str, Any]:
		"""Get analytics data"""
		pass
	
	def refresh_token(self) -> bool:
		"""Refresh OAuth token if needed"""
		if not self.account.refresh_token:
			return False
		
		try:
			# Implementation varies by platform
			return self._refresh_oauth_token()
		except Exception as e:
			frappe.log_error(f"Token refresh failed: {str(e)}")
			return False
	
	@abstractmethod
	def _refresh_oauth_token(self) -> bool:
		"""Platform-specific token refresh"""
		pass
	
	def make_request(self, method, url, **kwargs):
		"""Make rate-limited API request"""
		self.rate_limiter.wait_if_needed()
		
		# Add auth headers
		headers = kwargs.get('headers', {})
		headers.update(self._get_auth_headers())
		kwargs['headers'] = headers
		
		response = requests.request(method, url, **kwargs)
		
		# Update rate limit info
		self.rate_limiter.update_from_response(response)
		
		if response.status_code == 401:
			# Token expired, try refresh
			if self.refresh_token():
				headers.update(self._get_auth_headers())
				response = requests.request(method, url, **kwargs)
		
		return response
	
	@abstractmethod
	def _get_auth_headers(self) -> Dict[str, str]:
		"""Get authentication headers"""
		pass


class RateLimiter:
	"""Rate limiting manager"""
	
	def __init__(self, platform):
		self.platform = platform
		self.redis_key = f"rate_limit:{platform}"
	
	def wait_if_needed(self):
		"""Wait if rate limit exceeded"""
		# Simple implementation - can be enhanced with Redis
		pass
	
	def update_from_response(self, response):
		"""Update rate limit info from API response"""
		# Extract rate limit headers and update Redis
		pass