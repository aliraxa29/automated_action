// Copyright (c) 2026, Ali Raxa and contributors
// For license information, please see license.txt

frappe.ui.form.on("Automation Rule", {
	refresh(frm) {
		_set_queries(frm);
		_set_dynamic_field_options(frm);
		_toggle_trigger_sections(frm);
		_setup_whatsapp_template_field(frm);

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
			frm.dashboard.add_indicator(__("Executed {0} times", [frm.doc.run_count]), "blue");
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

	email_template(frm, cdt, cdn) {
		_fetch_email_template(frm, cdt, cdn);
	},

	whatsapp_template(frm, cdt, cdn) {
		_fetch_whatsapp_template(frm, cdt, cdn);
	},

	form_render(frm, cdt, cdn) {
		_setup_json_editor_buttons(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Automation Condition", {
	value_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.value_type === "Document Field") {
			frappe.model.set_value(cdt, cdn, "value", row.value_document_field || "");
		}
		frm.refresh_field("conditions");
	},

	value_document_field(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "value", row.value_document_field);
	},

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

	frm.fields_dict.action_steps.grid.get_field("target_doctype").get_query = function () {
		return { filters: { istable: 0, issingle: 0 } };
	};

	frm.fields_dict.action_steps.grid.get_field("email_template").get_query = function () {
		return {};
	};

	frm.fields_dict.action_steps.grid.get_field("target_automation_rule").get_query = function () {
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
		if (frm.fields_dict.conditions) {
			frm.fields_dict.conditions.grid.update_docfield_property("fieldname", "options", "");
			frm.fields_dict.conditions.grid.update_docfield_property(
				"value_document_field",
				"options",
				""
			);
			frm.refresh_field("conditions");
		}
		return;
	}

	frappe.model.with_doctype(frm.doc.document_type, function () {
		const meta = frappe.get_meta(frm.doc.document_type);

		const dateFields = meta.fields
			.filter((f) => ["Date", "Datetime"].includes(f.fieldtype))
			.map((f) => f.fieldname);
		frm.set_df_property("trigger_date_field", "options", ["", ...dateFields].join("\n"));

		const allFields = meta.fields
			.filter((f) => f.fieldname && !frappe.model.no_value_type.includes(f.fieldtype))
			.map((f) => `${f.fieldname}`);
		const fieldOptions = ["", ...allFields].join("\n");

		if (frm.fields_dict.conditions) {
			frm.fields_dict.conditions.grid.update_docfield_property(
				"fieldname",
				"options",
				fieldOptions
			);
			frm.fields_dict.conditions.grid.update_docfield_property(
				"value_document_field",
				"options",
				fieldOptions
			);
			frm.refresh_field("conditions");
		}
	});
}

function _toggle_trigger_sections(frm) {
	const tt = frm.doc.trigger_type;

	const hasFields = ["On Update", "On Create & Update", "Field Value Change"].includes(tt);
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

function _fetch_email_template(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.email_template) return;

	frappe.db.get_value("Email Template", row.email_template, ["subject", "response"], (r) => {
		if (r) {
			frappe.model.set_value(cdt, cdn, "subject", r.subject || "");
			frappe.model.set_value(cdt, cdn, "message_template", r.response || "");
			frm.refresh_field("action_steps");
		}
	});
}

let _whatsapp_doctype = null;

function _setup_whatsapp_template_field(frm) {
	const possible_doctypes = [
		"WhatsApp Templates",
		"WhatsApp Message Template",
		"WhatsApp Template",
	];

	frappe
		.xcall(
			"automated_actions.automated_actions.doctype.automation_rule.automation_rule.get_whatsapp_template_doctype",
			{
				possible_doctypes: possible_doctypes,
			}
		)
		.then((doctype_name) => {
			_whatsapp_doctype = doctype_name;
			if (doctype_name && frm.fields_dict.action_steps) {
				frm.fields_dict.action_steps.grid.update_docfield_property(
					"whatsapp_template",
					"description",
					__("Linked to {0}", [doctype_name])
				);
			} else if (frm.fields_dict.action_steps) {
				frm.fields_dict.action_steps.grid.update_docfield_property(
					"whatsapp_template",
					"hidden",
					1
				);
			}
			frm.refresh_field("action_steps");
		});
}

function _fetch_whatsapp_template(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.whatsapp_template || !_whatsapp_doctype) return;

	frappe.db.get_value(_whatsapp_doctype, row.whatsapp_template, ["*"], (r) => {
		if (r) {
			const subject = r.subject || r.template_name || r.name || "";
			const message = r.message || r.template || r.response || r.content || r.body || "";
			frappe.model.set_value(cdt, cdn, "subject", subject);
			frappe.model.set_value(cdt, cdn, "message_template", message);
			frm.refresh_field("action_steps");
		}
	});
}

function _setup_json_editor_buttons(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const grid_row = frm.fields_dict.action_steps.grid.grid_rows_by_docname[cdn];
	if (!grid_row || !grid_row.grid_form) return;
	const fields_dict = grid_row.grid_form.fields_dict;

	if (["Update Current Record", "Update Linked Record"].includes(row.action_type)) {
		const target_dt =
			row.action_type === "Update Current Record"
				? frm.doc.document_type
				: row.target_doctype;
		_attach_editor_btn(
			fields_dict.field_updates_json,
			__("Edit Field Updates"),
			frm,
			cdt,
			cdn,
			"field_updates_json",
			target_dt
		);
	}

	if (["Create Record", "Create Child Row"].includes(row.action_type)) {
		_attach_editor_btn(
			fields_dict.create_values_json,
			__("Edit Record Values"),
			frm,
			cdt,
			cdn,
			"create_values_json",
			row.target_doctype
		);
	}
}

