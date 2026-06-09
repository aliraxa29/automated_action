# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AutomationActionStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_category: DF.Literal["Business Action", "Advanced Action"]
		action_type: DF.Literal[
			"",
			"Update Current Record",
			"Update Linked Record",
			"Create Record",
			"Create Child Row",
			"Create ToDo",
			"Create Activity",
			"Add Comment",
			"Send Email",
			"Send WhatsApp",
			"Send Notification",
			"Assign User",
			"Add Tag",
			"Remove Tag",
			"Change Workflow State",
			"Call Webhook",
			"Trigger Another Automation",
			"Execute Server Script",
			"Execute Jinja Expression",
			"Custom Python Handler",
			"External API Call",
			"Queue Background Job",
			"Branch / If-Else",
			"Wait / Delay",
			"Loop Through Child Rows",
			"Aggregate and Decide",
		]
		assign_to_field: DF.Data | None
		assign_to_user: DF.Link | None
		branch_condition: DF.SmallText | None
		comment_text: DF.SmallText | None
		create_values_json: DF.Code | None
		email_template: DF.Link | None
		enabled: DF.Check
		execute_if: DF.SmallText | None
		field_updates_json: DF.Code | None
		jinja_template: DF.Code | None
		link_field: DF.Data | None
		loop_action_json: DF.Code | None
		loop_child_table: DF.Data | None
		message_template: DF.Text | None
		on_false_goto: DF.Int
		on_true_goto: DF.Int
		parent: DF.Data
		parent_doctype_field: DF.Data | None
		parentfield: DF.Data
		parenttype: DF.Data
		python_code: DF.Code | None
		send_to: DF.Data | None
		send_to_field: DF.Data | None
		step_name: DF.Data | None
		subject: DF.Data | None
		tag_value: DF.Data | None
		target_automation_rule: DF.Link | None
		target_doctype: DF.Link | None
		todo_description: DF.SmallText | None
		wait_duration: DF.Int
		wait_duration_type: DF.Literal["Seconds", "Minutes", "Hours", "Days"]
		webhook_auth_credentials: DF.Password | None
		webhook_auth_type: DF.Literal["None", "Basic Auth", "Bearer Token", "API Key"]
		whatsapp_template: DF.Data | None
		webhook_body_json: DF.Code | None
		webhook_headers_json: DF.Code | None
		webhook_method: DF.Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
		webhook_url: DF.Data | None
		workflow_state: DF.Data | None
	# end: auto-generated types

	pass
