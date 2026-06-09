# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Core Execution Engine for Automation Rules.

Orchestrates:
- Rule caching and lookup
- Condition evaluation
- Multi-step action flow execution with logging
- Branch/jump control flow
- Async execution support
"""

import frappe
from frappe.utils import now_datetime


def get_rules_for_doctype(doctype, trigger_type=None):
	"""Fetch all enabled Automation Rules for a given DocType.

	Args:
		doctype: The DocType name.
		trigger_type: Optional trigger type to filter by.

	Returns:
		List of Automation Rule names matching criteria, ordered by priority DESC.
	"""
	all_rules = _get_cached_rules()
	rules = [r for r in all_rules if r.get("document_type") == doctype and r.get("enabled")]

	if trigger_type:
		if isinstance(trigger_type, list | tuple):
			rules = [r for r in rules if r.get("trigger_type") in trigger_type]
		else:
			rules = [r for r in rules if r.get("trigger_type") == trigger_type]

	rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
	return rules


def _get_cached_rules():
	"""Return all enabled Automation Rules (lightweight), cached."""
	rules = frappe.cache.get_value("automation_rules")
	if rules is None:
		try:
			rules = frappe.get_all(
				"Automation Rule",
				filters={"enabled": 1},
				fields=[
					"name",
					"rule_name",
					"document_type",
					"trigger_type",
					"trigger_fields",
					"field_from_value",
					"field_to_value",
					"enabled",
					"priority",
					"run_mode",
					"stop_on_error",
					"allow_repeated_execution",
					"recursion_protection",
					"trigger_date_field",
					"delay_count",
					"delay_type",
					"cron_expression",
					"child_doctype",
					"linked_doctype",
					"linked_field",
					"linked_status_field",
					"condition_logic",
					"custom_condition",
					"last_scheduled_run",
				],
				order_by="priority desc",
			)
		except Exception:
			rules = []
		frappe.cache.set_value("automation_rules", rules, expires_in_sec=300)
	return rules


def run_automation_rule(rule, doc, trigger_context=None):
	"""Execute an Automation Rule against a document.

	This is the main entry point. It:
	1. Creates an execution log
	2. Evaluates conditions
	3. Executes action steps in order (with branch/jump support)
	4. Handles errors and updates the log

	Args:
		rule: Automation Rule document (or name string).
		doc: The triggering document.
		trigger_context: Optional dict with extra context (e.g., triggered_by).
	"""
	if isinstance(rule, str):
		rule = frappe.get_doc("Automation Rule", rule)

	log = _create_log(rule, doc)
	start_time = now_datetime()
	context = dict(trigger_context or {})
	steps = [s for s in rule.action_steps if s.enabled]

	try:
		step_idx = 0
		while step_idx < len(steps):
			step = steps[step_idx]
			step_result = _execute_single_step(step, doc, rule, log, context)

			if step.action_type == "Branch / If-Else" and step_result:
				goto = _parse_branch_goto(step_result, step)
				if goto and goto > 0:
					target_idx = _find_step_index(steps, goto)
					if target_idx is not None:
						step_idx = target_idx
						continue

			if step.action_type in ("Wait / Delay", "Queue Background Job"):
				break

			step_idx += 1

		any_failed = any(s.status == "Failed" for s in log.steps)
		any_success = any(s.status == "Success" for s in log.steps)

		if any_failed and any_success:
			log.status = "Partial"
		elif any_failed:
			log.status = "Failed"
		else:
			log.status = "Success"

	except Exception:
		log.status = "Failed"
		log.error_message = frappe.get_traceback()
		frappe.log_error(
			title=f"Automation Rule Error: {rule.rule_name}",
			message=frappe.get_traceback(),
		)

	finally:
		end_time = now_datetime()
		log.completed_at = end_time
		log.duration_ms = (end_time - start_time).total_seconds() * 1000
		log.save(ignore_permissions=True)
		frappe.db.commit()

		_update_rule_stats(rule.name, log.status)


def _execute_single_step(step, doc, rule, log, context):
	"""Execute a single action step with logging.

	Args:
		step: Automation Action Step row.
		doc: The document.
		rule: The Automation Rule.
		log: The Automation Log document.
		context: Execution context dict.

	Returns:
		Result summary string or None.
	"""
	from automated_actions.actions import execute_action_step, resolve_template

	step_start = now_datetime()

	if step.execute_if:
		condition_result = resolve_template(step.execute_if, doc, context)
		cond_str = str(condition_result).strip().lower()
		if cond_str in ("", "0", "false", "none", "null", "no"):
			_add_log_step(log, step, "Skipped", step_start, result="Condition not met")
			return None

	try:
		result = execute_action_step(step, doc, rule, context)
		_add_log_step(log, step, "Success", step_start, result=result)
		return result
	except Exception as e:
		error_msg = str(e)
		tb = frappe.get_traceback()
		_add_log_step(log, step, "Failed", step_start, error=f"{error_msg}\n{tb}")

		if rule.stop_on_error:
			raise

		return None


def _parse_branch_goto(result_str, step):
	"""Parse the branch result to determine jump target."""
	if not result_str:
		return None

	if "True" in result_str:
		return step.on_true_goto or 0
	elif "False" in result_str:
		return step.on_false_goto or 0

	return None


def _find_step_index(steps, target_idx):
	"""Find the list index of a step by its row idx number."""
	for i, s in enumerate(steps):
		if s.idx == target_idx:
			return i
	return None


def _create_log(rule, doc):
	"""Create an Automation Log entry."""
	log = frappe.new_doc("Automation Log")
	log.automation_rule = rule.name
	log.rule_name = rule.rule_name
	log.document_type = doc.doctype
	log.document_name = doc.name
	log.trigger_type = rule.trigger_type
	log.status = "Running"
	log.started_at = now_datetime()
	log.insert(ignore_permissions=True)
	return log


def _add_log_step(log, step, status, started_at, result=None, error=None):
	"""Add a step entry to the Automation Log."""
	log.append(
		"steps",
		{
			"step_name": step.step_name or step.action_type,
			"action_type": step.action_type,
			"status": status,
			"started_at": started_at,
			"completed_at": now_datetime(),
			"result_summary": result,
			"error_message": error,
		},
	)


def _update_rule_stats(rule_name, status):
	"""Update last_run, run_count, and last_error on the Automation Rule."""
	old_count = frappe.db.get_value("Automation Rule", rule_name, "run_count") or 0
	update = {
		"last_run": now_datetime(),
		"run_count": old_count + 1,
		"last_error": frappe.get_traceback() if status == "Failed" else "",
	}
	frappe.db.set_value("Automation Rule", rule_name, update, update_modified=False)


def _run_steps_async(rule_name, doc_doctype, doc_name, step_names):
	"""Execute specific steps of a rule asynchronously (called by enqueue).

	Args:
		rule_name: Name of the Automation Rule.
		doc_doctype: DocType of the document.
		doc_name: Name of the document.
		step_names: List of Automation Action Step names to execute.
	"""
	rule = frappe.get_doc("Automation Rule", rule_name)
	doc = frappe.get_doc(doc_doctype, doc_name)

	log = _create_log(rule, doc)
	context = {"async_continuation": True}

	try:
		for step in rule.action_steps:
			if step.name in step_names and step.enabled:
				_execute_single_step(step, doc, rule, log, context)

		any_failed = any(s.status == "Failed" for s in log.steps)
		any_success = any(s.status == "Success" for s in log.steps)

		if any_failed and any_success:
			log.status = "Partial"
		elif any_failed:
			log.status = "Failed"
		else:
			log.status = "Success"

	except Exception:
		log.status = "Failed"
		log.error_message = frappe.get_traceback()

	finally:
		log.completed_at = now_datetime()
		log.save(ignore_permissions=True)
		frappe.db.commit()

		_update_rule_stats(rule_name, log.status)


def _run_rule_async(rule_name, doc_doctype, doc_name):
	"""Re-fetch the rule and document then run the automation.

	This is the RQ job entrypoint for asynchronous rule execution.
	Accepts primitive types only so RQ serialisation is safe.

	Args:
		rule_name: Name of the Automation Rule.
		doc_doctype: DocType of the triggering document.
		doc_name: Name of the triggering document.
	"""
	rule = frappe.get_doc("Automation Rule", rule_name)
	doc = frappe.get_doc(doc_doctype, doc_name)
	run_automation_rule(rule, doc)


@frappe.whitelist()
def test_automation_rule(rule_name):
	"""Test an Automation Rule by simulating execution.

	Args:
		rule_name: Name of the Automation Rule to test.

	Returns:
		A message describing the test result.
	"""
	frappe.only_for("System Manager")

	rule = frappe.get_doc("Automation Rule", rule_name)
	if not rule.enabled:
		return frappe._("This rule is disabled. Enable it first.")

	from automated_actions.conditions import evaluate_conditions

	try:
		sample_docs = frappe.get_all(rule.document_type, limit=5, pluck="name")
	except Exception:
		return frappe._("Error querying documents: {0}").format(frappe.get_traceback(with_context=False))

	if not sample_docs:
		return frappe._("No documents found for DocType '{0}'").format(rule.document_type)

	matching = []
	for doc_name in sample_docs:
		doc = frappe.get_doc(rule.document_type, doc_name)
		if evaluate_conditions(rule, doc):
			matching.append(doc_name)

	if matching:
		return frappe._("Test passed. {0} of {1} sample document(s) match conditions: {2}").format(
			len(matching), len(sample_docs), ", ".join(matching)
		)
	else:
		return frappe._("No sample documents currently match the conditions.")
