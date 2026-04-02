# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


BLOCKED_PYTHON_PATTERNS = [
	"import os",
	"import subprocess",
	"import shutil",
	"__import__",
	"exec(",
	"eval(",
	"compile(",
	"open(",
	"frappe.db.sql",
	"frappe.destroy",
	"frappe.init",
]

ADVANCED_ACTION_TYPES = {
	"Execute Server Script",
	"Execute Jinja Expression",
	"Custom Python Handler",
	"External API Call",
	"Queue Background Job",
	"Branch / If-Else",
	"Wait / Delay",
	"Loop Through Child Rows",
	"Aggregate and Decide",
}


class AutomationRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from automated_actions.automated_actions.doctype.automation_action_step.automation_action_step import AutomationActionStep
		from automated_actions.automated_actions.doctype.automation_condition.automation_condition import AutomationCondition
		from frappe.types import DF

		action_steps: DF.Table[AutomationActionStep]
		allow_repeated_execution: DF.Check
		child_doctype: DF.Link | None
		company: DF.Link | None
		condition_logic: DF.Literal["All Match (AND)", "Any Match (OR)"]
		conditions: DF.Table[AutomationCondition]
		cron_expression: DF.Data | None
		custom_condition: DF.Code | None
		delay_count: DF.Int
		delay_type: DF.Literal["Minutes", "Hours", "Days", "Months"]
		document_type: DF.Link
		enabled: DF.Check
		field_from_value: DF.Data | None
		field_to_value: DF.Data | None
		last_error: DF.SmallText | None
		last_run: DF.Datetime | None
		last_scheduled_run: DF.Datetime | None
		linked_doctype: DF.Link | None
		linked_field: DF.Data | None
		linked_status_field: DF.Data | None
		module: DF.Link | None
		priority: DF.Int
		recursion_protection: DF.Check
		rule_name: DF.Data
		run_count: DF.Int
		run_mode: DF.Literal["Synchronous", "Asynchronous"]
		status: DF.Literal["Draft", "Active", "Paused", "Error"]
		stop_on_error: DF.Check
		trigger_date_field: DF.Literal[None]
		trigger_fields: DF.SmallText | None
		trigger_type: DF.Literal["", "On Create", "On Update", "On Create & Update", "On Delete", "Field Value Change", "Time Based", "Cron Schedule", "Child Record Added", "Linked Document Change", "Webhook Received"]
		webhook_secret: DF.Password | None
	# end: auto-generated types

	def validate(self):
		self._validate_action_steps()
		self._validate_conditions()
		self._set_action_categories()

	def _validate_action_steps(self):
		if not self.action_steps:
			frappe.throw(_("Please add at least one action step"))

		for step in self.action_steps:
			self._validate_step(step)

	def _validate_step(self, step):
		if step.action_type in ("Execute Server Script", "Custom Python Handler"):
			self._validate_python_code(step)

		if step.action_type in ("Update Current Record", "Update Linked Record"):
			if not step.field_updates_json:
				frappe.throw(
					_("Step {0}: Please provide field updates JSON for '{1}' action").format(
						step.idx, step.action_type
					)
				)
			self._validate_json_field(step, "field_updates_json")

		if step.action_type in ("Create Record", "Create Child Row"):
			if not step.target_doctype:
				frappe.throw(
					_("Step {0}: Please select a Target Document Type for '{1}' action").format(
						step.idx, step.action_type
					)
				)

		if step.action_type == "Send Email" and not step.email_template and not step.message_template:
			frappe.throw(
				_("Step {0}: Please provide an Email Template or Message Template for 'Send Email' action").format(
					step.idx
				)
			)

		if step.action_type == "Create ToDo" and not step.todo_description:
			frappe.throw(
				_("Step {0}: Please provide a description for 'Create ToDo' action").format(step.idx)
			)

		if step.action_type == "Call Webhook" and not step.webhook_url:
			frappe.throw(
				_("Step {0}: Please provide a URL for 'Call Webhook' action").format(step.idx)
			)

		if step.action_type == "Branch / If-Else" and not step.branch_condition:
			frappe.throw(
				_("Step {0}: Please provide a branch condition for 'Branch / If-Else' action").format(
					step.idx
				)
			)

		if step.action_type == "Change Workflow State" and not step.workflow_state:
			frappe.throw(
				_("Step {0}: Please specify a workflow state").format(step.idx)
			)

		if step.action_type in ("Add Tag", "Remove Tag") and not step.tag_value:
			frappe.throw(
				_("Step {0}: Please specify a tag value for '{1}' action").format(
					step.idx, step.action_type
				)
			)

		if step.action_type in ("Add Comment", "Create Activity") and not step.comment_text:
			frappe.throw(
				_("Step {0}: Please provide comment text for '{1}' action").format(
					step.idx, step.action_type
				)
			)

		if step.action_type == "Trigger Another Automation" and not step.target_automation_rule:
			frappe.throw(
				_("Step {0}: Please select a target Automation Rule").format(step.idx)
			)

	def _validate_python_code(self, step):
		if not step.python_code:
			frappe.throw(
				_("Step {0}: Please provide Python code for '{1}' action").format(
					step.idx, step.action_type
				)
			)

		code_lower = step.python_code.lower()
		for pattern in BLOCKED_PYTHON_PATTERNS:
			if pattern.lower() in code_lower:
				frappe.throw(
					_("Step {0}: Python code contains blocked operation: {1}").format(
						step.idx, pattern
					)
				)

	def _validate_conditions(self):
		for cond in self.conditions:
			if cond.operator not in ("is set", "is not set", "changed") and not cond.value:
				frappe.throw(
					_("Condition row {0}: Value is required for operator '{1}'").format(
						cond.idx, cond.operator
					)
				)

	def _validate_json_field(self, step, fieldname):
		value = step.get(fieldname)
		if value:
			try:
				parsed = json.loads(value)
				if not isinstance(parsed, list):
					frappe.throw(
						_("Step {0}: {1} must be a JSON array").format(step.idx, fieldname)
					)
			except json.JSONDecodeError:
				frappe.throw(
					_("Step {0}: {1} must be valid JSON").format(step.idx, fieldname)
				)

	def _set_action_categories(self):
		for step in self.action_steps:
			if step.action_type in ADVANCED_ACTION_TYPES:
				step.action_category = "Advanced Action"
			else:
				step.action_category = "Business Action"

	def on_update(self):
		_clear_automation_rule_cache()

	def on_trash(self):
		_clear_automation_rule_cache()


def _clear_automation_rule_cache():
	frappe.cache.delete_key("automation_rules")
