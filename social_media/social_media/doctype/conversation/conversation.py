import frappe
from frappe.model.document import Document


class Conversation(Document):
	def validate(self):
		if not self.subject and self.participants:
			self.subject = f"Conversation with {self.participants}"