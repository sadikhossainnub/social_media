app_name = "social_media"
app_title = "Social Media"
app_publisher = "Prime Technology of Bangladesh"
app_description = "Social media app for frappe whatsapp, facebook, instagram, linadin, X and etc"
app_email = "sayedtkg@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "social_media",
# 		"logo": "/assets/social_media/logo.png",
# 		"title": "Social Media",
# 		"route": "/social_media",
# 		"has_permission": "social_media.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/social_media/css/social_media.css"
app_include_js = [
	"whatsapp/public/whatsapp_bubble_chat.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/social_media/css/social_media.css"
# web_include_js = "/assets/social_media/js/social_media.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "social_media/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "social_media/public/icons.svg"

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
# 	"methods": "social_media.utils.jinja_methods",
# 	"filters": "social_media.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "social_media.install.before_install"
# after_install = "social_media.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "social_media.uninstall.before_uninstall"
# after_uninstall = "social_media.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "social_media.utils.before_app_install"
# after_app_install = "social_media.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "social_media.utils.before_app_uninstall"
# after_app_uninstall = "social_media.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "social_media.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Notification": "social_media.whatsapp.overrides.notification_override.WhatsappNotificationOverride"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"*": {
		"after_insert": [
			"social_media.whatsapp.doctype.whatsapp_notification.whatsapp_notification.trigger_whatsapp_notifications",
			"social_media.facebook.doctype.facebook_notification.facebook_notification.trigger_facebook_notifications"
		],
		"on_update": [
			"social_media.whatsapp.doctype.whatsapp_notification.whatsapp_notification.trigger_whatsapp_notifications",
			"social_media.facebook.doctype.facebook_notification.facebook_notification.trigger_facebook_notifications"
		],
		"on_submit": [
			"social_media.whatsapp.doctype.whatsapp_notification.whatsapp_notification.trigger_whatsapp_notifications",
			"social_media.facebook.doctype.facebook_notification.facebook_notification.trigger_facebook_notifications",
			"social_media.facebook.post.post_from_sales_invoice",
			"social_media.facebook.post.post_from_sales_order"
		],
		"on_cancel": [
			"social_media.whatsapp.doctype.whatsapp_notification.whatsapp_notification.trigger_whatsapp_notifications",
			"social_media.facebook.doctype.facebook_notification.facebook_notification.trigger_facebook_notifications"
		]
	},
	"Sales Invoice": {
		"on_submit": "social_media.facebook.post.post_from_sales_invoice"
	},
	"Sales Order": {
		"on_submit": "social_media.facebook.post.post_from_sales_order"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"social_media.whatsapp.doctype.whatsapp_notification.whatsapp_notification.trigger_daily_whatsapp_notifications",
		"social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher.analyze_post_engagement",
		"social_media.facebook.insights.pull_daily_insights"
	],
	"cron": {
		"*/5 * * * *": [
			"social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher.process_scheduled_posts"
		],
		"* * * * *": [
			"social_media.whatsapp.doctype.scheduled_whatsapp_message.scheduled_whatsapp_message.process_scheduled_whatsapp_messages"
		]
	}
}

# Testing
# -------

# before_tests = "social_media.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "social_media.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "social_media.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["social_media.utils.before_request"]
# after_request = ["social_media.utils.after_request"]

# Job Events
# ----------
# before_job = ["social_media.utils.before_job"]
# after_job = ["social_media.utils.after_job"]

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
# 	"social_media.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

default_log_clearing_doctypes = {
	"Facebook API Log": 30  # days to retain logs
}

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

