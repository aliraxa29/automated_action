# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Scheduler for time-based Automated Action triggers.

Runs periodically to check documents with date/datetime fields
that match the configured delay from now.
"""

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from automated_actions.core import evaluate_apply_on_condition, execute_action


def process_time_based_rules():
	"""Process all 'Based on Time Condition' automated actions.

	Called by the scheduler (default: every 4 hours via cron_hourly,
	but can be configured to run more frequently).
	"""
	rules = frappe.get_all(
		"Automated Action",
		filters={"enabled": 1, "trigger": "Based on Time Condition"},
		fields=[
			"name",
			"action_name",
			"document_type",
			"trigger",
			"trigger_date_field",
			"delay_count",
			"delay_type",
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
			"last_scheduled_run",
		],
	)

	for rule in rules:
		try:
			_process_single_time_rule(rule)
		except Exception:
			frappe.log_error(
				title=f"Automated Action Scheduler Error: {rule.get('action_name', rule.get('name'))}",
				message=frappe.get_traceback(),
			)


def _process_single_time_rule(rule: dict) -> None:
	"""Process a single time-based rule: find matching documents and execute actions."""
	date_field = rule.get("trigger_date_field")
	if not date_field:
		return

	delay_count = rule.get("delay_count", 0)
	delay_type = (rule.get("delay_type") or "Hours").lower()

	now = now_datetime()
	last_run = get_datetime(rule.get("last_scheduled_run")) if rule.get("last_scheduled_run") else None

	target_date = add_to_date(now, **{delay_type: -delay_count})

	filters = {date_field: ["<=", target_date]}

	if last_run:
		last_target_date = add_to_date(last_run, **{delay_type: -delay_count})
		filters[date_field] = ["between", [last_target_date, target_date]]

	if rule.get("apply_on_condition"):
		import json

		try:
			extra_filters = json.loads(rule["apply_on_condition"])
			for f in extra_filters:
				if len(f) == 3:
					filters[f[0]] = [f[1], f[2]]
				elif len(f) == 2:
					filters[f[0]] = f[1]
		except (json.JSONDecodeError, IndexError):
			frappe.log_error(
				title="Automated Action: Invalid condition JSON",
				message=f"Rule: {rule['name']}, condition: {rule['apply_on_condition']}",
			)
			return

	try:
		docs = frappe.get_all(
			rule["document_type"],
			filters=filters,
			pluck="name",
			limit=500,
		)
	except Exception:
		frappe.log_error(
			title="Automated Action: Query error",
			message=frappe.get_traceback(),
		)
		return

	for doc_name in docs:
		try:
			doc = frappe.get_doc(rule["document_type"], doc_name)
			if evaluate_apply_on_condition(rule, doc):
				execute_action(rule, doc)
		except Exception:
			frappe.log_error(
				title=f"Automated Action Error: {rule.get('action_name')}",
				message=f"Doc: {doc_name}\n{frappe.get_traceback()}",
			)

	frappe.db.set_value(
		"Automated Action",
		rule["name"],
		"last_scheduled_run",
		now,
		update_modified=False,
	)
	frappe.db.commit()
