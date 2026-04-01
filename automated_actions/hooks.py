app_name = "automated_actions"
app_title = "Automated Actions"
app_publisher = "Ali Raxa"
app_description = "No-code workflow automation for the Frappe Framework"
app_email = "ar.frappe.dev@gmail.com"
app_license = "MIT"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "automated_actions",
# 		"logo": "/assets/automated_actions/images/automated_actions-logo.svg",
# 		"title": "Automated Actions",
# 		"route": "/automated_actions",
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/automated_actions/css/automated_actions.css"
# app_include_js = "/assets/automated_actions/js/automated_actions.js"

# include js, css files in header of web template
# web_include_css = "/assets/automated_actions/css/automated_actions.css"
# web_include_js = "/assets/automated_actions/js/automated_actions.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "automated_actions/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {
# 	"doctype": "automated_actions/api/doctype.js",
# }


# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "automated_actions/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": [
# 		"automated_actions.api.jinja_helpers.automated_actions_barcode",
# 		"automated_actions.api.jinja_helpers.automated_actions_barcode_uri",
# 		"automated_actions.api.jinja_helpers.automated_actions_qrcode",
# 		"automated_actions.api.jinja_helpers.automated_actions_qrcode_uri",
# 		"automated_actions.api.jinja_helpers.automated_actions_item_barcode",
# 	],
# }

# Installation
# ------------

# before_install = "automated_actions.install.before_install"
# after_install = "automated_actions.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "automated_actions.uninstall.before_uninstall"
# after_uninstall = "automated_actions.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "automated_actions.utils.before_app_install"
# after_app_install = "automated_actions.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "automated_actions.uninstall.before_uninstall"
# after_app_uninstall = "automated_actions.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "automated_actions.notifications.get_notification_config"

# Permissions
# -----------

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"POS Invoice": "automated_actions.x_pos.overrides.pos_invoice.CustomPOSInvoice",
# 	"POS Invoice Merge Log": "automated_actions.x_pos.overrides.pos_invoice_merge_log.CustomPOSInvoiceMergeLog",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"*": {
		"after_insert": "automated_actions.handlers.handle_after_insert",
		"on_update": "automated_actions.handlers.handle_on_update",
		"on_trash": "automated_actions.handlers.handle_on_trash",
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"0 */4 * * *": [
			"automated_actions.scheduler.process_time_based_rules",
		],
	},
}

# Testing
# -------

# before_tests = "automated_actions.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "automated_actions.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "automated_actions.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["automated_actions.utils.before_request"]
# after_request = ["automated_actions.utils.after_request"]

# Job Events
# ----------
# before_job = ["automated_actions.utils.before_job"]
# after_job = ["automated_actions.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"automated_actions.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


# Website Route Rules
# -------------------
# Serve the Automated Actions SPA for deep links under /automated_actions

# website_route_rules = [
# 	{"from_route": "/automated_actions", "to_route": "automated_actions"},
# 	{"from_route": "/automated_actions/<path:app_path>", "to_route": "automated_actions"},
# ]
