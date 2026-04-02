app_name = "b2r_custom"
app_title = "b2r_custom"
app_publisher = "M R Tech Solutions"
app_description = "This is a custom ERP for B2R"
app_email = "mrts.products@gmail.com"
app_license = "mit"

after_install = "b2r_custom.install.after_install"

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [["module", "=", "b2r_custom"]],
	},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "b2r_custom",
# 		"logo": "/assets/b2r_custom/logo.png",
# 		"title": "b2r_custom",
# 		"route": "/b2r_custom",
# 		"has_permission": "b2r_custom.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/b2r_custom/css/b2r_custom.css"
# app_include_js = "/assets/b2r_custom/js/b2r_custom.js"

# include js, css files in header of web template
# web_include_css = "/assets/b2r_custom/css/b2r_custom.css"
# web_include_js = "/assets/b2r_custom/js/b2r_custom.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "b2r_custom/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Item": "public/js/item.js",
	"Warehouse": "public/js/warehouse.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "b2r_custom/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "b2r_custom.utils.jinja_methods",
# 	"filters": "b2r_custom.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "b2r_custom.install.before_install"
# after_install = "b2r_custom.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "b2r_custom.uninstall.before_uninstall"
# after_uninstall = "b2r_custom.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "b2r_custom.utils.before_app_install"
# after_app_install = "b2r_custom.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "b2r_custom.utils.before_app_uninstall"
# after_app_uninstall = "b2r_custom.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "b2r_custom.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Receipt": {
		"validate": "b2r_custom.api.validate_inbound_capacity",
		"on_submit": "b2r_custom.api.handle_stock_impact_submit",
		"on_cancel": "b2r_custom.api.handle_stock_impact_cancel",
	},
	"Stock Entry": {
		"validate": "b2r_custom.api.validate_inbound_capacity",
		"on_submit": "b2r_custom.api.handle_stock_impact_submit",
		"on_cancel": "b2r_custom.api.handle_stock_impact_cancel",
	},
	"Delivery Note": {
		"on_submit": "b2r_custom.api.handle_stock_impact_submit",
		"on_cancel": "b2r_custom.api.handle_stock_impact_cancel",
	},
	"Sales Invoice": {
		"validate": "b2r_custom.api.validate_sales_invoice",
		"on_submit": "b2r_custom.api.handle_sales_invoice_submit",
		"on_cancel": "b2r_custom.api.handle_sales_invoice_cancel",
	},
	"Payment Entry": {
		"on_submit": "b2r_custom.api.reserve_stock_on_payment",
		"on_cancel": "b2r_custom.api.release_stock_on_payment_cancel",
	},
	"Employee Checkin": {
		"validate": "b2r_custom.api.validate_employee_checkin",
	},
	"Attendance": {
		"validate": "b2r_custom.api.validate_attendance",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"b2r_custom.api.send_vendor_aging_reminders",
	],
}

# Testing
# -------

# before_tests = "b2r_custom.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "b2r_custom.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "b2r_custom.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "b2r_custom.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["b2r_custom.utils.before_request"]
# after_request = ["b2r_custom.utils.after_request"]

# Job Events
# ----------
# before_job = ["b2r_custom.utils.before_job"]
# after_job = ["b2r_custom.utils.after_job"]

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
# 	"b2r_custom.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

