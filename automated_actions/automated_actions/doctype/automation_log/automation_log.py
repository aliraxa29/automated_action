# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AutomationLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from automated_actions.automated_actions.doctype.automation_log_step.automation_log_step import (
			AutomationLogStep,
		)

		automation_rule: DF.Link | None
		completed_at: DF.Datetime | None
		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		duration_ms: DF.Float
		error_message: DF.LongText | None
		rule_name: DF.Data | None
		started_at: DF.Datetime | None
		status: DF.Literal["Running", "Success", "Partial", "Failed", "Skipped"]
		steps: DF.Table[AutomationLogStep]
		trigger_type: DF.Data | None
	# end: auto-generated types

	pass
