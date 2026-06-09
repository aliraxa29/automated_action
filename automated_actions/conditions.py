# Copyright (c) 2026, Kodlyft and contributors
# For license information, please see license.txt

"""
Conditions Engine for Automation Rules.

Evaluates structured conditions (AND/OR) and custom Jinja expressions
against a document, optionally comparing with the document before save.
"""

import re

import frappe
from frappe.utils import cstr


def evaluate_conditions(rule, doc, doc_before_save=None):
	"""Evaluate all conditions on an Automation Rule against a document.

	Args:
		rule: Automation Rule document or dict with conditions, condition_logic,
			  custom_condition fields.
		doc: The current document object.
		doc_before_save: The document state before save (for 'changed' operators).

	Returns:
		True if conditions are met, False otherwise.
	"""
	conditions = rule.get("conditions") or []
	if not conditions and not rule.get("custom_condition"):
		return True

	structured_result = _evaluate_structured_conditions(
		conditions, rule.get("condition_logic", "All Match (AND)"), doc, doc_before_save
	)

	if not structured_result:
		return False

	if rule.get("custom_condition"):
		return _evaluate_custom_condition(rule.custom_condition, doc)

	return True


def check_trigger_fields(rule, doc):
	"""Check if any of the specified trigger fields were changed.

	Args:
		rule: The Automation Rule (must have trigger_fields).
		doc: The document object.

	Returns:
		True if trigger_fields is empty or if any specified field changed.
	"""
	trigger_fields_str = rule.get("trigger_fields")
	if not trigger_fields_str:
		return True

	trigger_fields = [f.strip() for f in trigger_fields_str.split(",") if f.strip()]
	if not trigger_fields:
		return True

	doc_before = doc.get_doc_before_save()
	if not doc_before:
		return True

	for field in trigger_fields:
		if doc_before.get(field) != doc.get(field):
			return True

	return False


def check_field_value_change(rule, doc):
	"""Check field value change trigger conditions (from X to Y).

	Args:
		rule: The Automation Rule with trigger_fields, field_from_value, field_to_value.
		doc: The document object.

	Returns:
		True if the field value change matches the rule.
	"""
	trigger_fields_str = rule.get("trigger_fields")
	if not trigger_fields_str:
		return False

	trigger_fields = [f.strip() for f in trigger_fields_str.split(",") if f.strip()]
	if not trigger_fields:
		return False

	doc_before = doc.get_doc_before_save()
	if not doc_before:
		return False

	from_value = rule.get("field_from_value")
	to_value = rule.get("field_to_value")

	for field in trigger_fields:
		old_val = cstr(doc_before.get(field))
		new_val = cstr(doc.get(field))

		if old_val == new_val:
			continue

		if from_value and old_val != from_value:
			continue

		if to_value and new_val != to_value:
			continue

		return True

	return False


def _evaluate_structured_conditions(conditions, logic, doc, doc_before_save):
	"""Evaluate structured condition rows with AND/OR logic.

	Args:
		conditions: List of Automation Condition child rows.
		logic: 'All Match (AND)' or 'Any Match (OR)'.
		doc: Current document.
		doc_before_save: Document before save.

	Returns:
		True if conditions are satisfied.
	"""
	if not conditions:
		return True

	use_and = logic == "All Match (AND)"

	for cond in conditions:
		result = _evaluate_single_condition(cond, doc, doc_before_save)

		if use_and and not result:
			return False
		if not use_and and result:
			return True

	return use_and


