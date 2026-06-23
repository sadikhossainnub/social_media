import frappe
import re
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec
from frappe.utils import get_datetime, getdate, now_datetime


class ScheduledWhatsappMessage(Document):
	def validate(self):
		self._validate_recipient()
		self._validate_schedule()

	def _validate_recipient(self):
		if self.recipient_type == "Employee" and not self.employee:
			frappe.throw("Please select an Employee.")
		if self.recipient_type == "Customer" and not self.customer:
			frappe.throw("Please select a Customer.")
		if self.recipient_type == "Custom Number" and not self.whatsapp_number:
			frappe.throw("Please enter at least one Whatsapp Number.")
		if self.recipient_type in ("Employee", "Customer") and not self.recipient_fields:
			frappe.throw("Please set Recipient Number Fields.")

	def _validate_schedule(self):
		if self.trigger_frequency == "Weekly" and not self.weekday:
			frappe.throw("Please select Weekday for Weekly trigger.")
		if self.trigger_frequency == "Monthly" and not self.day_of_month:
			frappe.throw("Please set Day of Month for Monthly trigger.")
		if self.trigger_frequency == "Yearly" and (not self.month_of_year or not self.day_of_month):
			frappe.throw("Please set Month and Day for Yearly trigger.")
		if self.trigger_frequency == "Specific Date" and not self.specific_date:
			frappe.throw("Please select Specific Date.")


@frappe.whitelist()
def send_now(name):
	doc = frappe.get_doc("Scheduled Whatsapp Message", name)
	doc.check_permission("read")

	recipient_targets = _get_recipient_targets(doc)
	if not recipient_targets:
		frappe.throw("No valid recipient number found for this message.")

	context_doc = _get_context_doc_from_script(doc)
	if (getattr(doc, "context_script", None) or "").strip() and context_doc is None:
		frappe.throw("Context script failed. Check Error Log: Scheduled Whatsapp Message Context Script Error")

	# list of dicts হলে per-item message পাঠাও
	if isinstance(context_doc, list):
		if not context_doc:
			frappe.throw("Context script returned empty result.")
		sent = 0
		for item in context_doc:
			for target in recipient_targets:
				context = {"scheduled_message": doc, "frappe": frappe}
				context.update(item)
				context.update(_build_recipient_context(target))
				if not _evaluate_condition(doc, context):
					continue
				message = _render_message(doc, context)
				frappe.enqueue(
					"social_media.whatsapp.utils.send_text",
					instance_name=doc.instance,
					number=target["number"],
					text=message,
					now=True,
				)
				sent += 1
		if sent == 0:
			frappe.throw("Condition did not match. Message was not sent.")
		return {"status": "queued", "sent": sent}

	# পুরনো behavior
	sent = 0
	for target in recipient_targets:
		context = _build_template_context(doc)
		context.update(_build_recipient_context(target))
		if not _evaluate_condition(doc, context):
			continue
		message = _render_message(doc, context)
		frappe.enqueue(
			"social_media.whatsapp.utils.send_text",
			instance_name=doc.instance,
			number=target["number"],
			text=message,
			now=True,
		)
		sent += 1
	if sent == 0:
		frappe.throw("Condition did not match. Message was not sent.")
	return {"status": "queued", "recipient_numbers": [d["number"] for d in recipient_targets], "sent": sent}


def process_scheduled_whatsapp_messages():
	"""Run every minute and send pending daily messages."""
	if frappe.flags.in_import or frappe.flags.in_patch:
		return

	now = now_datetime()
	today = getdate(now)

	messages = frappe.get_all(
		"Scheduled Whatsapp Message",
		filters={"enabled": 1},
		fields=[
			"name", "instance", "send_time", "trigger_frequency", "weekday", "day_of_month", "month_of_year", "specific_date",
			"recipient_type", "employee", "customer", "recipient_fields", "whatsapp_number",
			"context_script", "condition_expression", "message", "last_sent_on"
		],
	)

	for row in messages:
		if not row.send_time:
			continue

		scheduled_dt = get_datetime(f"{today} {row.send_time}")
		if now < scheduled_dt:
			continue

		if not _is_due_for_today(row, today):
			continue

		if row.last_sent_on and getdate(row.last_sent_on) == today:
			continue

		recipient_targets = _get_recipient_targets(row)
		if not recipient_targets:
			frappe.log_error(
				title="Scheduled Whatsapp Message Recipient Missing",
				message=f"Message: {row.name}, Recipient Type: {row.recipient_type}",
			)
			continue

		context_doc = _get_context_doc_from_script(row)
		if (getattr(row, "context_script", None) or "").strip() and context_doc is None:
			continue

		if isinstance(context_doc, list):
			if not context_doc:
				continue
			sent = 0
			for item in context_doc:
				for target in recipient_targets:
					context = {"scheduled_message": row, "frappe": frappe}
					context.update(item)
					context.update(_build_recipient_context(target))
					if not _evaluate_condition(row, context):
						continue
					message = _render_message(row, context)
					frappe.enqueue(
						"social_media.whatsapp.utils.send_text",
						instance_name=row.instance,
						number=target["number"],
						text=message,
						now=frappe.flags.in_test,
					)
					sent += 1
			if sent > 0:
				frappe.db.set_value(
					"Scheduled Whatsapp Message", row.name,
					"last_sent_on", today, update_modified=False
				)
		else:
			# পুরনো behavior
			sent = 0
			for target in recipient_targets:
				context = _build_template_context(row)
				context.update(_build_recipient_context(target))
				if not _evaluate_condition(row, context):
					continue
				message = _render_message(row, context)
				frappe.enqueue(
					"social_media.whatsapp.utils.send_text",
					instance_name=row.instance,
					number=target["number"],
					text=message,
					now=frappe.flags.in_test,
				)
				sent += 1
			if sent > 0:
				frappe.db.set_value(
					"Scheduled Whatsapp Message", row.name,
					"last_sent_on", today, update_modified=False
				)


