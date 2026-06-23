import frappe
from frappe.model.document import Document

class WhatsappNotification(Document):
	pass

def trigger_whatsapp_notifications(doc, method):
	"""
	Global hook to trigger WhatsApp notifications based on DocType and Event
	"""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_setup_wizard:
		return

	# Translate Frappe method to our internal Event names
	method_map = {
		"after_insert": "After Insert",
		"on_update": "After Save",
		"on_submit": "On Submit",
		"on_cancel": "On Cancel"
	}
	
	event_name = method_map.get(method)
	if not event_name:
		return

	# Find active notifications for this doctype and event
	notifications = frappe.get_all("Whatsapp Notification", 
		filters={
			"document_type": doc.doctype,
			"event": event_name,
			"enabled": 1
		}
	)

	for n in notifications:
		notification_doc = frappe.get_doc("Whatsapp Notification", n.name)
		
		# Check condition
		if notification_doc.condition:
			try:
				if not frappe.safe_eval(notification_doc.condition, None, {"doc": doc}):
					continue
			except Exception:
				# Log logic error but don't block
				frappe.log_error("WhatsApp Notification Condition Error", f"Doc: {doc.name}, Condition: {notification_doc.condition}")
				continue

		# Send notification
		send_whatsapp_notification(notification_doc, doc)



def trigger_daily_whatsapp_notifications():
	"""
	Scheduled daily hook to trigger 'Days After' and 'Days Before' notifications
	"""
	from frappe.utils import add_to_date, nowdate
	if frappe.flags.in_import or frappe.flags.in_patch:
		return

	notifications = frappe.get_all("Whatsapp Notification", 
		filters={
			"event": ["in", ["Days Before", "Days After"]],
			"enabled": 1
		}
	)

	for n in notifications:
		notification_doc = frappe.get_doc("Whatsapp Notification", n.name)
		if not notification_doc.date_changed:
			continue

		diff_days = notification_doc.days_in_advance or 0
		if notification_doc.event == "Days After":
			diff_days = -diff_days

		reference_date = add_to_date(nowdate(), days=diff_days)
		reference_date_start = reference_date + " 00:00:00.000000"
		reference_date_end = reference_date + " 23:59:59.000000"

		doc_list = frappe.get_all(
			notification_doc.document_type,
			filters=[
				{notification_doc.date_changed: (">=", reference_date_start)},
				{notification_doc.date_changed: ("<=", reference_date_end)},
			]
		)

		for d in doc_list:
			doc = frappe.get_doc(notification_doc.document_type, d.name)
			
			# Check condition
			if notification_doc.condition:
				try:
					if not frappe.safe_eval(notification_doc.condition, None, {"doc": doc}):
						continue
				except Exception:
					frappe.log_error("WhatsApp Notification Condition Error", f"Doc: {doc.name}, Condition: {notification_doc.condition}")
					continue
			
			# Send notification
			send_whatsapp_notification(notification_doc, doc)

def send_whatsapp_notification(notification_doc, doc):
	# Prepare recipients
	recipients = []
	raw_send_to = notification_doc.send_to or ""
	
	for part in raw_send_to.split(","):
		part = part.strip()
		if not part: continue
		
		if part in doc.as_dict():
			val = doc.get(part)
			if val:
				for sub_val in str(val).replace("\n", ",").split(","):
					sub_val = sub_val.strip()
					if sub_val: recipients.append(sub_val)
		else:
			recipients.append(part)
	
	recipients = list(set(recipients))
	
	if not recipients:
		return

	# Render message
	try:
		message = frappe.render_template(notification_doc.message_template, {"doc": doc})
	except Exception as e:
		frappe.log_error("WhatsApp Notification Template Error", f"Doc: {doc.name}, Template: {notification_doc.message_template}\nError: {str(e)}")
		return

	# Enqueue sending for each recipient
	for recipient in recipients:
		frappe.enqueue(
			"social_media.whatsapp.utils.send_text",
			instance_name=notification_doc.instance,
			number=recipient,
			text=message,
			now=frappe.flags.in_test
		)