def _evaluate_single_condition(cond, doc, doc_before_save):
	"""Evaluate a single condition row against the document.

	Args:
		cond: An Automation Condition row.
		doc: Current document.
		doc_before_save: Document before save.

	Returns:
		True if condition matches.
	"""
	fieldname = cond.get("fieldname")
	operator = cond.get("operator")
	value = cond.get("value")
	value_type = cond.get("value_type", "Static Value")

	doc_value = doc.get(fieldname)

	resolved_value = _resolve_condition_value(value, value_type, doc)

	if operator == "changed":
		if not doc_before_save:
			return True
		return doc_before_save.get(fieldname) != doc_value

	if operator == "changed to":
		if not doc_before_save:
			return cstr(doc_value) == cstr(resolved_value)
		old_val = doc_before_save.get(fieldname)
		return old_val != doc_value and cstr(doc_value) == cstr(resolved_value)

	if operator == "changed from":
		if not doc_before_save:
			return False
		old_val = doc_before_save.get(fieldname)
		return old_val != doc_value and cstr(old_val) == cstr(resolved_value)

	if operator == "is set":
		return bool(doc_value)

	if operator == "is not set":
		return not doc_value

	return _compare(doc_value, operator, resolved_value)


def _resolve_condition_value(value, value_type, doc):
	"""Resolve a condition value based on its type.

	Args:
		value: The raw value string.
		value_type: 'Static Value', 'Document Field', or 'Jinja Expression'.
		doc: The document object.

	Returns:
		The resolved value.
	"""
	if not value:
		return value

	if value_type == "Document Field":
		return doc.get(value)

	if value_type == "Jinja Expression":
		return frappe.render_template(value, {"doc": doc, "frappe": frappe})

	return value


def _evaluate_custom_condition(condition_template, doc):
	"""Evaluate a custom Jinja condition expression.

	Args:
		condition_template: Jinja template string.
		doc: The document object.

	Returns:
		True if the rendered result is truthy.
	"""
	try:
		result = frappe.render_template(condition_template, {"doc": doc, "frappe": frappe})
		result = cstr(result).strip().lower()
		return result not in ("", "0", "false", "none", "null", "no")
	except Exception:
		frappe.log_error(
			title="Automation Rule: Custom condition error",
			message=frappe.get_traceback(),
		)
		return False


def _compare(doc_value, operator, filter_value):
	"""Compare a document field value against a filter value.

	Args:
		doc_value: The value from the document field.
		operator: Comparison operator string.
		filter_value: The value to compare against.

	Returns:
		True if comparison matches.
	"""
	operator = operator.lower().strip()

	if operator == "=":
		return cstr(doc_value) == cstr(filter_value)
	elif operator == "!=":
		return cstr(doc_value) != cstr(filter_value)
	elif operator == ">":
		return doc_value is not None and doc_value > _coerce_type(filter_value, doc_value)
	elif operator == "<":
		return doc_value is not None and doc_value < _coerce_type(filter_value, doc_value)
	elif operator == ">=":
		return doc_value is not None and doc_value >= _coerce_type(filter_value, doc_value)
	elif operator == "<=":
		return doc_value is not None and doc_value <= _coerce_type(filter_value, doc_value)
	elif operator == "like":
		return _like_match(doc_value, filter_value)
	elif operator == "not like":
		return not _like_match(doc_value, filter_value)
	elif operator == "in":
		values = _parse_in_values(filter_value)
		return cstr(doc_value) in values
	elif operator == "not in":
		values = _parse_in_values(filter_value)
		return cstr(doc_value) not in values

	return False


def _coerce_type(filter_value, reference_value):
	"""Coerce filter_value to the same type as reference_value for comparison."""
	try:
		if isinstance(reference_value, int):
			return int(filter_value)
		if isinstance(reference_value, float):
			return float(filter_value)
	except (ValueError, TypeError):
		pass
	return filter_value


def _parse_in_values(value):
	"""Parse a comma-separated or list value into a list of strings."""
	if isinstance(value, list | tuple):
		return [cstr(v).strip() for v in value]
	return [v.strip() for v in cstr(value).split(",")]


def _like_match(doc_value, pattern):
	"""SQL-style LIKE match with % wildcards."""
	if not doc_value or not pattern:
		return False
	doc_value = cstr(doc_value)
	regex = "^" + re.escape(cstr(pattern)).replace("%", ".*") + "$"
	return bool(re.match(regex, doc_value, re.IGNORECASE))
