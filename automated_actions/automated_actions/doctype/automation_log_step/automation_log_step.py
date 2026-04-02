# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AutomationLogStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_type: DF.Data | None
		completed_at: DF.Datetime | None
		error_message: DF.LongText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		result_summary: DF.SmallText | None
		started_at: DF.Datetime | None
		status: DF.Literal["Pending", "Success", "Failed", "Skipped"]
		step_name: DF.Data | None

	# end: auto-generated types

	pass
