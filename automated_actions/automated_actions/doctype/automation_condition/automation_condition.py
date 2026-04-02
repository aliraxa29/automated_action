# Copyright (c) 2026, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AutomationCondition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fieldname: DF.Data
		operator: DF.Literal["=", "!=", ">", "<", ">=", "<=", "like", "not like", "in", "not in", "is set", "is not set", "changed", "changed to", "changed from"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		value: DF.SmallText | None
		value_type: DF.Literal["Static Value", "Document Field", "Jinja Expression"]
	# end: auto-generated types

	pass
