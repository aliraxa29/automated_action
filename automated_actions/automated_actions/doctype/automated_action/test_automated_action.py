# Copyright (c) 2026, Ali Raxa and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAutomatedAction(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _create_rule(self, **kwargs):
		"""Helper to create an Automated Action rule for testing."""
		defaults = {
			"doctype": "Automated Action",
			"action_name": frappe.generate_hash(length=10),
			"document_type": "ToDo",
			"enabled": 1,
			"trigger": "On Create",
			"action_type": "Add Comment",
			"comment_text": "Auto comment from test",
		}
		defaults.update(kwargs)
		rule = frappe.get_doc(defaults)
		rule.insert(ignore_permissions=True)
		return rule

	def test_rule_creation(self):
		rule = self._create_rule()
		self.assertTrue(rule.name)
		self.assertEqual(rule.enabled, 1)

	def test_on_create_trigger(self):
		"""Test that On Create trigger fires when a new document is created."""
		self._create_rule(
			action_type="Add Comment",
			comment_text="Created by automation",
		)
		frappe.cache.delete_key("automated_action_rules")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Test on create"})
		todo.insert(ignore_permissions=True)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "ToDo",
				"reference_name": todo.name,
				"comment_type": "Comment",
			},
			pluck="content",
		)
		self.assertTrue(any("Created by automation" in (c or "") for c in comments))

	def test_on_update_trigger_with_field_change(self):
		"""Test that On Update with trigger_fields only fires on matching field changes."""
		self._create_rule(
			trigger="On Update",
			trigger_fields="status",
			action_type="Add Comment",
			comment_text="Status changed!",
		)
		frappe.cache.delete_key("automated_action_rules")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Test on update"})
		todo.insert(ignore_permissions=True)

		# Update a non-trigger field - should NOT trigger
		todo.description = "Updated description"
		todo.save(ignore_permissions=True)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "ToDo",
				"reference_name": todo.name,
				"comment_type": "Comment",
				"content": ["like", "%Status changed%"],
			},
		)
		self.assertEqual(len(comments), 0)

		# Update the trigger field - SHOULD trigger
		todo.status = "Cancelled"
		todo.save(ignore_permissions=True)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "ToDo",
				"reference_name": todo.name,
				"comment_type": "Comment",
				"content": ["like", "%Status changed%"],
			},
		)
		self.assertTrue(len(comments) > 0)

	def test_before_and_apply_on_conditions(self):
		"""Test before_condition and apply_on_condition filtering."""
		self._create_rule(
			trigger="On Update",
			trigger_fields="status",
			before_condition=json.dumps([["status", "=", "Open"]]),
			apply_on_condition=json.dumps([["status", "=", "Closed"]]),
			action_type="Add Comment",
			comment_text="Transitioned Open to Closed!",
		)
		frappe.cache.delete_key("automated_action_rules")

		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test conditions",
				"status": "Open",
			}
		)
		todo.insert(ignore_permissions=True)

		# Change to Closed (matches both conditions)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "ToDo",
				"reference_name": todo.name,
				"comment_type": "Comment",
				"content": ["like", "%Transitioned Open to Closed%"],
			},
		)
		self.assertTrue(len(comments) > 0)

	def test_update_record_action(self):
		"""Test Update Record action modifies the document."""
		self._create_rule(
			trigger="On Create",
			action_type="Update Record",
			field_updates=[
				{"fieldname": "priority", "value": "High"},
			],
		)
		frappe.cache.delete_key("automated_action_rules")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Test update record"})
		todo.insert(ignore_permissions=True)

		todo.reload()
		self.assertEqual(todo.priority, "High")

	def test_disabled_rule_does_not_fire(self):
		"""Disabled rules should not execute."""
		self._create_rule(
			enabled=0,
			action_type="Add Comment",
			comment_text="Should not appear",
		)
		frappe.cache.delete_key("automated_action_rules")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Test disabled"})
		todo.insert(ignore_permissions=True)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "ToDo",
				"reference_name": todo.name,
				"comment_type": "Comment",
				"content": ["like", "%Should not appear%"],
			},
		)
		self.assertEqual(len(comments), 0)

	def test_python_code_blocked_patterns(self):
		"""Ensure dangerous Python code is blocked during validation."""
		with self.assertRaises(frappe.exceptions.ValidationError):
			self._create_rule(
				action_type="Execute Python Code",
				python_code="import os\nos.system('ls')",
			)

	def test_condition_json_validation(self):
		"""Ensure invalid JSON in conditions is rejected."""
		with self.assertRaises(frappe.exceptions.ValidationError):
			self._create_rule(
				before_condition="not valid json {{{",
			)
