# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class AutomatedAction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from automated_actions.automated_actions.doctype.automated_action_field_update.automated_action_field_update import (
			AutomatedActionFieldUpdate,
		)

		action_name: DF.Data
		action_type: DF.Literal[
			"",
			"Update Record",
			"Create Record",
			"Execute Python Code",
			"Send Email",
			"Create ToDo",
			"Add Comment",
		]
		apply_on_condition: DF.Code | None
		assign_to_field: DF.Data | None
		assign_to_user: DF.Link | None
		before_condition: DF.Code | None
		comment_text: DF.SmallText | None
		delay_count: DF.Int
		delay_type: DF.Literal["Minutes", "Hours", "Days", "Months"]
		document_type: DF.Link
		email_template: DF.Link | None
		enabled: DF.Check
		field_updates: DF.Table[AutomatedActionFieldUpdate]
		last_run: DF.Datetime | None
		last_scheduled_run: DF.Datetime | None
		link_field: DF.Data | None
		new_record_values: DF.Table[AutomatedActionFieldUpdate]
		python_code: DF.Code | None
		run_count: DF.Int
		send_to_field: DF.Data | None
		target_document_type: DF.Link | None
		todo_description: DF.SmallText | None
		trigger: DF.Literal[
			"", "On Create", "On Update", "On Create & Update", "On Delete", "Based on Time Condition"
		]
		trigger_date_field: DF.Data | None
		trigger_fields: DF.SmallText | None

	# end: auto-generated types

	def validate(self):
		self._validate_conditions()
		self._validate_action_config()
		self._validate_python_code()

	def _validate_conditions(self):
		"""Validate that condition JSON is well-formed."""
		for field in ("before_condition", "apply_on_condition"):
			value = self.get(field)
			if value:
				try:
					parsed = json.loads(value)
					if not isinstance(parsed, list):
						frappe.throw(
							_("{0} must be a JSON array of filter conditions").format(
								self.meta.get_label(field)
							)
						)
				except json.JSONDecodeError:
					frappe.throw(_("{0} must be valid JSON").format(self.meta.get_label(field)))

	def _validate_action_config(self):
		"""Validate that action-specific required fields are set."""
		if self.action_type == "Update Record" and not self.field_updates:
			frappe.throw(_("Please add at least one field update for 'Update Record' action"))

		if self.action_type == "Execute Python Code" and not self.python_code:
			frappe.throw(_("Please provide Python code for 'Execute Python Code' action"))

		if self.action_type == "Send Email" and not self.email_template:
			frappe.throw(_("Please select an Email Template for 'Send Email' action"))

		if self.action_type == "Create Record" and not self.target_document_type:
			frappe.throw(_("Please select a Target Document Type for 'Create Record' action"))

		if self.action_type == "Create ToDo" and not self.todo_description:
			frappe.throw(_("Please provide a ToDo Description for 'Create ToDo' action"))

		if self.action_type == "Add Comment" and not self.comment_text:
			frappe.throw(_("Please provide Comment Text for 'Add Comment' action"))

	def _validate_python_code(self):
		"""Block dangerous operations in custom Python code."""
		if self.action_type != "Execute Python Code" or not self.python_code:
			return

		blocked = [
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
		code_lower = self.python_code.lower()
		for pattern in blocked:
			if pattern.lower() in code_lower:
				frappe.throw(
					_("Python code contains blocked operation: {0}. Use Frappe ORM methods instead.").format(
						pattern
					)
				)

	def on_update(self):
		_clear_automated_action_cache()

	def on_trash(self):
		_clear_automated_action_cache()


def _clear_automated_action_cache():
	"""Clear the cached rules so handlers pick up changes."""
	frappe.cache.delete_key("automated_action_rules")
