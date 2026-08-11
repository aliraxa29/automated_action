# Copyright (c) 2026, Kodlyft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

test_ignore = ["Company"]


class TestAutomationRule(FrappeTestCase):
	def test_rule_creation(self):
		rule = frappe.get_doc(
			{
				"doctype": "Automation Rule",
				"rule_name": "Test Rule - On Create",
				"document_type": "ToDo",
				"trigger_type": "On Create",
				"enabled": 1,
				"action_steps": [
					{
						"step_name": "Add Comment",
						"action_type": "Add Comment",
						"comment_text": "Auto-created comment",
						"enabled": 1,
					}
				],
			}
		)
		rule.insert(ignore_permissions=True)
		self.assertTrue(rule.name)
		rule.delete()

	def test_conditions_validation(self):
		rule = frappe.get_doc(
			{
				"doctype": "Automation Rule",
				"rule_name": "Test Rule - With Conditions",
				"document_type": "ToDo",
				"trigger_type": "On Update",
				"enabled": 1,
				"conditions": [
					{
						"fieldname": "status",
						"operator": "=",
						"value": "Open",
					}
				],
				"action_steps": [
					{
						"step_name": "Update Record",
						"action_type": "Add Comment",
						"comment_text": "Status is Open",
						"enabled": 1,
					}
				],
			}
		)
		rule.insert(ignore_permissions=True)
		self.assertEqual(len(rule.conditions), 1)
		rule.delete()

	def test_multi_step_creation(self):
		rule = frappe.get_doc(
			{
				"doctype": "Automation Rule",
				"rule_name": "Test Rule - Multi Step",
				"document_type": "ToDo",
				"trigger_type": "On Create",
				"enabled": 1,
				"action_steps": [
					{
						"step_name": "Step 1 - Comment",
						"action_type": "Add Comment",
						"comment_text": "Step 1 executed",
						"enabled": 1,
					},
					{
						"step_name": "Step 2 - Tag",
						"action_type": "Add Tag",
						"tag_value": "automated",
						"enabled": 1,
					},
				],
			}
		)
		rule.insert(ignore_permissions=True)
		self.assertEqual(len(rule.action_steps), 2)
		self.assertEqual(rule.action_steps[0].action_category, "Business Action")
		rule.delete()

	def test_python_code_validation(self):
		rule = frappe.get_doc(
			{
				"doctype": "Automation Rule",
				"rule_name": "Test Rule - Blocked Python",
				"document_type": "ToDo",
				"trigger_type": "On Create",
				"enabled": 1,
				"action_steps": [
					{
						"step_name": "Bad Code",
						"action_type": "Execute Server Script",
						"python_code": "import os\nos.system('rm -rf /')",
						"enabled": 1,
					}
				],
			}
		)
		self.assertRaises(frappe.ValidationError, rule.insert)
