# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Action Library for Automation Rules.

Contains all action executors organized in two tiers:
  A. Business-safe no-code actions
  B. Advanced actions for power users

Each action function has the signature:
    execute_<action>(step, doc, rule, context) -> str | None

Where:
    step: The Automation Action Step child row
    doc: The triggering document
    rule: The parent Automation Rule
    context: Dict with execution context (e.g., loop variables)

Returns a result summary string or None.
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime


def resolve_template(value, doc, context=None):
	"""Render a Jinja template string with doc context.

	Args:
		value: Template string (may contain {{ doc.field }}).
		doc: The document object.
		context: Extra context dict.

	Returns:
		Rendered string, or original value if no templates found.
	"""
	if not value:
		return value

	ctx = {"doc": doc, "frappe": frappe, "now": now_datetime()}
	if context:
		ctx.update(context)

	if "{" in str(value) and "}" in str(value):
		return frappe.render_template(str(value), ctx)

	return value


def parse_field_updates(json_str, doc, context=None):
	"""Parse a JSON field updates string into a dict.

	Args:
		json_str: JSON array like [{"fieldname": "x", "value": "y"}].
		doc: The document for template resolution.
		context: Extra context.

	Returns:
		Dict of {fieldname: resolved_value}.
	"""
	if not json_str:
		return {}

	try:
		updates = json.loads(json_str)
	except json.JSONDecodeError:
		frappe.log_error(title="Automation: Invalid JSON", message=json_str)
		return {}

	result = {}
	for item in updates:
		fieldname = item.get("fieldname")
		value = item.get("value")
		if fieldname:
			result[fieldname] = resolve_template(value, doc, context)

	return result


def execute_update_current_record(step, doc, rule, context=None):
	"""Update fields on the triggering document."""
	updates = parse_field_updates(step.field_updates_json, doc, context)
	if not updates:
		return "No updates specified"

	frappe.db.set_value(doc.doctype, doc.name, updates, update_modified=True)
	return f"Updated {len(updates)} field(s) on {doc.doctype} {doc.name}"


def execute_update_linked_record(step, doc, rule, context=None):
	"""Update fields on a linked document."""
	updates = parse_field_updates(step.field_updates_json, doc, context)
	target_dt = step.target_doctype
	if not updates or not target_dt:
		return "Missing target doctype or updates"

	link_field = step.link_field
	if link_field:
		target_name = doc.get(link_field)
	else:
		target_name = doc.name

	if not target_name:
		return f"No linked document found via field '{link_field}'"

	frappe.db.set_value(target_dt, target_name, updates, update_modified=True)
	return f"Updated {target_dt} {target_name}"


def execute_create_record(step, doc, rule, context=None):
	"""Create a new document."""
	target_dt = step.target_doctype
	if not target_dt:
		return "No target document type specified"

	new_doc = frappe.new_doc(target_dt)
	values = parse_field_updates(step.create_values_json, doc, context)

	for fieldname, value in values.items():
		new_doc.set(fieldname, value)

	link_field = step.link_field
	if link_field:
		new_doc.set(link_field, doc.name)

	new_doc.insert(ignore_permissions=True)
	return f"Created {target_dt} {new_doc.name}"


def execute_create_child_row(step, doc, rule, context=None):
	"""Add a child row to the current document's child table."""
	parent_field = step.parent_doctype_field
	if not parent_field:
		return "No parent table field specified"

	values = parse_field_updates(step.create_values_json, doc, context)
	# Reload to avoid timestamp mismatch if a prior step modified the doc
	doc.reload()
	row = doc.append(parent_field, values)
	doc.save(ignore_permissions=True)
	return f"Added child row to {parent_field} (idx {row.idx})"


