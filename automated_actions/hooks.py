app_name = "automated_actions"
app_title = "Automated Actions"
app_publisher = "Ali Raxa"
app_description = "No-code workflow automation for the Frappe Framework"
app_email = "ar.frappe.dev@gmail.com"
app_license = "MIT"

# Document Events
# ---------------
# Intercept all document events and dispatch to matching Automated Action rules.

doc_events = {
	"*": {
		"after_insert": "automated_actions.handlers.handle_after_insert",
		"on_update": "automated_actions.handlers.handle_on_update",
		"on_trash": "automated_actions.handlers.handle_on_trash",
	}
}

# Scheduled Tasks
# ---------------
# Process time-based Automated Action triggers every 4 hours.

scheduler_events = {
	"cron": {
		"0 */4 * * *": [
			"automated_actions.scheduler.process_time_based_rules",
		],
	},
}
