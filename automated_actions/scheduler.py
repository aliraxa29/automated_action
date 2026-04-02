# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

"""
Scheduler for time-based and cron-based Automation Rule triggers.

process_time_based_automation_rules() — runs periodically for delay-based triggers.
process_cron_automation_rules() — runs every minute to check cron-scheduled rules.
"""

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime
from automated_actions.conditions import evaluate_conditions
from automated_actions.engine import run_automation_rule


def process_time_based_automation_rules():
	"""Process all Automation Rules with 'Time Based' trigger.

	Called periodically (default: every 15 minutes).
	Finds documents matching the date/delay criteria and runs the rule.
	"""
	rules = frappe.get_all(
		"Automation Rule",
		filters={"enabled": 1, "trigger_type": "Time Based"},
		fields=["name", "rule_name", "document_type", "trigger_date_field",
				"delay_count", "delay_type", "last_scheduled_run"],
	)

	for rule_dict in rules:
		try:
			_process_time_rule(rule_dict)
		except Exception:
			frappe.log_error(
				title=f"Automation Rule Scheduler Error: {rule_dict.get('rule_name', rule_dict.get('name'))}",
				message=frappe.get_traceback(),
			)


def _process_time_rule(rule_dict):
	"""Process a single time-based Automation Rule."""
	date_field = rule_dict.get("trigger_date_field")
	if not date_field:
		return

	delay_count = rule_dict.get("delay_count", 0)
	delay_type = (rule_dict.get("delay_type") or "Hours").lower()

	now = now_datetime()
	last_run = get_datetime(rule_dict["last_scheduled_run"]) if rule_dict.get("last_scheduled_run") else None

	target_date = add_to_date(now, **{delay_type: -delay_count})

	filters = {date_field: ["<=", target_date]}

	if last_run:
		last_target_date = add_to_date(last_run, **{delay_type: -delay_count})
		filters[date_field] = ["between", [last_target_date, target_date]]

	rule = frappe.get_doc("Automation Rule", rule_dict["name"])

	try:
		docs = frappe.get_all(
			rule_dict["document_type"],
			filters=filters,
			pluck="name",
			limit=500,
		)
	except Exception:
		frappe.log_error(title="Automation Rule: Time query error", message=frappe.get_traceback())
		return

	for doc_name in docs:
		try:
			doc = frappe.get_doc(rule_dict["document_type"], doc_name)
			if evaluate_conditions(rule, doc):
				run_automation_rule(rule, doc, trigger_context={"trigger": "time_based"})
		except Exception:
			frappe.log_error(
				title=f"Automation Rule Error: {rule_dict.get('rule_name')}",
				message=f"Doc: {doc_name}\n{frappe.get_traceback()}",
			)

	frappe.db.set_value(
		"Automation Rule", rule_dict["name"], "last_scheduled_run", now, update_modified=False
	)
	frappe.db.commit()


def process_cron_automation_rules():
	"""Process all Automation Rules with 'Cron Schedule' trigger.

	Called every minute. Checks if the cron expression matches the current time.
	"""
	rules = frappe.get_all(
		"Automation Rule",
		filters={"enabled": 1, "trigger_type": "Cron Schedule"},
		fields=["name", "rule_name", "document_type", "cron_expression",
				"last_scheduled_run"],
	)

	now = now_datetime()

	for rule_dict in rules:
		try:
			if not _cron_matches(rule_dict.get("cron_expression"), now):
				continue
			_process_cron_rule(rule_dict)
		except Exception:
			frappe.log_error(
				title=f"Automation Cron Error: {rule_dict.get('rule_name', rule_dict.get('name'))}",
				message=frappe.get_traceback(),
			)


def _process_cron_rule(rule_dict):
	"""Process a single cron-scheduled Automation Rule against all matching documents."""
	rule = frappe.get_doc("Automation Rule", rule_dict["name"])
	now = now_datetime()

	try:
		docs = frappe.get_all(
			rule_dict["document_type"],
			pluck="name",
			limit=500,
		)
	except Exception:
		frappe.log_error(title="Automation Rule: Cron query error", message=frappe.get_traceback())
		return

	for doc_name in docs:
		try:
			doc = frappe.get_doc(rule_dict["document_type"], doc_name)
			if evaluate_conditions(rule, doc):
				run_automation_rule(rule, doc, trigger_context={"trigger": "cron"})
		except Exception:
			frappe.log_error(
				title=f"Automation Cron Error: {rule_dict.get('rule_name')}",
				message=f"Doc: {doc_name}\n{frappe.get_traceback()}",
			)

	frappe.db.set_value(
		"Automation Rule", rule_dict["name"], "last_scheduled_run", now, update_modified=False
	)
	frappe.db.commit()


def _cron_matches(expression, dt):
	"""Check if a cron expression matches a given datetime.

	Supports standard 5-field cron: minute hour day_of_month month day_of_week.
	"""
	if not expression:
		return False

	parts = expression.strip().split()
	if len(parts) != 5:
		return False

	checks = [
		(parts[0], dt.minute),      # minute (0-59)
		(parts[1], dt.hour),        # hour (0-23)
		(parts[2], dt.day),         # day of month (1-31)
		(parts[3], dt.month),       # month (1-12)
		(parts[4], dt.weekday()),   # day of week (0=Mon in Python, cron uses 0=Sun)
	]

	for pattern, value in checks:
		if not _cron_field_matches(pattern, value):
			return False

	return True


def _cron_field_matches(pattern, value):
	"""Check if a single cron field pattern matches a value."""
	if pattern == "*":
		return True

	for part in pattern.split(","):
		part = part.strip()

		if "/" in part:
			base, step_str = part.split("/", 1)
			try:
				step = int(step_str)
			except ValueError:
				continue
			if base == "*":
				if value % step == 0:
					return True
			else:
				try:
					base_val = int(base)
					if value >= base_val and (value - base_val) % step == 0:
						return True
				except ValueError:
					continue
		elif "-" in part:
			try:
				low, high = part.split("-", 1)
				if int(low) <= value <= int(high):
					return True
			except ValueError:
				continue
		else:
			try:
				if int(part) == value:
					return True
			except ValueError:
				continue

	return False