def _get_recipient_numbers(row):
	return [d["number"] for d in _get_recipient_targets(row)]


def _get_recipient_targets(row):
	targets = []
	if row.recipient_type == "Custom Number":
		for number in _split_numbers(row.whatsapp_number):
			targets.append({"number": number})
		return targets

	fieldnames = _split_fieldnames(getattr(row, "recipient_fields", None))
	if not fieldnames:
		return []

	if row.recipient_type == "Customer" and row.customer:
		customer_name = frappe.db.get_value("Customer", row.customer, "customer_name") or row.customer
		for number in _numbers_from_linked_doc("Customer", row.customer, fieldnames):
			targets.append({
				"number": number,
				"customer": row.customer,
				"customer_name": customer_name,
			})
		return targets

	if row.recipient_type == "Employee":
		if isinstance(getattr(row, "employee", None), list):
			employees = [emp.employee for emp in row.employee if getattr(emp, "employee", None)]
		else:
			employees = frappe.get_all(
				"Scheduled Whatsapp Message Employee",
				filters={"parent": getattr(row, "name", ""), "parenttype": "Scheduled Whatsapp Message"},
				pluck="employee"
			)

		if employees:
			for emp in employees:
				if not emp:
					continue
				employee_name = frappe.db.get_value("Employee", emp, "employee_name") or emp
				for number in _numbers_from_linked_doc("Employee", emp, fieldnames):
					targets.append({
						"number": number,
						"employee": emp,
						"employee_name": employee_name,
					})
			# Deduplicate by number while keeping first mapped details
			return list({t["number"]: t for t in targets}.values())

	return []


def _build_recipient_context(target):
	context = {
		"recipient_number": target.get("number"),
	}
	if target.get("employee"):
		context["employee"] = target.get("employee")
	if target.get("employee_name"):
		# Keep template backward-compatible: {{ employee_name }} resolves to receiver name
		context["employee_name"] = target.get("employee_name")
	if target.get("customer"):
		context["customer"] = target.get("customer")
	if target.get("customer_name"):
		context["customer_name"] = target.get("customer_name")
	return context


def _split_fieldnames(raw_fieldnames):
	if not raw_fieldnames:
		return []
	return [field.strip() for field in str(raw_fieldnames).replace("\n", ",").split(",") if field.strip()]


def _split_numbers(raw_numbers):
	if not raw_numbers:
		return []
	numbers = []
	for line in str(raw_numbers).splitlines():
		number = line.strip()
		if number:
			if number.startswith('+'):
				number = number[1:]
			if not number.startswith('880'):
				if number.startswith('0'):
					number = '88' + number
				else:
					number = '880' + number
			numbers.append(number)
	return list(dict.fromkeys(numbers))


def _numbers_from_linked_doc(doctype, docname, fieldnames):
	meta = frappe.get_meta(doctype)
	numbers = []
	for fieldname in fieldnames:
		if not meta.has_field(fieldname):
			continue
		value = frappe.db.get_value(doctype, docname, fieldname)
		numbers.extend(_split_numbers(value))
	return list(dict.fromkeys(numbers))


def _is_due_for_today(row, today):
	frequency = getattr(row, "trigger_frequency", None) or "Daily"
	if frequency == "Daily":
		return True
	if frequency == "Weekly":
		return (getattr(row, "weekday", None) or "") == today.strftime("%A")
	if frequency == "Monthly":
		return int(getattr(row, "day_of_month", 0) or 0) == today.day
	if frequency == "Yearly":
		month_value = _month_to_int(getattr(row, "month_of_year", None))
		day_value = int(getattr(row, "day_of_month", 0) or 0)
		return month_value == today.month and day_value == today.day
	if frequency == "Specific Date":
		specific_date = getattr(row, "specific_date", None)
		return bool(specific_date) and getdate(specific_date) == today
	return False