function _attach_editor_btn(field_control, label, frm, cdt, cdn, fieldname, doctype_for_fields) {
	if (!field_control || !field_control.$wrapper) return;
	const $wrapper = field_control.$wrapper;

	if ($wrapper.find(".json-editor-btn").length) return;

	const $btn =
		$(`<button class="btn btn-xs btn-default json-editor-btn" style="margin-bottom:8px; margin-top:4px;">
		<svg class="icon icon-sm" style="margin-right:4px;"><use href="#icon-edit"></use></svg>${label}
	</button>`);

	$btn.on("click", function (e) {
		e.preventDefault();
		e.stopPropagation();
		_open_json_editor_dialog(frm, cdt, cdn, fieldname, label, doctype_for_fields);
	});

	$wrapper.find(".control-input-wrapper").first().before($btn);
	if (!$wrapper.find(".json-editor-btn").length) {
		$wrapper.prepend($btn);
	}
}

function _get_selectable_fields(doctype) {
	if (!doctype) {
		return [];
	}

	const meta = frappe.get_meta(doctype);
	return meta.fields.filter(
		(field) => field.fieldname && !frappe.model.no_value_type.includes(field.fieldtype)
	);
}

function _format_action_entry_value(value) {
	if (Array.isArray(value) || (value && typeof value === "object")) {
		return JSON.stringify(value, null, 2);
	}

	return value ?? "";
}

function _parse_action_entry_value(value) {
	if (typeof value !== "string") {
		return value;
	}

	const trimmed = value.trim();
	if (!trimmed) {
		return "";
	}

	if (["[", "{"].includes(trimmed[0])) {
		try {
			return JSON.parse(trimmed);
		} catch (e) {
			return value;
		}
	}

	return value;
}

function _open_json_editor_dialog(frm, cdt, cdn, fieldname, title, doctype_for_fields) {
	const row = locals[cdt][cdn];
	let existing = [];
	try {
		existing = JSON.parse(row[fieldname] || "[]");
	} catch (e) {
		existing = [];
	}

	if (!doctype_for_fields) {
		frappe.msgprint(__("Please select a Target Document Type first."));
		return;
	}

	frappe.model.with_doctype(doctype_for_fields, () => {
		const target_field_options = [
			"",
			..._get_selectable_fields(doctype_for_fields).map((field) => field.fieldname),
		];

		const render_dialog = (source_field_options) => {
			const d = new frappe.ui.Dialog({
				title: title + " — " + doctype_for_fields,
				size: "extra-large",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "help_text",
						options: `<p class="text-muted" style="margin-bottom:10px;">
							Select fields from <strong>${doctype_for_fields}</strong> and set their values.
							Use <strong>Document Field</strong> to copy a value from the triggering document,
							or use <strong>Jinja Expression</strong> like <code>{{ doc.fieldname }}</code>.
						</p>`,
					},
					{
						fieldtype: "Table",
						fieldname: "entries",
						label: __("Fields"),
						cannot_add_rows: false,
						in_place_edit: true,
						fields: [
							{
								fieldtype: "Select",
								fieldname: "fieldname",
								label: __("Field"),
								options: target_field_options.join("\n"),
								in_list_view: 1,
								reqd: 1,
								columns: 3,
							},
							{
								fieldtype: "Select",
								fieldname: "value_type",
								label: __("Type"),
								options: "Static Value\nDocument Field\nJinja Expression",
								default: "Static Value",
								in_list_view: 1,
								columns: 2,
							},
							{
								fieldtype: "Small Text",
								fieldname: "value",
								label: __("Value"),
								in_list_view: 1,
								columns: 4,
							},
							{
								fieldtype: "Select",
								fieldname: "value_document_field",
								label: __("Source Field"),
								options: source_field_options.join("\n"),
								in_list_view: 1,
								columns: 3,
							},
						],
						data: existing.map((entry) => {
							const inferred_type =
								entry.value_type ||
								(entry.value_document_field ? "Document Field" : "") ||
								(typeof entry.value === "string" && entry.value.includes("{{")
									? "Jinja Expression"
									: "Static Value");

							return {
								fieldname: entry.fieldname || "",
								value_type: inferred_type,
								value:
									inferred_type === "Document Field"
										? ""
										: _format_action_entry_value(entry.value),
								value_document_field:
									entry.value_document_field ||
									(inferred_type === "Document Field" ? entry.value || "" : ""),
							};
						}),
					},
				],
				primary_action_label: __("Apply"),
				primary_action(values) {
					const entries = (values.entries || [])
						.filter((entry) => entry.fieldname)
						.map((entry) => {
							const payload = {
								fieldname: entry.fieldname,
								value_type: entry.value_type || "Static Value",
							};

							if (payload.value_type === "Document Field") {
								payload.value_document_field = entry.value_document_field || "";
								payload.value = payload.value_document_field || "";
							} else {
								payload.value = _parse_action_entry_value(entry.value);
							}

							return payload;
						});

					frappe.model.set_value(cdt, cdn, fieldname, JSON.stringify(entries, null, 2));
					frm.dirty();
					d.hide();
				},
			});

			d.show();
		};

		if (frm.doc.document_type) {
			frappe.model.with_doctype(frm.doc.document_type, () => {
				const source_field_options = [
					"",
					..._get_selectable_fields(frm.doc.document_type).map(
						(field) => field.fieldname
					),
				];
				render_dialog(source_field_options);
			});
		} else {
			render_dialog([""]);
		}
	});
}