def execute_create_todo(step, doc, rule, context=None):
	"""Create a ToDo linked to the document."""
	description = resolve_template(step.todo_description, doc, context) or ""

	allocated_to = step.assign_to_user
	if not allocated_to and step.assign_to_field:
		allocated_to = doc.get(step.assign_to_field)
	if not allocated_to:
		allocated_to = doc.owner

	todo = frappe.get_doc({
		"doctype": "ToDo",
		"description": description,
		"reference_type": doc.doctype,
		"reference_name": doc.name,
		"allocated_to": allocated_to,
		"assigned_by": frappe.session.user,
		"status": "Open",
	})
	todo.insert(ignore_permissions=True)
	return f"Created ToDo {todo.name} assigned to {allocated_to}"


def execute_create_activity(step, doc, rule, context=None):
	"""Create an Activity Log entry."""
	text = resolve_template(step.comment_text, doc, context) or ""

	activity = frappe.get_doc({
		"doctype": "Activity Log",
		"subject": text[:140],
		"content": text,
		"reference_doctype": doc.doctype,
		"reference_name": doc.name,
		"user": frappe.session.user,
	})
	activity.insert(ignore_permissions=True)
	return f"Created Activity Log {activity.name}"


def execute_add_comment(step, doc, rule, context=None):
	"""Add a comment to the document."""
	text = resolve_template(step.comment_text, doc, context) or ""
	doc.add_comment("Comment", text)
	return f"Added comment to {doc.doctype} {doc.name}"


def execute_send_email(step, doc, rule, context=None):
	"""Send an email using template or inline message."""
	recipient = _get_recipient(step, doc, context)
	if not recipient:
		return "No recipient found"

	if step.email_template:
		template = frappe.get_doc("Email Template", step.email_template)
		subject = frappe.render_template(template.subject, {"doc": doc})
		message = frappe.render_template(
			template.get("response_html") or template.response, {"doc": doc}
		)
	else:
		subject = resolve_template(step.subject, doc, context) or f"Notification: {doc.doctype} {doc.name}"
		message = resolve_template(step.message_template, doc, context) or ""

	frappe.sendmail(
		recipients=recipient if isinstance(recipient, list) else [recipient],
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		now=False,
	)
	return f"Email sent to {recipient}"


def execute_send_whatsapp(step, doc, rule, context=None):
	"""Send a WhatsApp message (requires WhatsApp integration)."""
	recipient = _get_recipient(step, doc, context)
	message = resolve_template(step.message_template, doc, context) or ""

	if not recipient:
		return "No recipient found for WhatsApp"

	try:
		frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "WhatsApp",
			"sent_or_received": "Sent",
			"content": message,
			"subject": resolve_template(step.subject, doc, context) or doc.name,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"phone_no": recipient,
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Automation: WhatsApp send error", message=frappe.get_traceback())
		return f"WhatsApp send failed for {recipient}"

	return f"WhatsApp message queued for {recipient}"


def execute_send_notification(step, doc, rule, context=None):
	"""Send an in-app notification."""
	recipient = _get_recipient(step, doc, context)
	if not recipient:
		return "No recipient found for notification"

	subject = resolve_template(step.subject, doc, context) or f"Notification: {doc.name}"
	message = resolve_template(step.message_template, doc, context) or ""

	notification = frappe.get_doc({
		"doctype": "Notification Log",
		"subject": subject,
		"email_content": message,
		"for_user": recipient,
		"type": "Alert",
		"document_type": doc.doctype,
		"document_name": doc.name,
	})
	notification.insert(ignore_permissions=True)
	return f"Notification sent to {recipient}"


def execute_assign_user(step, doc, rule, context=None):
	"""Assign a user to the document."""
	user = step.assign_to_user
	if not user and step.assign_to_field:
		user = doc.get(step.assign_to_field)
	if not user:
		return "No user to assign"

	from frappe.desk.form.assign_to import add as assign_add

	assign_add({
		"assign_to": [user],
		"doctype": doc.doctype,
		"name": doc.name,
		"description": resolve_template(step.todo_description, doc, context) or "",
	})
	return f"Assigned {user} to {doc.doctype} {doc.name}"


