// Copyright (c) 2026, Ali Raxa and contributors
// For license information, please see license.txt

frappe.ui.form.on("Automation Rule", {
	refresh(frm) {
		_set_queries(frm);
		_set_dynamic_field_options(frm);
		_toggle_trigger_sections(frm);

		if (!frm.is_new() && frm.doc.enabled) {
			frm.add_custom_button(__("Test Run"), function () {
				frappe.call({
					method: "automated_actions.engine.test_automation_rule",
					args: { rule_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint({
								title: __("Test Result"),
								message: r.message,
								indicator: r.message.includes("Error") ? "red" : "green",
							});
						}
					},
				});
			});

			frm.add_custom_button(
				__("View Logs"),
				function () {
					frappe.set_route("List", "Automation Log", {
						automation_rule: frm.doc.name,
					});
				},
				__("View")
			);
		}

		if (frm.doc.run_count) {
			frm.dashboard.add_indicator(
				__("Executed {0} times", [frm.doc.run_count]),
				"blue"
			);
		}

		if (frm.doc.last_error) {
			frm.dashboard.add_indicator(__("Last run had errors"), "red");
		}
	},

	document_type(frm) {
		_set_dynamic_field_options(frm);
	},

	trigger_type(frm) {
		_toggle_trigger_sections(frm);
	},
});

frappe.ui.form.on("Automation Action Step", {
	action_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		_set_action_category(row);
		frm.refresh_field("action_steps");
	},
});

frappe.ui.form.on("Automation Condition", {
	fieldname(frm, cdt, cdn) {
		frm.refresh_field("conditions");
	},
});

function _set_queries(frm) {
	frm.set_query("document_type", function () {
		return { filters: { istable: 0, issingle: 0 } };
	});

	frm.set_query("child_doctype", function () {
		return { filters: { istable: 1 } };
	});

	frm.set_query("linked_doctype", function () {
		return { filters: { istable: 0, issingle: 0 } };
	});

	frm.fields_dict.action_steps.grid.get_field("target_doctype").get_query =
		function () {
			return { filters: { istable: 0, issingle: 0 } };
		};

	frm.fields_dict.action_steps.grid.get_field("email_template").get_query =
		function () {
			return {};
		};

	frm.fields_dict.action_steps.grid.get_field("target_automation_rule").get_query =
		function () {
			return {
				filters: {
					name: ["!=", frm.doc.name],
					enabled: 1,
				},
			};
		};
}

function _set_dynamic_field_options(frm) {
	if (!frm.doc.document_type) {
		frm.set_df_property("trigger_date_field", "options", "");
		return;
	}

	frappe.model.with_doctype(frm.doc.document_type, function () {
		const meta = frappe.get_meta(frm.doc.document_type);

		const dateFields = meta.fields
			.filter((f) => ["Date", "Datetime"].includes(f.fieldtype))
			.map((f) => f.fieldname);
		frm.set_df_property(
			"trigger_date_field",
			"options",
			["", ...dateFields].join("\n")
		);

		const allFields = meta.fields
			.filter(
				(f) =>
					f.fieldname &&
					!frappe.model.no_value_type.includes(f.fieldtype)
			)
			.map((f) => f.fieldname);
		const fieldOptions = ["", ...allFields].join("\n");

		if (frm.fields_dict.conditions) {
			frm.fields_dict.conditions.grid.update_docfield_property(
				"fieldname",
				"options",
				fieldOptions
			);
			frm.refresh_field("conditions");
		}
	});
}

function _toggle_trigger_sections(frm) {
	const tt = frm.doc.trigger_type;

	const hasFields = [
		"On Update",
		"On Create & Update",
		"Field Value Change",
	].includes(tt);
	frm.toggle_display("trigger_fields", hasFields);

	const hasFromTo = tt === "Field Value Change";
	frm.toggle_display("field_from_value", hasFromTo);
	frm.toggle_display("field_to_value", hasFromTo);

	frm.toggle_display("cron_expression", tt === "Cron Schedule");

	const isTimeBased = tt === "Time Based";
	frm.toggle_display("trigger_date_field", isTimeBased);
	frm.toggle_display("delay_count", isTimeBased);
	frm.toggle_display("delay_type", isTimeBased);

	frm.toggle_display("child_doctype", tt === "Child Record Added");
	frm.toggle_display("linked_doctype", tt === "Linked Document Change");
	frm.toggle_display("linked_field", tt === "Linked Document Change");
	frm.toggle_display("linked_status_field", tt === "Linked Document Change");

	frm.toggle_display("webhook_secret", tt === "Webhook Received");
}

function _set_action_category(row) {
	const advanced = [
		"Execute Server Script",
		"Execute Jinja Expression",
		"Custom Python Handler",
		"External API Call",
		"Queue Background Job",
		"Branch / If-Else",
		"Wait / Delay",
		"Loop Through Child Rows",
		"Aggregate and Decide",
	];

	if (advanced.includes(row.action_type)) {
		row.action_category = "Advanced Action";
	} else {
		row.action_category = "Business Action";
	}
}
