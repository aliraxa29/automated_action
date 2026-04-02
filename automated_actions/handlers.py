# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Document event handlers for the Automation Engine.

All triggers go through the unified engine for Automation Rules.
"""

import frappe
from automated_actions.conditions import (
	check_field_value_change,
	check_trigger_fields,
	evaluate_conditions,
)
from automated_actions.engine import get_rules_for_doctype, run_automation_rule

_PROCESSING_FLAG = "_automation_processing"
_MAX_RECURSION_DEPTH = 5


def handle_after_insert(doc, method=None):
	"""Triggered after a new document is inserted."""
	if _is_blocked(doc):
		return

	try:
		rules = get_rules_for_doctype(doc.doctype, trigger_type=["On Create", "On Create & Update"])
		for rule_dict in rules:
			_run_rule_safe(rule_dict, doc)
	except Exception:
		pass


def handle_on_update(doc, method=None):
	"""Triggered when an existing document is updated."""
	if _is_blocked(doc):
		return

	if doc.flags.in_insert:
		return

	try:
		update_rules = get_rules_for_doctype(
			doc.doctype, trigger_type=["On Update", "On Create & Update"]
		)
		for rule_dict in update_rules:
			if not check_trigger_fields(rule_dict, doc):
				continue
			_run_rule_safe(rule_dict, doc)

		fvc_rules = get_rules_for_doctype(doc.doctype, trigger_type="Field Value Change")
		for rule_dict in fvc_rules:
			if not check_field_value_change(rule_dict, doc):
				continue
			_run_rule_safe(rule_dict, doc)
	except Exception:
		pass


def handle_on_trash(doc, method=None):
	"""Triggered when a document is deleted."""
	if _is_blocked(doc):
		return

	try:
		rules = get_rules_for_doctype(doc.doctype, trigger_type="On Delete")
		for rule_dict in rules:
			_run_rule_safe(rule_dict, doc)
	except Exception:
		pass


def handle_on_update_after_submit(doc, method=None):
	"""Triggered when a submitted document is amended."""
	if _is_blocked(doc):
		return

	try:
		update_rules = get_rules_for_doctype(
			doc.doctype, trigger_type=["On Update", "On Create & Update"]
		)
		for rule_dict in update_rules:
			if not check_trigger_fields(rule_dict, doc):
				continue
			_run_rule_safe(rule_dict, doc)
	except Exception:
		pass


def _run_rule_safe(rule_dict, doc):
	"""Load and execute an Automation Rule with error handling and recursion protection."""
	rule_name = rule_dict.get("name")

	try:
		rule = frappe.get_doc("Automation Rule", rule_name)

		if rule.recursion_protection and _is_blocked(doc):
			return

		if rule.company and doc.get("company") and doc.company != rule.company:
			return

		doc_before_save = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
		if not evaluate_conditions(rule, doc, doc_before_save):
			return

		doc.flags[_PROCESSING_FLAG] = True
		_increment_depth(doc)

		try:
			if rule.run_mode == "Asynchronous":
				frappe.enqueue(
					run_automation_rule,
					rule=rule.name,
					doc=doc.as_dict(),
					queue="default",
					enqueue_after_commit=True,
				)
			else:
				run_automation_rule(rule, doc)
		finally:
			doc.flags[_PROCESSING_FLAG] = False

	except Exception:
		frappe.log_error(
			title=f"Automation Rule Error: {rule_dict.get('rule_name', rule_name)}",
			message=frappe.get_traceback(),
		)


def _is_blocked(doc):
	"""Check if the document is currently being processed by an automation."""
	if getattr(doc.flags, _PROCESSING_FLAG, False):
		return True
	depth = getattr(doc.flags, "_automation_depth", 0) or 0
	if depth >= _MAX_RECURSION_DEPTH:
		frappe.log_error(
			title="Automation Rule: Max recursion depth",
			message=f"Recursion depth {depth} reached for {doc.doctype} {doc.name}",
		)
		return True
	return False


def _increment_depth(doc):
	"""Increment the automation recursion depth counter."""
	current = getattr(doc.flags, "_automation_depth", 0)
	doc.flags._automation_depth = current + 1