def execute_add_tag(step, doc, rule, context=None):
	"""Add a tag to the document."""
	tag = resolve_template(step.tag_value, doc, context)
	if not tag:
		return "No tag specified"

	doc.add_tag(tag)
	return f"Tag '{tag}' added to {doc.doctype} {doc.name}"


def execute_remove_tag(step, doc, rule, context=None):
	"""Remove a tag from the document."""
	tag = resolve_template(step.tag_value, doc, context)
	if not tag:
		return "No tag specified"

	frappe.db.delete("Tag Link", {
		"document_type": doc.doctype,
		"document_name": doc.name,
		"tag": tag,
	})
	return f"Tag '{tag}' removed from {doc.doctype} {doc.name}"


def execute_change_workflow_state(step, doc, rule, context=None):
	"""Change the workflow state of the document."""
	state = resolve_template(step.workflow_state, doc, context)
	if not state:
		return "No workflow state specified"

	frappe.db.set_value(doc.doctype, doc.name, "workflow_state", state, update_modified=True)
	return f"Workflow state changed to '{state}' on {doc.doctype} {doc.name}"


def execute_call_webhook(step, doc, rule, context=None):
	"""Call an external webhook URL."""
	import requests

	url = resolve_template(step.webhook_url, doc, context)
	if not url:
		return "No webhook URL specified"

	method = (step.webhook_method or "POST").upper()
	headers = {}
	body = None

	if step.webhook_headers_json:
		try:
			headers = json.loads(resolve_template(step.webhook_headers_json, doc, context))
		except json.JSONDecodeError:
			pass

	if step.webhook_body_json:
		body_str = resolve_template(step.webhook_body_json, doc, context)
		try:
			body = json.loads(body_str)
		except json.JSONDecodeError:
			body = body_str

	if step.webhook_auth_type and step.webhook_auth_type != "None":
		creds = step.get_password("webhook_auth_credentials") if step.webhook_auth_credentials else ""
		if step.webhook_auth_type == "Bearer Token":
			headers["Authorization"] = f"Bearer {creds}"
		elif step.webhook_auth_type == "API Key":
			headers["X-API-Key"] = creds
		elif step.webhook_auth_type == "Basic Auth":
			import base64
			headers["Authorization"] = f"Basic {base64.b64encode(creds.encode()).decode()}"

	if not headers.get("Content-Type") and method in ("POST", "PUT", "PATCH"):
		headers["Content-Type"] = "application/json"

	response = requests.request(
		method,
		url,
		headers=headers,
		json=body if isinstance(body, dict) else None,
		data=body if not isinstance(body, dict) else None,
		timeout=30,
	)

	return f"Webhook {method} {url} → {response.status_code}"


def execute_trigger_another_automation(step, doc, rule, context=None):
	"""Trigger another Automation Rule for the same document."""
	target_rule_name = step.target_automation_rule
	if not target_rule_name:
		return "No target automation rule specified"

	from automated_actions.engine import run_automation_rule

	target_rule = frappe.get_doc("Automation Rule", target_rule_name)
	run_automation_rule(target_rule, doc, trigger_context={"triggered_by": rule.name})
	return f"Triggered automation '{target_rule_name}'"


def execute_server_script(step, doc, rule, context=None):
	"""Execute custom Python code in a sandboxed environment."""
	code = step.python_code
	if not code:
		return "No Python code provided"

	exec_globals = {
		"frappe": frappe,
		"doc": doc,
		"rule": rule,
		"step": step,
		"context": context or {},
		"now_datetime": now_datetime,
		"_": _,
		"json": json,
	}

	from frappe.utils.safe_exec import safe_exec

	safe_exec(code, _globals=exec_globals, _locals={"doc": doc})
	return "Python code executed"


