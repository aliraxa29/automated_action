# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Core engine for evaluating and executing Automated Action rules.

This module handles:
- Fetching and caching active rules per DocType
- Evaluating before/after conditions
- Executing actions (update record, create record, python code, etc.)
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime


def get_rules_for_doctype(doctype: str, trigger: str | None = None) -> list[dict]:
	"""Fetch all enabled Automated Action rules for a given DocType.

	Rules are cached per-request for performance. The cache is invalidated
	when any Automated Action document is saved or deleted.

	Args:
		doctype: The DocType name to fetch rules for.
		trigger: Optional trigger type to filter by.

	Returns:
		List of rule dicts matching the criteria.
	"""
	all_rules = _get_cached_rules()
	rules = [r for r in all_rules if r.get("document_type") == doctype]
	if trigger:
		rules = [r for r in rules if r.get("trigger") == trigger]
	return rules


def _get_cached_rules() -> list[dict]:
	"""Return all enabled Automated Action rules, cached."""
	rules = frappe.cache.get_value("automated_action_rules")
	if rules is None:
		rules = frappe.get_all(
			"Automated Action",
			filters={"enabled": 1},
			fields=[
				"name",
				"action_name",
				"document_type",
				"trigger",
				"trigger_fields",
				"before_condition",
				"apply_on_condition",
				"action_type",
				"python_code",
				"email_template",
				"send_to_field",
				"target_document_type",
				"link_field",
				"todo_description",
				"assign_to_user",
				"assign_to_field",
				"comment_text",
				"trigger_date_field",
				"delay_count",
				"delay_type",
			],
		)
		frappe.cache.set_value("automated_action_rules", rules, expires_in_sec=300)
	return rules


def evaluate_before_condition(rule: dict, doc_before_save) -> bool:
	"""Check if the document BEFORE save matches the before_condition filters.

	Args:
		rule: The Automated Action rule dict.
		doc_before_save: The document object before the save (from get_doc_before_save()).

	Returns:
		True if conditions match or no before_condition is set.
	"""
	if not rule.get("before_condition"):
		return True

	if not doc_before_save:
		return True

	filters = json.loads(rule["before_condition"])
	return _match_filters(doc_before_save, filters)


def evaluate_apply_on_condition(rule: dict, doc) -> bool:
	"""Check if the document AFTER save matches the apply_on_condition filters.

	Args:
		rule: The Automated Action rule dict.
		doc: The document object after save.

	Returns:
		True if conditions match or no apply_on_condition is set.
	"""
	if not rule.get("apply_on_condition"):
		return True

	filters = json.loads(rule["apply_on_condition"])
	return _match_filters(doc, filters)


def check_trigger_fields(rule: dict, doc) -> bool:
	"""Check if any of the specified trigger fields were changed.

	Args:
		rule: The Automated Action rule dict.
		doc: The document object (must have _doc_before_save available).

	Returns:
		True if trigger_fields is empty (any change triggers) or
		if any of the specified fields changed.
	"""
	if not rule.get("trigger_fields"):
		return True

	trigger_fields = [f.strip() for f in rule["trigger_fields"].split(",") if f.strip()]
	if not trigger_fields:
		return True

	doc_before = doc.get_doc_before_save()
	if not doc_before:
		return True

	for field in trigger_fields:
		old_val = doc_before.get(field)
		new_val = doc.get(field)
		if old_val != new_val:
			return True

	return False


def execute_action(rule: dict, doc) -> None:
	"""Execute the action defined in the rule against the given document.

	Args:
		rule: The Automated Action rule dict.
		doc: The document that triggered the action.
	"""
	action_type = rule.get("action_type")

	try:
		if action_type == "Update Record":
			_execute_update_record(rule, doc)
		elif action_type == "Create Record":
			_execute_create_record(rule, doc)
		elif action_type == "Execute Python Code":
			_execute_python_code(rule, doc)
		elif action_type == "Send Email":
			_execute_send_email(rule, doc)
		elif action_type == "Create ToDo":
			_execute_create_todo(rule, doc)
		elif action_type == "Add Comment":
			_execute_add_comment(rule, doc)
		else:
			frappe.log_error(
				title="Automated Action: Unknown action type",
				message=f"Rule '{rule.get('name')}' has unknown action_type: {action_type}",
			)
			return

		_update_execution_log(rule["name"])

	except Exception:
		frappe.log_error(
			title=f"Automated Action Error: {rule.get('action_name', rule.get('name'))}",
			message=frappe.get_traceback(),
		)


