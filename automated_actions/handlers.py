# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Document event handlers for Automated Actions.

These hooks are registered via hooks.py on all DocTypes ("*")
and dispatch to matching Automated Action rules.
"""

import frappe

from automated_actions.core import (
	check_trigger_fields,
	evaluate_apply_on_condition,
	evaluate_before_condition,
	execute_action,
	get_rules_for_doctype,
)

# Flag to prevent infinite recursion when an action updates a document
_PROCESSING_FLAG = "_automated_action_processing"


def handle_after_insert(doc, method=None):
	"""Triggered after a new document is inserted (On Create / On Create & Update)."""
	if getattr(doc.flags, _PROCESSING_FLAG, False):
		return

	rules = get_rules_for_doctype(doc.doctype)
	rules = [r for r in rules if r["trigger"] in ("On Create", "On Create & Update")]

	if not rules:
		return

	for rule in rules:
		try:
			if not evaluate_apply_on_condition(rule, doc):
				continue

			doc.flags[_PROCESSING_FLAG] = True
			execute_action(rule, doc)
		except Exception:
			frappe.log_error(
				title=f"Automated Action Error: {rule.get('action_name', rule.get('name'))}",
				message=frappe.get_traceback(),
			)
		finally:
			doc.flags[_PROCESSING_FLAG] = False


def handle_on_update(doc, method=None):
	"""Triggered when an existing document is updated (On Update / On Create & Update)."""
	if getattr(doc.flags, _PROCESSING_FLAG, False):
		return

	# Skip if this is a new document (handled by after_insert)
	if doc.flags.in_insert:
		return

	rules = get_rules_for_doctype(doc.doctype)
	rules = [r for r in rules if r["trigger"] in ("On Update", "On Create & Update")]

	if not rules:
		return

	doc_before_save = doc.get_doc_before_save()

	for rule in rules:
		try:
			# Check trigger fields first (cheapest check)
			if not check_trigger_fields(rule, doc):
				continue

			# Check before condition against old values
			if not evaluate_before_condition(rule, doc_before_save):
				continue

			# Check apply_on condition against new values
			if not evaluate_apply_on_condition(rule, doc):
				continue

			doc.flags[_PROCESSING_FLAG] = True
			execute_action(rule, doc)
		except Exception:
			frappe.log_error(
				title=f"Automated Action Error: {rule.get('action_name', rule.get('name'))}",
				message=frappe.get_traceback(),
			)
		finally:
			doc.flags[_PROCESSING_FLAG] = False


def handle_on_trash(doc, method=None):
	"""Triggered when a document is deleted (On Delete)."""
	if getattr(doc.flags, _PROCESSING_FLAG, False):
		return

	rules = get_rules_for_doctype(doc.doctype, trigger="On Delete")
	if not rules:
		return

	for rule in rules:
		try:
			if not evaluate_apply_on_condition(rule, doc):
				continue

			doc.flags[_PROCESSING_FLAG] = True
			execute_action(rule, doc)
		except Exception:
			frappe.log_error(
				title=f"Automated Action Error: {rule.get('action_name', rule.get('name'))}",
				message=frappe.get_traceback(),
			)
		finally:
			doc.flags[_PROCESSING_FLAG] = False