def execute_jinja_expression(step, doc, rule, context=None):
	"""Render a Jinja template and return the result."""
	template = step.jinja_template
	if not template:
		return "No Jinja template provided"

	result = frappe.render_template(template, {
		"doc": doc, "frappe": frappe, "rule": rule, "context": context or {},
	})
	return f"Jinja rendered: {result[:200]}"


def execute_custom_python_handler(step, doc, rule, context=None):
	"""Same as server script but labeled for power users."""
	return execute_server_script(step, doc, rule, context)


def execute_external_api_call(step, doc, rule, context=None):
	"""External API call with auth — delegates to webhook executor."""
	return execute_call_webhook(step, doc, rule, context)


def execute_queue_background_job(step, doc, rule, context=None):
	"""Queue a background job to run the remaining steps."""
	from automated_actions.engine import _run_steps_async

	remaining_steps = []
	found = False
	for s in rule.action_steps:
		if s.name == step.name:
			found = True
			continue
		if found:
			remaining_steps.append(s.name)

	if remaining_steps:
		frappe.enqueue(
			_run_steps_async,
			rule_name=rule.name,
			doc_doctype=doc.doctype,
			doc_name=doc.name,
			step_names=remaining_steps,
			queue="default",
		)

	return f"Queued {len(remaining_steps)} remaining step(s) as background job"


def execute_branch(step, doc, rule, context=None):
	"""Evaluate a branch condition and return the goto step index.

	The engine uses the returned goto info to jump to the correct step.
	"""
	condition = step.branch_condition
	if not condition:
		return "No branch condition"

	result = resolve_template(condition, doc, context)
	result_str = str(result).strip().lower()
	is_true = result_str not in ("", "0", "false", "none", "null", "no")

	if is_true:
		goto = step.on_true_goto or 0
		return f"Branch: True → goto step {goto}"
	else:
		goto = step.on_false_goto or 0
		return f"Branch: False → goto step {goto}"


def execute_wait_delay(step, doc, rule, context=None):
	"""Schedule remaining steps after a delay."""
	duration = step.wait_duration or 0
	duration_type = (step.wait_duration_type or "Seconds").lower()

	multipliers = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
	total_seconds = duration * multipliers.get(duration_type, 1)

	from automated_actions.engine import _run_steps_async

	remaining_steps = []
	found = False
	for s in rule.action_steps:
		if s.name == step.name:
			found = True
			continue
		if found:
			remaining_steps.append(s.name)

	if remaining_steps and total_seconds > 0:
		from frappe.utils import add_to_date

		execute_at = add_to_date(now_datetime(), seconds=total_seconds)
		frappe.enqueue(
			_run_steps_async,
			rule_name=rule.name,
			doc_doctype=doc.doctype,
			doc_name=doc.name,
			step_names=remaining_steps,
			queue="default",
			enqueue_after_commit=True,
			at_front=False,
			job_id=f"automation_wait_{rule.name}_{doc.name}_{step.idx}",
		)

	return f"Wait {duration} {duration_type} then continue ({len(remaining_steps)} steps remaining)"


def execute_loop_through_child_rows(step, doc, rule, context=None):
	"""Iterate over a child table and apply an action config to each row."""
	child_table = step.loop_child_table
	if not child_table:
		return "No child table specified"

	rows = doc.get(child_table) or []
	if not rows:
		return f"No rows in {child_table}"

	action_config = {}
	if step.loop_action_json:
		try:
			action_config = json.loads(step.loop_action_json)
		except json.JSONDecodeError:
			return "Invalid loop action JSON"

	processed = 0
	for row in rows:
		loop_context = {**(context or {}), "row": row, "row_idx": row.idx}

		if action_config.get("field_updates"):
			updates = {}
			for fu in action_config["field_updates"]:
				fieldname = fu.get("fieldname")
				value = resolve_template(fu.get("value"), doc, loop_context)
				if fieldname:
					updates[fieldname] = value

			if updates and action_config.get("target") == "child":
				for key, val in updates.items():
					row.set(key, val)
			elif updates and action_config.get("target_doctype"):
				target_name = row.get(action_config.get("link_field", "name"))
				if target_name:
					frappe.db.set_value(
						action_config["target_doctype"], target_name, updates, update_modified=True
					)
		processed += 1

	if action_config.get("target") == "child":
		doc.save(ignore_permissions=True)

	return f"Processed {processed} child rows in {child_table}"