def _execute_update_record(rule: dict, doc) -> None:
	"""Update fields on the triggering document."""
	field_updates = frappe.get_all(
		"Automated Action Field Update",
		filters={"parent": rule["name"], "parentfield": "field_updates"},
		fields=["fieldname", "value"],
		order_by="idx asc",
	)

	if not field_updates:
		return

	update_dict = {}
	for fu in field_updates:
		fieldname = fu.get("fieldname")
		value = fu.get("value")
		value = _resolve_value(value, doc)
		update_dict[fieldname] = value

	frappe.db.set_value(doc.doctype, doc.name, update_dict, update_modified=True)
	frappe.logger("automated_actions").info(
		f"Updated {doc.doctype} {doc.name}: {update_dict} (Rule: {rule['name']})"
	)


def _execute_create_record(rule: dict, doc) -> None:
	"""Create a new record in the target DocType."""
	target_dt = rule.get("target_document_type")
	if not target_dt:
		return

	new_doc = frappe.new_doc(target_dt)

	field_updates = frappe.get_all(
		"Automated Action Field Update",
		filters={"parent": rule["name"], "parentfield": "new_record_values"},
		fields=["fieldname", "value"],
		order_by="idx asc",
	)

	for fu in field_updates:
		value = _resolve_value(fu.get("value"), doc)
		new_doc.set(fu.get("fieldname"), value)

	link_field = rule.get("link_field")
	if link_field:
		new_doc.set(link_field, doc.name)

	new_doc.insert(ignore_permissions=True)
	frappe.logger("automated_actions").info(
		f"Created {target_dt} {new_doc.name} from {doc.doctype} {doc.name} (Rule: {rule['name']})"
	)


def _execute_python_code(rule: dict, doc) -> None:
	"""Execute custom Python code in a restricted context."""
	code = rule.get("python_code")
	if not code:
		return

	exec_globals = {
		"frappe": frappe,
		"doc": doc,
		"now_datetime": now_datetime,
		"_": _,
	}

	safe_builtins = {
		"True": True,
		"False": False,
		"None": None,
		"int": int,
		"float": float,
		"str": str,
		"bool": bool,
		"list": list,
		"dict": dict,
		"tuple": tuple,
		"set": set,
		"len": len,
		"range": range,
		"enumerate": enumerate,
		"zip": zip,
		"map": map,
		"filter": filter,
		"sorted": sorted,
		"min": min,
		"max": max,
		"sum": sum,
		"abs": abs,
		"round": round,
		"isinstance": isinstance,
		"getattr": getattr,
		"setattr": setattr,
		"hasattr": hasattr,
		"print": frappe.logger("automated_actions").info,
	}
	exec_globals["__builtins__"] = safe_builtins

	frappe.utils.safe_exec.safe_exec(code, _globals=exec_globals, _locals={"doc": doc})
	frappe.logger("automated_actions").info(
		f"Executed Python code for {doc.doctype} {doc.name} (Rule: {rule['name']})"
	)


def _execute_send_email(rule: dict, doc) -> None:
	"""Send an email using a template."""
	template_name = rule.get("email_template")
	if not template_name:
		return

	send_to_field = rule.get("send_to_field")
	recipient = doc.get(send_to_field) if send_to_field else doc.get("email_id") or doc.get("email")

	if not recipient:
		frappe.logger("automated_actions").warning(
			f"No recipient found for {doc.doctype} {doc.name} (Rule: {rule['name']})"
		)
		return

	template = frappe.get_doc("Email Template", template_name)
	subject = frappe.render_template(template.subject, {"doc": doc})
	message = frappe.render_template(template.get("response_html") or template.response, {"doc": doc})

	frappe.sendmail(
		recipients=[recipient],
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		now=False,
	)
	frappe.logger("automated_actions").info(
		f"Sent email to {recipient} for {doc.doctype} {doc.name} (Rule: {rule['name']})"
	)


def _execute_create_todo(rule: dict, doc) -> None:
	"""Create a ToDo and optionally assign it."""
	description = rule.get("todo_description", "")
	description = frappe.render_template(description, {"doc": doc})

	allocated_to = rule.get("assign_to_user")
	if not allocated_to:
		assign_field = rule.get("assign_to_field")
		if assign_field:
			allocated_to = doc.get(assign_field)
	if not allocated_to:
		allocated_to = doc.owner

	todo = frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": description,
			"reference_type": doc.doctype,
			"reference_name": doc.name,
			"allocated_to": allocated_to,
			"assigned_by": frappe.session.user,
			"status": "Open",
		}
	)
	todo.insert(ignore_permissions=True)
	frappe.logger("automated_actions").info(
		f"Created ToDo {todo.name} for {doc.doctype} {doc.name} (Rule: {rule['name']})"
	)


