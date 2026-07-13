"""
Facebook Analytics and Insights
Scheduler tasks and helper methods for pulling page-level/post-level stats.
"""

import frappe
from datetime import datetime, timedelta
from social_media.facebook.graph_client import FacebookGraphClient


def pull_daily_insights():
	"""
	Scheduler job (daily) that fetches insights from Facebook Graph API
	for all active, connected Facebook Pages.
	"""
	# Get all active Facebook Pages
	active_pages = frappe.get_all("Facebook Page", filters={"status": "Active"}, fields=["name", "page_id"])
	
	for page in active_pages:
		try:
			# Pull daily stats
			pull_page_insights_for_date(page.name)
		except Exception as e:
			frappe.log_error(
				f"Failed to pull daily insights for Facebook Page {page.name}: {str(e)}",
				"Facebook Insights Scheduler"
			)


def pull_page_insights_for_date(page_id, since_date=None, until_date=None):
	"""
	Fetch insights for page_id for a given period and save to Facebook Insight.
	"""
	client = FacebookGraphClient(page_id=page_id)
	
	# Default range: last 3 days to catch delayed data
	if not since_date:
		since_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
	if not until_date:
		until_date = datetime.now().strftime("%Y-%m-%d")
		
	# Common metrics to pull
	metrics = [
		"page_impressions",
		"page_engaged_users",
		"page_fans",
		"page_fan_adds",
		"page_views_total",
		"page_post_engagements"
	]
	
	res = client.get_page_insights(page_id=page_id, metrics=metrics, period="day", since=since_date, until=until_date)
	if not res or "data" not in res:
		return
		
	# Group metrics by date
	# Structure of res: {"data": [{"name": "metric_name", "period": "day", "values": [{"value": 10, "end_time": "2026-07-12T07:00:00+0000"}]}]}
	for metric in res["data"]:
		metric_name = metric.get("name")
		period = metric.get("period")
		
		for entry in metric.get("values", []):
			value = entry.get("value", 0)
			# end_time represents the date of metrics collection
			end_time_str = entry.get("end_time")
			if not end_time_str:
				continue
				
			# Extract YYYY-MM-DD
			date_str = end_time_str.split("T")[0]
			
			# Save to database
			# Unique identifier: page + date + metric_name
			insight_name = frappe.db.get_value(
				"Facebook Insight",
				{"page": page_id, "date": date_str, "metric_name": metric_name},
				"name"
			)
			
			if insight_name:
				doc = frappe.get_doc("Facebook Insight", insight_name)
				doc.metric_value = float(value)
				doc.raw_data = frappe.as_json(entry)
				doc.save(ignore_permissions=True)
			else:
				doc = frappe.get_doc({
					"doctype": "Facebook Insight",
					"page": page_id,
					"date": date_str,
					"metric_name": metric_name,
					"metric_value": float(value),
					"period": period,
					"raw_data": frappe.as_json(entry)
				})
				doc.insert(ignore_permissions=True)


def get_best_posting_time(page_id):
	"""
	Analyze page insights to suggest the best date/time to post.
	Looks at engagement levels (page_post_engagements) grouped by hour/day.
	"""
	# Fallback if no detailed hour metrics exist: return a standard time
	default_best_time = "18:00:00" # 6 PM local
	
	try:
		# Query local insights for the last 30 days
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=30)
		
		insights = frappe.get_all(
			"Facebook Insight",
			filters={
				"page": page_id,
				"metric_name": "page_post_engagements",
				"date": ["between", [start_date, end_date]]
			},
			fields=["date", "metric_value"]
		)
		
		if not insights:
			return default_best_time
			
		# Let's see what days are best
		# Day-of-week engagement dict
		day_engagement = {i: 0.0 for i in range(7)}
		for ins in insights:
			dt = datetime.strptime(str(ins.date), "%Y-%m-%d").date()
			day_engagement[dt.weekday()] += ins.metric_value
			
		best_day_idx = max(day_engagement, key=day_engagement.get)
		days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		
		# Now check for hours - if we have detailed post engagement times
		# In this basic implementation, we default to 5 PM or 6 PM on the best weekday
		# Let's say 17:00 or 18:00
		return {
			"best_day": days[best_day_idx],
			"best_time": "17:00:00",
			"score": day_engagement[best_day_idx]
		}
	except Exception:
		return {
			"best_day": "Wednesday",
			"best_time": default_best_time,
			"score": 0
		}


def calculate_engagement_rate(post_id):
	"""
	Compute the engagement rate of a specific post.
	Engagement Rate = (Reactions + Comments + Shares) / Impressions * 100
	"""
	try:
		post_doc = frappe.get_doc("Facebook Post", post_id)
		
		# If impressions or reach is zero/none, fallback to total fans
		client = FacebookGraphClient(page_id=post_doc.page)
		insights = client.get_post_insights(post_doc.post_id)
		
		impressions = 0
		if insights and "data" in insights:
			for metric in insights["data"]:
				if metric.get("name") == "post_impressions":
					impressions = metric.get("values", [{}])[0].get("value", 0)
					break
					
		total_interactions = post_doc.like_count + post_doc.comment_count + post_doc.share_count
		
		if impressions > 0:
			rate = (total_interactions / impressions) * 100
		else:
			# Fallback: total page followers/fans
			page_fans = frappe.db.get_value("Facebook Page", post_doc.page, "fan_count") or 1000
			rate = (total_interactions / page_fans) * 100
			
		return round(rate, 2)
	except Exception:
		return 0.0