def execute_aggregate_and_decide(step, doc, rule, context=None):
	"""Aggregate values from child tables and store result in context."""
	config = {}
	if step.loop_action_json:
		try:
			config = json.loads(step.loop_action_json)
		except json.JSONDecodeError:
			return "Invalid aggregation config JSON"

	child_table = step.loop_child_table or config.get("child_table")
	if not child_table:
		return "No child table for aggregation"

	rows = doc.get(child_table) or []
	agg_field = config.get("field")
	agg_fn = config.get("function", "sum")

	if not agg_field:
		return "No aggregation field specified"

	values = [row.get(agg_field) or 0 for row in rows]

	if agg_fn == "sum":
		result = sum(values)
	elif agg_fn == "count":
		result = len(values)
	elif agg_fn == "avg":
		result = sum(values) / len(values) if values else 0
	elif agg_fn == "min":
		result = min(values) if values else 0
	elif agg_fn == "max":
		result = max(values) if values else 0
	else:
		result = sum(values)

	target_field = config.get("target_field")
	if target_field:
		frappe.db.set_value(doc.doctype, doc.name, target_field, result, update_modified=True)

	return f"Aggregation ({agg_fn}) of {agg_field}: {result}"


ACTION_REGISTRY = {
	"Update Current Record": execute_update_current_record,
	"Update Linked Record": execute_update_linked_record,
	"Create Record": execute_create_record,
	"Create Child Row": execute_create_child_row,
	"Create ToDo": execute_create_todo,
	"Create Activity": execute_create_activity,
	"Add Comment": execute_add_comment,
	"Send Email": execute_send_email,
	"Send WhatsApp": execute_send_whatsapp,
	"Send Notification": execute_send_notification,
	"Assign User": execute_assign_user,
	"Add Tag": execute_add_tag,
	"Remove Tag": execute_remove_tag,
	"Change Workflow State": execute_change_workflow_state,
	"Call Webhook": execute_call_webhook,
	"Trigger Another Automation": execute_trigger_another_automation,
	"Execute Server Script": execute_server_script,
	"Execute Jinja Expression": execute_jinja_expression,
	"Custom Python Handler": execute_custom_python_handler,
	"External API Call": execute_external_api_call,
	"Queue Background Job": execute_queue_background_job,
	"Branch / If-Else": execute_branch,
	"Wait / Delay": execute_wait_delay,
	"Loop Through Child Rows": execute_loop_through_child_rows,
	"Aggregate and Decide": execute_aggregate_and_decide,
}


def execute_action_step(step, doc, rule, context=None):
	"""Dispatch to the correct action executor.

	Args:
		step: Automation Action Step child row.
		doc: The triggering document.
		rule: The parent Automation Rule.
		context: Extra execution context.

	Returns:
		Result summary string.

	Raises:
		ValueError: If the action type is unknown.
	"""
	action_fn = ACTION_REGISTRY.get(step.action_type)
	if not action_fn:
		raise ValueError(f"Unknown action type: {step.action_type}")
	return action_fn(step, doc, rule, context)


def _get_recipient(step, doc, context=None):
	"""Resolve the recipient from step configuration."""
	if step.send_to:
		return resolve_template(step.send_to, doc, context)
	if step.send_to_field:
		return doc.get(step.send_to_field)
	return doc.get("email_id") or doc.get("email") or doc.get("contact_email")
