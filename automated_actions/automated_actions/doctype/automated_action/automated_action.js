// Copyright (c) 2026, Ali Raxa and contributors
// For license information, please see license.txt

frappe.ui.form.on("Automated Action", {
	refresh(frm) {
		frm.set_query("document_type", function () {
			return {
				filters: {
					istable: 0,
					issingle: 0,
				},
			};
		});

		frm.set_query("target_document_type", function () {
			return {
				filters: {
					istable: 0,
					issingle: 0,
				},
			};
		});

		_set_source_doctype_field_options(frm);
		_set_target_doctype_field_options(frm);
		_render_condition_builders(frm);
		_toggle_sections(frm);

		if (!frm.is_new() && frm.doc.enabled) {
			frm.add_custom_button(__("Test Run"), function () {
				frappe.call({
					method: "automated_actions.core.test_automated_action",
					args: { action_name: frm.doc.name },
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
		}

		if (frm.doc.run_count) {
			frm.dashboard.add_indicator(__("Executed {0} times", [frm.doc.run_count]), "blue");
		}
	},

	document_type(frm) {
		_set_source_doctype_field_options(frm);
		_render_condition_builders(frm);
	},

	target_document_type(frm) {
		_set_target_doctype_field_options(frm);
	},

	trigger(frm) {
		_toggle_sections(frm);
	},

	action_type(frm) {
		_toggle_sections(frm);
	},
});

function _set_source_doctype_field_options(frm) {
	_set_field_options(
		frm,
		frm.doc.document_type,
		{
			trigger_date_field: (field) => ["Date", "Datetime"].includes(field.fieldtype),
			send_to_field: _is_value_field,
			assign_to_field: _is_value_field,
		},
		"field_updates"
	);
}

function _set_target_doctype_field_options(frm) {
	_set_field_options(
		frm,
		frm.doc.target_document_type,
		{
			link_field: _is_value_field,
		},
		"new_record_values"
	);
}

function _set_field_options(frm, doctype, formFieldFilters, tableFieldname) {
	if (!doctype) {
		Object.keys(formFieldFilters).forEach((fieldname) => {
			frm.set_df_property(fieldname, "options", "");
		});

		if (tableFieldname && frm.fields_dict[tableFieldname]) {
			frm.fields_dict[tableFieldname].grid.update_docfield_property(
				"fieldname",
				"options",
				""
			);
			frm.refresh_field(tableFieldname);
		}
		return;
	}

	frappe.model.with_doctype(doctype, function () {
		const meta = frappe.get_meta(doctype);

		Object.entries(formFieldFilters).forEach(([fieldname, filterFn]) => {
			frm.set_df_property(fieldname, "options", _build_field_options(meta, filterFn));
		});

		if (tableFieldname && frm.fields_dict[tableFieldname]) {
			frm.fields_dict[tableFieldname].grid.update_docfield_property(
				"fieldname",
				"options",
				_build_field_options(meta, _is_value_field)
			);
			frm.refresh_field(tableFieldname);
		}
	});
}

function _build_field_options(meta, filterFn) {
	const options = meta.fields
		.filter((field) => field.fieldname && filterFn(field))
		.map((field) => field.fieldname);

	return ["", ...options].join("\n");
}

function _is_value_field(field) {
	return !frappe.model.no_value_type.includes(field.fieldtype);
}

const SUPPORTED_FILTER_OPERATORS = new Set([
	"=",
	"!=",
	"like",
	"not like",
	"in",
	"not in",
	"is",
	">",
	"<",
	">=",
	"<=",
]);

function _render_condition_builders(frm) {
	_render_condition_builder(frm, {
		fieldname: "before_condition",
		htmlFieldname: "before_condition_builder",
		emptyMessage: __("Add filters to match the document before it is updated."),
	});

	_render_condition_builder(frm, {
		fieldname: "apply_on_condition",
		htmlFieldname: "apply_on_condition_builder",
		emptyMessage: __("Add filters to match the document after the trigger is evaluated."),
	});
}

function _render_condition_builder(frm, config) {
	const existingBuilder = frm.__condition_filter_groups?.[config.fieldname];
	if (existingBuilder) {
		existingBuilder.filterButton.off(`.automated-action-${config.fieldname}`);
		existingBuilder.clearButton.off(`.automated-action-${config.fieldname}`);
		existingBuilder.filterButton.popover("dispose");
	}

	frm.__condition_filter_groups = frm.__condition_filter_groups || {};

	const field = frm.get_field(config.htmlFieldname);
	if (!field) {
		return;
	}

	const $wrapper = field.$wrapper;
	$wrapper.empty();

	if (!frm.doc.document_type) {
		$wrapper.html(
			`<div class="text-muted small">${__(
				"Select a Document Type to configure conditions."
			)}</div>`
		);
		_set_condition_value(frm, config.fieldname, []);
		return;
	}

	const builderId = `${config.htmlFieldname}-${frappe.utils.get_random(6)}`;
	$wrapper.html(`
		<div class="automated-action-condition-builder" data-builder="${builderId}">
			<div class="flex align-center justify-between mb-2">
				<div class="text-muted small">${config.emptyMessage}</div>
				<div class="btn-group">
					<button class="btn btn-default btn-sm filter-button" type="button">
						<span class="filter-icon">${frappe.utils.icon("es-line-filter")}</span>
						<span class="button-label hidden-xs">${__("Filter")}</span>
					</button>
					<button class="btn btn-default btn-sm filter-x-button" type="button" title="${__(
						"Clear all filters"
					)}">
						<span class="filter-icon">${frappe.utils.icon("es-small-close")}</span>
					</button>
				</div>
			</div>
			<div class="condition-summary"></div>
		</div>
	`);

	const $builder = $wrapper.find(`[data-builder="${builderId}"]`);
	const filterButton = $builder.find(".filter-button");
	const clearButton = $builder.find(".filter-x-button");
	const initialFilters = _parse_stored_conditions(
		frm.doc.document_type,
		frm.doc[config.fieldname]
	);

	const filterGroup = new frappe.ui.FilterGroup({
		parent: $builder,
		doctype: frm.doc.document_type,
		filter_button: filterButton,
		filter_x_button: clearButton,
		on_change: () => {
			_sync_condition_builder(frm, config, filterGroup, $builder);
		},
	});

	frm.__condition_filter_groups[config.fieldname] = {
		filterButton,
		clearButton,
		filterGroup,
	};

	filterButton.on(`shown.bs.popover.automated-action-${config.fieldname}`, () => {
		_restrict_filter_group_operators(filterGroup);
		if (!filterGroup.__options_bound && filterGroup.wrapper) {
			filterGroup.__options_bound = true;
			filterGroup.wrapper.on("click", ".add-filter", () => {
				setTimeout(() => _restrict_filter_group_operators(filterGroup), 0);
			});
		}
	});

	clearButton.on(`click.automated-action-${config.fieldname}`, () => {
		_sync_condition_builder(frm, config, filterGroup, $builder, []);
		_update_condition_summary(frm, $builder, []);
	});

	frappe.model.with_doctype(frm.doc.document_type, () => {
		if (!initialFilters.length) {
			_update_condition_summary(frm, $builder, []);
			filterGroup.update_filter_button();
			return;
		}

		filterGroup.add_filters(initialFilters).then(() => {
			_restrict_filter_group_operators(filterGroup);
			_sync_condition_builder(
				frm,
				config,
				filterGroup,
				$builder,
				_normalize_filter_values(filterGroup.get_filters())
			);
			filterGroup.update_filter_button();
		});
	});
}

function _sync_condition_builder(frm, config, filterGroup, $builder, filters) {
	const normalizedFilters = filters || _normalize_filter_values(filterGroup.get_filters());
	_set_condition_value(frm, config.fieldname, normalizedFilters);
	_update_condition_summary(frm, $builder, normalizedFilters);
}

function _set_condition_value(frm, fieldname, filters) {
	const serialized = filters.length ? JSON.stringify(filters) : "";
	if (frm.doc[fieldname] !== serialized) {
		frm.set_value(fieldname, serialized);
	}
}

function _parse_stored_conditions(doctype, value) {
	if (!value) {
		return [];
	}

	try {
		const parsed = JSON.parse(value);
		if (!Array.isArray(parsed)) {
			return [];
		}

		return parsed
			.filter((filter) => Array.isArray(filter) && filter.length >= 2)
			.map((filter) => {
				const [fieldname, operatorOrValue, maybeValue] = filter;
				if (filter.length === 2) {
					return [doctype, fieldname, "=", operatorOrValue];
				}
				return [doctype, fieldname, operatorOrValue, maybeValue];
			});
	} catch (error) {
		return [];
	}
}

function _normalize_filter_values(filters) {
	return (filters || [])
		.filter((filter) => Array.isArray(filter) && filter.length >= 4)
		.map(([doctype, fieldname, operator, value]) => [fieldname, operator, value]);
}

function _update_condition_summary(frm, $builder, filters) {
	const $summary = $builder.find(".condition-summary");
	if (!filters.length) {
		$summary.html(`<div class="text-muted small">${__("No conditions set.")}</div>`);
		return;
	}

	frappe.model.with_doctype(frm.doc.document_type, () => {
		const chips = filters
			.map(([fieldname, operator, value]) => {
				const df = frappe.meta.get_docfield(frm.doc.document_type, fieldname);
				const label = df ? df.label : fieldname;
				const displayValue = Array.isArray(value) ? value.join(", ") : `${value ?? ""}`;
				return `
					<span class="inline-flex align-center badge badge-light ellipsis mr-2 mb-2" title="${_escape_html(
						`${label} ${operator} ${displayValue}`.trim()
					)}">
						${_escape_html(label)} ${_escape_html(operator)} ${_escape_html(displayValue)}
					</span>
				`;
			})
			.join("");

		$summary.html(chips);
	});
}

function _escape_html(value) {
	return frappe.utils.escape_html(`${value ?? ""}`);
}

function _restrict_filter_group_operators(filterGroup) {
	if (!filterGroup.wrapper) {
		return;
	}

	filterGroup.wrapper.find(".condition option").each((_, option) => {
		const $option = $(option);
		$option.toggle(SUPPORTED_FILTER_OPERATORS.has($option.val()));
	});

	filterGroup.filters.forEach((filter) => {
		const currentCondition = filter.get_condition();
		if (!SUPPORTED_FILTER_OPERATORS.has(currentCondition)) {
			filter.set_condition("=", true);
		}
	});
}

function _toggle_sections(frm) {
	let trigger = frm.doc.trigger;
	let action = frm.doc.action_type;

	let is_time = trigger === "Based on Time Condition";
	frm.toggle_display("section_time_condition", is_time);

	let has_conditions = ["On Update", "On Create & Update", "On Create"].includes(trigger);
	frm.toggle_display("section_conditions", has_conditions);
	frm.toggle_display("apply_on_condition_builder", has_conditions);

	let has_before = ["On Update", "On Create & Update"].includes(trigger);
	frm.toggle_display("before_condition_builder", has_before);
	frm.toggle_display("before_condition", false);
	frm.toggle_display("apply_on_condition", false);

	frm.toggle_display("section_update_record", action === "Update Record");
	frm.toggle_display("section_python_code", action === "Execute Python Code");
	frm.toggle_display("section_email", action === "Send Email");
	frm.toggle_display("section_create_record", action === "Create Record");
	frm.toggle_display("section_create_todo", action === "Create ToDo");
	frm.toggle_display("section_add_comment", action === "Add Comment");
}