def _execute_add_comment(rule: dict, doc) -> None:
	"""Add a comment to the document."""
	comment_text = rule.get("comment_text", "")
	comment_text = frappe.render_template(comment_text, {"doc": doc})

	doc.add_comment("Comment", comment_text)
	frappe.logger("automated_actions").info(
		f"Added comment to {doc.doctype} {doc.name} (Rule: {rule['name']})"
	)


def _update_execution_log(rule_name: str) -> None:
	"""Update last_run and run_count on the Automated Action."""
	frappe.db.set_value(
		"Automated Action",
		rule_name,
		{"last_run": now_datetime(), "run_count": ("run_count", "+", 1)},
		update_modified=False,
	)


def _resolve_value(value: str | None, doc) -> str | None:
	"""Resolve template expressions in a field value.

	Supports:
	- {fieldname} → doc.fieldname
	- {today} → today's date
	- {now} → current datetime
	- Static values (returned as-is)
	"""
	if not value:
		return value

	if "{" in value and "}" in value:
		return frappe.render_template(value, {"doc": doc, "frappe": frappe})

	return value


def _match_filters(doc, filters: list) -> bool:
	"""Check if a document matches a set of Frappe-style filters.

	Supports operators: =, !=, >, <, >=, <=, like, not like, in, not in,
	is (set/not set).

	Args:
		doc: The document object to check.
		filters: List of filter conditions, each [fieldname, operator, value]
			or [fieldname, value] (defaults to =).

	Returns:
		True if ALL filters match.
	"""
	for condition in filters:
		if len(condition) == 2:
			fieldname, value = condition
			operator = "="
		elif len(condition) == 3:
			fieldname, operator, value = condition
		else:
			continue

		doc_value = doc.get(fieldname)
		operator = operator.lower().strip()

		if not _compare(doc_value, operator, value):
			return False

	return True


def _compare(doc_value, operator: str, filter_value) -> bool:
	"""Compare a document field value against a filter value using the given operator."""
	if operator == "=":
		return doc_value == filter_value
	elif operator == "!=":
		return doc_value != filter_value
	elif operator == ">":
		return doc_value is not None and doc_value > filter_value
	elif operator == "<":
		return doc_value is not None and doc_value < filter_value
	elif operator == ">=":
		return doc_value is not None and doc_value >= filter_value
	elif operator == "<=":
		return doc_value is not None and doc_value <= filter_value
	elif operator == "like":
		return _like_match(doc_value, filter_value)
	elif operator == "not like":
		return not _like_match(doc_value, filter_value)
	elif operator == "in":
		if isinstance(filter_value, str):
			filter_value = [v.strip() for v in filter_value.split(",")]
		return doc_value in filter_value
	elif operator == "not in":
		if isinstance(filter_value, str):
			filter_value = [v.strip() for v in filter_value.split(",")]
		return doc_value not in filter_value
	elif operator == "is":
		if filter_value == "set":
			return bool(doc_value)
		elif filter_value == "not set":
			return not doc_value
	return False


def _like_match(doc_value, pattern) -> bool:
	"""SQL-style LIKE match (% wildcards)."""
	if not doc_value or not pattern:
		return False

	import re

	doc_value = str(doc_value)
	regex = "^" + re.escape(str(pattern)).replace("%", ".*") + "$"
	return bool(re.match(regex, doc_value, re.IGNORECASE))


@frappe.whitelist()
def test_automated_action(action_name: str) -> str:
	"""Test an Automated Action by finding matching documents and reporting what would happen.

	Args:
		action_name: Name of the Automated Action to test.

	Returns:
		A message describing the test result.
	"""
	frappe.only_for("System Manager")

	rule = frappe.get_doc("Automated Action", action_name)
	if not rule.enabled:
		return _("This rule is disabled. Enable it first.")

	filters = {}
	if rule.apply_on_condition:
		try:
			raw_filters = json.loads(rule.apply_on_condition)
			for f in raw_filters:
				if len(f) == 3:
					filters[f[0]] = [f[1], f[2]]
				elif len(f) == 2:
					filters[f[0]] = f[1]
		except (json.JSONDecodeError, IndexError):
			return _("Error: Invalid Apply On Condition JSON")

	try:
		matching_docs = frappe.get_all(rule.document_type, filters=filters, limit=5, pluck="name")
	except Exception:
		return _("Error: Could not query documents - {0}").format(frappe.get_traceback(with_context=False))

	if not matching_docs:
		return _("No documents currently match the Apply On condition.")

	return _("Test passed. {0} document(s) match the conditions: {1}").format(
		len(matching_docs), ", ".join(matching_docs)
	)