def _month_to_int(month_name):
	months = {
		"January": 1, "February": 2, "March": 3, "April": 4,
		"May": 5, "June": 6, "July": 7, "August": 8,
		"September": 9, "October": 10, "November": 11, "December": 12
	}
	return months.get(month_name)


def _build_template_context(row):
	context = {
		"scheduled_message": row,
		"frappe": frappe,
	}
	context_doc = _get_context_doc_from_script(row)

	if isinstance(context_doc, list):
		# list হলে প্রথম item দিয়ে context build করো
		# (multiple messages এর জন্য send function এ handle হবে)
		context["result_list"] = context_doc
		if context_doc:
			context.update(context_doc[0])
	elif context_doc:
		context["doc"] = context_doc
		context.update(context_doc.as_dict())

	return context


def _get_context_doc_from_script(row):
	script = (getattr(row, "context_script", None) or "").strip()
	if not script:
		return None

	try:
		def _nowdate():
			return frappe.db.sql("select curdate()", as_list=1)[0][0]

		def _get_all(doctype, *args, **kwargs):
			return frappe.get_all(doctype, *args, **kwargs)

		def _db_get_value(doctype, docname, fieldname):
			return frappe.db.get_value(doctype, docname, fieldname)

		def _db_sql(query, values=None, as_dict=False, as_list=False):
			return frappe.db.sql(query, values=values, as_dict=as_dict, as_list=as_list)

		_locals = {
			"result": [],
			"scheduled_message": row,
			"nowdate": _nowdate,
			"get_all": _get_all,
			"db_get_value": _db_get_value,
			"db_sql": _db_sql,
			# Backward-compatible safe proxy for context scripts using frappe.get_all / frappe.db.*
			"frappe": frappe._dict(
				get_all=_get_all,
				db=frappe._dict(
					get_value=_db_get_value,
					sql=_db_sql,
				),
			),
		}
		safe_exec(script, _globals=None, _locals=_locals)
		config = _locals.get("result")
	except Exception:
		frappe.log_error(
			title="Scheduled Whatsapp Message Context Script Error",
			message=f"Message: {getattr(row, 'name', '')}\nScript: {script}\n{frappe.get_traceback()}",
		)
		return None

	# নতুন: list of dicts হলে সরাসরি return
	if isinstance(config, list):
		return config

	# পুরনো behavior: str বা dict হলে Frappe Doc fetch
	if isinstance(config, str):
		doctype = config
		filters = {}
		docname = None
	elif isinstance(config, dict):
		doctype = config.get("doctype")
		filters = config.get("filters") or {}
		docname = config.get("name")
	else:
		return None

	if not doctype:
		return None

	try:
		if docname:
			return frappe.get_doc(doctype, docname)
		docnames = frappe.get_all(doctype, filters=filters, pluck="name", limit=1)
		if not docnames:
			return None
		return frappe.get_doc(doctype, docnames[0])
	except Exception:
		frappe.log_error(
			title="Scheduled Whatsapp Message Context Fetch Error",
			message=f"Message: {getattr(row, 'name', '')}\nDocType: {doctype}\n{frappe.get_traceback()}",
		)
		return None


def _evaluate_condition(row, context):
	expression = (getattr(row, "condition_expression", None) or "").strip()
	if not expression:
		return True

	normalized = _normalize_condition_expression(expression)
	try:
		return bool(frappe.safe_eval(normalized, None, context))
	except Exception:
		frappe.log_error(
			title="Scheduled Whatsapp Message Condition Error",
			message=f"Message: {getattr(row, 'name', '')}\nCondition: {expression}\n{frappe.get_traceback()}",
		)
		return False


def _normalize_condition_expression(expression):
	# Allow business-style equality input like: 100*10+40=1040
	if "=" in expression and "==" not in expression and "!=" not in expression and ">=" not in expression and "<=" not in expression:
		return expression.replace("=", "==")
	return expression


def _render_message(row, context):
	template = getattr(row, "message", "") or ""
	try:
		return frappe.render_template(template, context)
	except Exception:
		# Retry once with default empty values for simple placeholders like {{ invoice }}.
		try:
			recovered_context = dict(context or {})
			for varname in _extract_simple_template_variables(template):
				recovered_context.setdefault(varname, "")
			return frappe.render_template(template, recovered_context)
		except Exception:
			pass
		frappe.log_error(
			title="Scheduled Whatsapp Message Template Error",
			message=f"Message: {getattr(row, 'name', '')}\nTemplate: {template}\n{frappe.get_traceback()}",
		)
		return template


def _extract_simple_template_variables(template):
	return set(re.findall(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}", template or ""))
