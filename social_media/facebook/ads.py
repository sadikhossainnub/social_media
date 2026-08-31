"""
Facebook Ads Management
Full CRUD + sync for Facebook Marketing API:
  Ad Accounts → Campaigns → Ad Sets → Ads
"""

import frappe
import json
from datetime import datetime
from social_media.facebook.graph_client import FacebookGraphClient


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_ads_client(ad_account_id=None):
	"""
	Return a FacebookGraphClient using the Marketing API token stored on
	the Facebook Ad Account doc (or fall back to settings).
	"""
	if ad_account_id:
		token = frappe.db.get_value("Facebook Ad Account", ad_account_id, "access_token")
		if token:
			client = FacebookGraphClient()
			client._access_token = token
			return client
	return FacebookGraphClient()


def _cents_to_currency(cents_str):
	"""Convert Facebook budget (in cents/lowest currency unit) to float."""
	try:
		return float(cents_str) / 100
	except (TypeError, ValueError):
		return 0.0


def _currency_to_cents(amount):
	"""Convert float amount to Facebook budget (cents/lowest currency unit)."""
	try:
		return int(float(amount) * 100)
	except (TypeError, ValueError):
		return 0


# ─── Ad Account Sync ────────────────────────────────────────────────────────

@frappe.whitelist()
def sync_ad_accounts():
	"""
	Sync all Facebook Ad Accounts for the authenticated user.
	Creates or updates Facebook Ad Account records.
	"""
	client = FacebookGraphClient(use_user_token=True)
	result = client.get(
		"/me/adaccounts",
		params={
			"fields": "id,name,account_status,currency,timezone_name,spend_cap,amount_spent,balance"
		}
	)

	if not result or "data" not in result:
		return {"success": False, "error": "Could not fetch ad accounts from Facebook."}

	synced = 0
	for account in result["data"]:
		account_id = account.get("id", "").replace("act_", "")
		facebook_id = account.get("id")  # keep act_ prefix for API calls

		status_code = account.get("account_status", 1)
		status = "Active" if status_code == 1 else "Disabled"

		existing = frappe.db.get_value("Facebook Ad Account", account_id)

		data = {
			"account_id": account_id,
			"account_name": account.get("name", ""),
			"status": status,
			"currency": account.get("currency", ""),
			"timezone": account.get("timezone_name", ""),
			"spend_limit": _cents_to_currency(account.get("spend_cap", 0)),
			"amount_spent": _cents_to_currency(account.get("amount_spent", 0)),
			"balance": _cents_to_currency(account.get("balance", 0)),
			"last_synced": datetime.now(),
		}

		if existing:
			doc = frappe.get_doc("Facebook Ad Account", account_id)
			doc.update(data)
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Facebook Ad Account", **data})
			doc.insert(ignore_permissions=True)

		synced += 1

	frappe.db.commit()
	return {"success": True, "message": f"Synced {synced} Ad Account(s).", "synced": synced}


# ─── Campaign Sync ───────────────────────────────────────────────────────────

@frappe.whitelist()
def sync_campaigns(ad_account_id):
	"""
	Sync campaigns for a given Facebook Ad Account.
	"""
	if not ad_account_id:
		return {"success": False, "error": "ad_account_id is required."}

	client = _get_ads_client(ad_account_id)
	act_id = f"act_{ad_account_id}"

	result = client.get(
		f"/{act_id}/campaigns",
		params={
			"fields": "id,name,objective,status,daily_budget,lifetime_budget,start_time,stop_time,bid_strategy,buying_type,special_ad_categories",
			"limit": 100
		}
	)

	if not result or "data" not in result:
		return {"success": False, "error": "Could not fetch campaigns."}

	synced = 0
	for c in result["data"]:
		campaign_id = c.get("id")
		existing = frappe.db.get_value("Facebook Ad Campaign", campaign_id)

		data = {
			"campaign_id": campaign_id,
			"campaign_name": c.get("name", ""),
			"ad_account": ad_account_id,
			"objective": c.get("objective", ""),
			"status": c.get("status", "Active").capitalize(),
			"daily_budget": _cents_to_currency(c.get("daily_budget", 0)),
			"lifetime_budget": _cents_to_currency(c.get("lifetime_budget", 0)),
			"bid_strategy": c.get("bid_strategy", ""),
			"buying_type": c.get("buying_type", "AUCTION"),
			"last_synced": datetime.now(),
		}

		# special_ad_categories comes as a list
		special_cats = c.get("special_ad_categories", [])
		data["special_ad_categories"] = special_cats[0] if special_cats else "NONE"

		if existing:
			doc = frappe.get_doc("Facebook Ad Campaign", campaign_id)
			doc.update(data)
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Facebook Ad Campaign", **data})
			doc.insert(ignore_permissions=True)

		synced += 1

	frappe.db.commit()
	return {"success": True, "message": f"Synced {synced} campaign(s).", "synced": synced}


# ─── Ad Set Sync ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def sync_ad_sets(campaign_id):
	"""Sync ad sets for a given campaign."""
	if not campaign_id:
		return {"success": False, "error": "campaign_id is required."}

	campaign_doc = frappe.get_doc("Facebook Ad Campaign", campaign_id)
	client = _get_ads_client(campaign_doc.ad_account)

	result = client.get(
		f"/{campaign_id}/adsets",
		params={
			"fields": "id,name,status,daily_budget,lifetime_budget,billing_event,optimization_goal,targeting,start_time,end_time",
			"limit": 100
		}
	)

	if not result or "data" not in result:
		return {"success": False, "error": "Could not fetch ad sets."}

	synced = 0
	for s in result["data"]:
		adset_id = s.get("id")
		existing = frappe.db.get_value("Facebook Ad Set", adset_id)

		targeting = s.get("targeting", {})
		targeting_summary = _build_targeting_summary(targeting)

		data = {
			"adset_id": adset_id,
			"adset_name": s.get("name", ""),
			"campaign": campaign_id,
			"ad_account": campaign_doc.ad_account,
			"status": s.get("status", "Active").capitalize(),
			"daily_budget": _cents_to_currency(s.get("daily_budget", 0)),
			"lifetime_budget": _cents_to_currency(s.get("lifetime_budget", 0)),
			"billing_event": s.get("billing_event", ""),
			"optimization_goal": s.get("optimization_goal", ""),
			"targeting_summary": targeting_summary,
			"targeting_json": json.dumps(targeting),
			"last_synced": datetime.now(),
		}

		if existing:
			doc = frappe.get_doc("Facebook Ad Set", adset_id)
			doc.update(data)
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Facebook Ad Set", **data})
			doc.insert(ignore_permissions=True)

		synced += 1

	frappe.db.commit()
	return {"success": True, "message": f"Synced {synced} ad set(s).", "synced": synced}


# ─── Ads Sync ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def sync_ads(adset_id):
	"""Sync individual ads for a given ad set."""
	if not adset_id:
		return {"success": False, "error": "adset_id is required."}

	adset_doc = frappe.get_doc("Facebook Ad Set", adset_id)
	client = _get_ads_client(adset_doc.ad_account)

	result = client.get(
		f"/{adset_id}/ads",
		params={
			"fields": "id,name,status,creative{id,title,body,object_url,image_url,video_id,call_to_action_type}",
			"limit": 100
		}
	)

	if not result or "data" not in result:
		return {"success": False, "error": "Could not fetch ads."}

	synced = 0
	for a in result["data"]:
		ad_id = a.get("id")
		creative = a.get("creative", {})
		existing = frappe.db.get_value("Facebook Ad", ad_id)

		cta = creative.get("call_to_action_type", "")

		data = {
			"ad_id": ad_id,
			"ad_name": a.get("name", ""),
			"ad_set": adset_id,
			"campaign": adset_doc.campaign,
			"ad_account": adset_doc.ad_account,
			"status": a.get("status", "Active").capitalize(),
			"headline": creative.get("title", ""),
			"body_text": creative.get("body", ""),
			"destination_url": creative.get("object_url", ""),
			"image_url": creative.get("image_url", ""),
			"call_to_action": cta,
			"last_synced": datetime.now(),
		}

		if existing:
			doc = frappe.get_doc("Facebook Ad", ad_id)
			doc.update(data)
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Facebook Ad", **data})
			doc.insert(ignore_permissions=True)

		synced += 1

	frappe.db.commit()
	return {"success": True, "message": f"Synced {synced} ad(s).", "synced": synced}


# ─── Insights Sync ──────────────────────────────────────────────────────────

@frappe.whitelist()
def sync_campaign_insights(campaign_id, date_preset="last_30d"):
	"""Fetch and store campaign performance insights."""
	if not campaign_id:
		return {"success": False, "error": "campaign_id is required."}

	campaign_doc = frappe.get_doc("Facebook Ad Campaign", campaign_id)
	client = _get_ads_client(campaign_doc.ad_account)

	result = client.get(
		f"/{campaign_id}/insights",
		params={
			"fields": "impressions,clicks,spend,reach,cpc,cpm,ctr,frequency",
			"date_preset": date_preset
		}
	)

	if not result or "data" not in result or not result["data"]:
		return {"success": False, "error": "No insights data."}

	insights = result["data"][0]
	campaign_doc.impressions = int(insights.get("impressions", 0) or 0)
	campaign_doc.clicks = int(insights.get("clicks", 0) or 0)
	campaign_doc.spend = float(insights.get("spend", 0) or 0)
	campaign_doc.reach = int(insights.get("reach", 0) or 0)
	campaign_doc.cpc = float(insights.get("cpc", 0) or 0)
	campaign_doc.cpm = float(insights.get("cpm", 0) or 0)
	campaign_doc.ctr = float(insights.get("ctr", 0) or 0)
	campaign_doc.frequency = float(insights.get("frequency", 0) or 0)
	campaign_doc.raw_insights = json.dumps(insights)
	campaign_doc.last_synced = datetime.now()
	campaign_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "message": "Campaign insights synced."}


@frappe.whitelist()
def sync_ad_set_insights(adset_id, date_preset="last_30d"):
	"""Fetch and store ad set performance insights."""
	if not adset_id:
		return {"success": False, "error": "adset_id is required."}

	adset_doc = frappe.get_doc("Facebook Ad Set", adset_id)
	client = _get_ads_client(adset_doc.ad_account)

	result = client.get(
		f"/{adset_id}/insights",
		params={
			"fields": "impressions,clicks,spend,reach,cpc,ctr,frequency",
			"date_preset": date_preset
		}
	)

	if not result or "data" not in result or not result["data"]:
		return {"success": False, "error": "No insights data."}

	insights = result["data"][0]
	adset_doc.impressions = int(insights.get("impressions", 0) or 0)
	adset_doc.clicks = int(insights.get("clicks", 0) or 0)
	adset_doc.spend = float(insights.get("spend", 0) or 0)
	adset_doc.reach = int(insights.get("reach", 0) or 0)
	adset_doc.cpc = float(insights.get("cpc", 0) or 0)
	adset_doc.ctr = float(insights.get("ctr", 0) or 0)
	adset_doc.frequency = float(insights.get("frequency", 0) or 0)
	adset_doc.raw_insights = json.dumps(insights)
	adset_doc.last_synced = datetime.now()
	adset_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "message": "Ad set insights synced."}


@frappe.whitelist()
def sync_ad_insights(ad_id, date_preset="last_30d"):
	"""Fetch and store individual ad performance insights."""
	if not ad_id:
		return {"success": False, "error": "ad_id is required."}

	ad_doc = frappe.get_doc("Facebook Ad", ad_id)
	client = _get_ads_client(ad_doc.ad_account)

	result = client.get(
		f"/{ad_id}/insights",
		params={
			"fields": "impressions,clicks,spend,reach,cpc,ctr,actions",
			"date_preset": date_preset
		}
	)

	if not result or "data" not in result or not result["data"]:
		return {"success": False, "error": "No insights data."}

	insights = result["data"][0]
	ad_doc.impressions = int(insights.get("impressions", 0) or 0)
	ad_doc.clicks = int(insights.get("clicks", 0) or 0)
	ad_doc.spend = float(insights.get("spend", 0) or 0)
	ad_doc.reach = int(insights.get("reach", 0) or 0)
	ad_doc.cpc = float(insights.get("cpc", 0) or 0)
	ad_doc.ctr = float(insights.get("ctr", 0) or 0)

	# Count conversions from actions array
	actions = insights.get("actions", [])
	conversions = sum(
		int(a.get("value", 0))
		for a in actions
		if a.get("action_type") in ("lead", "offsite_conversion", "purchase")
	)
	ad_doc.conversions = conversions
	if conversions > 0 and ad_doc.spend:
		ad_doc.cost_per_conversion = ad_doc.spend / conversions

	ad_doc.raw_insights = json.dumps(insights)
	ad_doc.last_synced = datetime.now()
	ad_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "message": "Ad insights synced."}


# ─── Campaign CRUD ───────────────────────────────────────────────────────────

@frappe.whitelist()
def create_campaign(ad_account_id, campaign_name, objective, daily_budget=None,
					lifetime_budget=None, start_date=None, end_date=None,
					bid_strategy="LOWEST_COST_WITHOUT_CAP", special_ad_categories=None):
	"""
	Create a new Facebook Ad Campaign via Marketing API and save it locally.

	Args:
		ad_account_id: Facebook Ad Account ID (without act_ prefix)
		campaign_name: Name for the campaign
		objective: Campaign objective (e.g. TRAFFIC, LEADS, CONVERSIONS)
		daily_budget: Daily budget in account currency
		lifetime_budget: Lifetime budget in account currency
		start_date: Start date YYYY-MM-DD
		end_date: End date YYYY-MM-DD
		bid_strategy: Bid strategy
		special_ad_categories: Special ad category list (e.g. ["NONE"])

	Returns:
		dict: {success, campaign_id, message}
	"""
	if not ad_account_id or not campaign_name or not objective:
		return {"success": False, "error": "ad_account_id, campaign_name, and objective are required."}

	client = _get_ads_client(ad_account_id)
	act_id = f"act_{ad_account_id}"

	payload = {
		"name": campaign_name,
		"objective": objective,
		"status": "PAUSED",  # always start paused for safety
		"bid_strategy": bid_strategy,
		"special_ad_categories": special_ad_categories or ["NONE"],
	}

	if daily_budget:
		payload["daily_budget"] = _currency_to_cents(daily_budget)
	if lifetime_budget:
		payload["lifetime_budget"] = _currency_to_cents(lifetime_budget)

	result = client.post(f"/{act_id}/campaigns", data=payload)

	if not result or "id" not in result:
		error_msg = result.get("error", {}).get("message", "Unknown error") if result else "API call failed"
		frappe.log_error(f"Facebook campaign creation failed: {result}", "Facebook Ads")
		return {"success": False, "error": error_msg}

	campaign_id = result["id"]

	# Save to ERPNext
	doc = frappe.get_doc({
		"doctype": "Facebook Ad Campaign",
		"campaign_id": campaign_id,
		"campaign_name": campaign_name,
		"ad_account": ad_account_id,
		"objective": objective,
		"status": "Paused",
		"daily_budget": daily_budget or 0,
		"lifetime_budget": lifetime_budget or 0,
		"bid_strategy": bid_strategy,
		"special_ad_categories": special_ad_categories[0] if special_ad_categories else "NONE",
		"start_date": start_date,
		"end_date": end_date,
		"last_synced": datetime.now(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"campaign_id": campaign_id,
		"erpnext_id": doc.name,
		"message": f"Campaign '{campaign_name}' created successfully (status: Paused)."
	}


@frappe.whitelist()
def update_campaign(campaign_id, campaign_name=None, daily_budget=None,
					lifetime_budget=None, bid_strategy=None):
	"""Update an existing campaign on Facebook and locally."""
	if not campaign_id:
		return {"success": False, "error": "campaign_id is required."}

	campaign_doc = frappe.get_doc("Facebook Ad Campaign", campaign_id)
	client = _get_ads_client(campaign_doc.ad_account)

	payload = {}
	if campaign_name:
		payload["name"] = campaign_name
	if daily_budget:
		payload["daily_budget"] = _currency_to_cents(daily_budget)
	if lifetime_budget:
		payload["lifetime_budget"] = _currency_to_cents(lifetime_budget)
	if bid_strategy:
		payload["bid_strategy"] = bid_strategy

	if not payload:
		return {"success": False, "error": "Nothing to update."}

	result = client.post(f"/{campaign_id}", data=payload)

	if not result or not result.get("success"):
		return {"success": False, "error": "Facebook API update failed."}

	# Update locally
	if campaign_name:
		campaign_doc.campaign_name = campaign_name
	if daily_budget:
		campaign_doc.daily_budget = daily_budget
	if lifetime_budget:
		campaign_doc.lifetime_budget = lifetime_budget
	if bid_strategy:
		campaign_doc.bid_strategy = bid_strategy
	campaign_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "message": "Campaign updated successfully."}


@frappe.whitelist()
def pause_campaign(campaign_id):
	"""Pause a Facebook campaign."""
	return _set_campaign_status(campaign_id, "PAUSED", "Paused")


@frappe.whitelist()
def activate_campaign(campaign_id):
	"""Activate a Facebook campaign."""
	return _set_campaign_status(campaign_id, "ACTIVE", "Active")


def _set_campaign_status(campaign_id, fb_status, local_status):
	"""Internal helper to change campaign status."""
	if not campaign_id:
		return {"success": False, "error": "campaign_id is required."}

	campaign_doc = frappe.get_doc("Facebook Ad Campaign", campaign_id)
	client = _get_ads_client(campaign_doc.ad_account)

	result = client.post(f"/{campaign_id}", data={"status": fb_status})

	if result and result.get("success"):
		campaign_doc.status = local_status
		campaign_doc.save(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True, "message": f"Campaign {local_status.lower()} successfully."}
	else:
		return {"success": False, "error": f"Failed to {local_status.lower()} campaign on Facebook."}


# ─── Ad Set CRUD ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_ad_set(campaign_id, adset_name, optimization_goal, billing_event,
				  daily_budget=None, lifetime_budget=None,
				  targeting=None, start_time=None, end_time=None):
	"""
	Create a new Ad Set under a campaign.

	Args:
		campaign_id: ERPNext Facebook Ad Campaign name (= Facebook campaign ID)
		adset_name: Ad Set name
		optimization_goal: e.g. LINK_CLICKS, LEAD_GENERATION, REACH
		billing_event: e.g. IMPRESSIONS, LINK_CLICKS
		daily_budget: Daily budget
		lifetime_budget: Lifetime budget
		targeting: dict with Facebook targeting spec
		start_time: ISO datetime string
		end_time: ISO datetime string
	"""
	if not campaign_id or not adset_name:
		return {"success": False, "error": "campaign_id and adset_name are required."}

	campaign_doc = frappe.get_doc("Facebook Ad Campaign", campaign_id)
	client = _get_ads_client(campaign_doc.ad_account)
	act_id = f"act_{campaign_doc.ad_account}"

	payload = {
		"name": adset_name,
		"campaign_id": campaign_id,
		"optimization_goal": optimization_goal,
		"billing_event": billing_event,
		"status": "PAUSED",
		"targeting": targeting or {"geo_locations": {"countries": ["BD"]}},
	}

	if daily_budget:
		payload["daily_budget"] = _currency_to_cents(daily_budget)
	if lifetime_budget:
		payload["lifetime_budget"] = _currency_to_cents(lifetime_budget)
	if start_time:
		payload["start_time"] = start_time
	if end_time:
		payload["end_time"] = end_time

	result = client.post(f"/{act_id}/adsets", data=payload)

	if not result or "id" not in result:
		error_msg = result.get("error", {}).get("message", "Unknown error") if result else "API call failed"
		return {"success": False, "error": error_msg}

	adset_id = result["id"]
	targeting_summary = _build_targeting_summary(targeting or {})

	doc = frappe.get_doc({
		"doctype": "Facebook Ad Set",
		"adset_id": adset_id,
		"adset_name": adset_name,
		"campaign": campaign_id,
		"ad_account": campaign_doc.ad_account,
		"status": "Paused",
		"optimization_goal": optimization_goal,
		"billing_event": billing_event,
		"daily_budget": daily_budget or 0,
		"lifetime_budget": lifetime_budget or 0,
		"targeting_summary": targeting_summary,
		"targeting_json": json.dumps(targeting or {}),
		"start_time": start_time,
		"end_time": end_time,
		"last_synced": datetime.now(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"adset_id": adset_id,
		"erpnext_id": doc.name,
		"message": f"Ad Set '{adset_name}' created successfully."
	}


@frappe.whitelist()
def pause_ad_set(adset_id):
	"""Pause an ad set."""
	return _set_adset_status(adset_id, "PAUSED", "Paused")


@frappe.whitelist()
def activate_ad_set(adset_id):
	"""Activate an ad set."""
	return _set_adset_status(adset_id, "ACTIVE", "Active")


def _set_adset_status(adset_id, fb_status, local_status):
	if not adset_id:
		return {"success": False, "error": "adset_id is required."}
	adset_doc = frappe.get_doc("Facebook Ad Set", adset_id)
	client = _get_ads_client(adset_doc.ad_account)
	result = client.post(f"/{adset_id}", data={"status": fb_status})
	if result and result.get("success"):
		adset_doc.status = local_status
		adset_doc.save(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True, "message": f"Ad Set {local_status.lower()}."}
	return {"success": False, "error": f"Failed to {local_status.lower()} ad set."}


# ─── Ad CRUD ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_ad(adset_id, ad_name, headline, body_text, destination_url,
			  image_url=None, call_to_action="LEARN_MORE", creative_type="Image"):
	"""
	Create a new Ad under an ad set.

	Steps:
	  1. Upload/reference the creative
	  2. Create the ad creative
	  3. Create the ad
	"""
	if not adset_id or not ad_name:
		return {"success": False, "error": "adset_id and ad_name are required."}

	adset_doc = frappe.get_doc("Facebook Ad Set", adset_id)
	client = _get_ads_client(adset_doc.ad_account)
	act_id = f"act_{adset_doc.ad_account}"

	# Step 1: Create ad creative
	creative_payload = {
		"name": f"{ad_name} - Creative",
		"object_story_spec": {
			"page_id": frappe.db.get_value("Facebook Ad Account", adset_doc.ad_account, "page") or
					   frappe.get_single("Facebook Settings").page_id,
			"link_data": {
				"message": body_text,
				"link": destination_url,
				"name": headline,
				"call_to_action": {"type": call_to_action},
			}
		}
	}

	if image_url:
		creative_payload["object_story_spec"]["link_data"]["picture"] = image_url

	creative_result = client.post(f"/{act_id}/adcreatives", data=creative_payload)

	if not creative_result or "id" not in creative_result:
		error_msg = creative_result.get("error", {}).get("message", "Creative creation failed") if creative_result else "API call failed"
		return {"success": False, "error": f"Creative creation failed: {error_msg}"}

	creative_id = creative_result["id"]

	# Step 2: Create the ad
	ad_payload = {
		"name": ad_name,
		"adset_id": adset_id,
		"creative": {"creative_id": creative_id},
		"status": "PAUSED",
	}

	ad_result = client.post(f"/{act_id}/ads", data=ad_payload)

	if not ad_result or "id" not in ad_result:
		error_msg = ad_result.get("error", {}).get("message", "Ad creation failed") if ad_result else "API call failed"
		return {"success": False, "error": f"Ad creation failed: {error_msg}"}

	ad_id = ad_result["id"]

	# Save to ERPNext
	doc = frappe.get_doc({
		"doctype": "Facebook Ad",
		"ad_id": ad_id,
		"ad_name": ad_name,
		"ad_set": adset_id,
		"campaign": adset_doc.campaign,
		"ad_account": adset_doc.ad_account,
		"status": "Paused",
		"creative_type": creative_type,
		"headline": headline,
		"body_text": body_text,
		"destination_url": destination_url,
		"image_url": image_url or "",
		"call_to_action": call_to_action,
		"last_synced": datetime.now(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"ad_id": ad_id,
		"erpnext_id": doc.name,
		"message": f"Ad '{ad_name}' created successfully."
	}


@frappe.whitelist()
def pause_ad(ad_id):
	"""Pause an ad."""
	return _set_ad_status(ad_id, "PAUSED", "Paused")


@frappe.whitelist()
def activate_ad(ad_id):
	"""Activate an ad."""
	return _set_ad_status(ad_id, "ACTIVE", "Active")


def _set_ad_status(ad_id, fb_status, local_status):
	if not ad_id:
		return {"success": False, "error": "ad_id is required."}
	ad_doc = frappe.get_doc("Facebook Ad", ad_id)
	client = _get_ads_client(ad_doc.ad_account)
	result = client.post(f"/{ad_id}", data={"status": fb_status})
	if result and result.get("success"):
		ad_doc.status = local_status
		ad_doc.save(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True, "message": f"Ad {local_status.lower()}."}
	return {"success": False, "error": f"Failed to {local_status.lower()} ad."}


# ─── Dashboard API ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_ads_dashboard_data(ad_account_id=None):
	"""
	Return aggregated data for the Ads Dashboard page.
	"""
	filters = {}
	if ad_account_id:
		filters["ad_account"] = ad_account_id

	campaigns = frappe.get_all(
		"Facebook Ad Campaign",
		filters=filters,
		fields=["campaign_id", "campaign_name", "status", "objective",
				"spend", "impressions", "clicks", "ctr", "cpc",
				"daily_budget", "lifetime_budget", "last_synced"]
	)

	total_spend = sum(c.spend or 0 for c in campaigns)
	total_impressions = sum(c.impressions or 0 for c in campaigns)
	total_clicks = sum(c.clicks or 0 for c in campaigns)
	avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0

	ad_accounts = frappe.get_all(
		"Facebook Ad Account",
		fields=["account_id", "account_name", "status", "currency",
				"amount_spent", "balance", "spend_limit"]
	)

	return {
		"success": True,
		"summary": {
			"total_spend": round(total_spend, 2),
			"total_impressions": total_impressions,
			"total_clicks": total_clicks,
			"avg_ctr": round(avg_ctr, 2),
			"campaign_count": len(campaigns),
		},
		"campaigns": campaigns,
		"ad_accounts": ad_accounts,
	}


# ─── Scheduler Jobs ───────────────────────────────────────────────────────────

def sync_all_ad_accounts():
	"""
	Scheduler task: Sync all ad accounts and their campaigns every 6 hours.
	"""
	settings = frappe.get_single("Facebook Settings")
	if not settings.is_connected or not getattr(settings, "enable_ads_management", False):
		return

	try:
		result = sync_ad_accounts()
		if result.get("success"):
			# Sync campaigns for each account
			accounts = frappe.get_all("Facebook Ad Account", filters={"status": "Active"}, pluck="account_id")
			for account_id in accounts:
				try:
					sync_campaigns(account_id)
				except Exception as e:
					frappe.log_error(f"Campaign sync error for {account_id}: {e}", "Facebook Ads Scheduler")
	except Exception as e:
		frappe.log_error(f"Ad account sync error: {e}", "Facebook Ads Scheduler")


def sync_campaign_insights_daily():
	"""
	Scheduler task: Sync insights for all active campaigns daily.
	"""
	settings = frappe.get_single("Facebook Settings")
	if not settings.is_connected or not getattr(settings, "enable_ads_management", False):
		return

	campaigns = frappe.get_all(
		"Facebook Ad Campaign",
		filters={"status": "Active"},
		pluck="name"
	)

	for campaign_id in campaigns:
		try:
			sync_campaign_insights(campaign_id)
		except Exception as e:
			frappe.log_error(f"Insights sync error for {campaign_id}: {e}", "Facebook Ads Scheduler")


# ─── Utilities ────────────────────────────────────────────────────────────────

def _build_targeting_summary(targeting):
	"""Build a human-readable targeting summary from a Facebook targeting dict."""
	if not targeting:
		return ""

	parts = []

	# Age
	age_min = targeting.get("age_min")
	age_max = targeting.get("age_max")
	if age_min or age_max:
		parts.append(f"Age {age_min or '13'}-{age_max or '65+'}")

	# Gender
	genders = targeting.get("genders", [])
	if genders:
		gender_map = {1: "Male", 2: "Female"}
		parts.append(", ".join(gender_map.get(g, str(g)) for g in genders))

	# Locations
	geo = targeting.get("geo_locations", {})
	countries = [c.get("name", c.get("country_code", "")) for c in geo.get("countries", [])] if isinstance(geo.get("countries"), list) else geo.get("countries", [])
	cities = [c.get("name", "") for c in geo.get("cities", [])]
	locations = countries + cities
	if locations:
		parts.append(f"Location: {', '.join(str(l) for l in locations[:3])}")

	# Interests
	interests = targeting.get("flexible_spec", [{}])
	interest_names = []
	for spec in interests:
		for category in ["interests", "behaviors", "work_positions"]:
			for item in spec.get(category, []):
				if isinstance(item, dict):
					interest_names.append(item.get("name", ""))
				else:
					interest_names.append(str(item))
	if interest_names:
		parts.append(f"Interests: {', '.join(interest_names[:3])}")

	return " | ".join(filter(None, parts)) or "Custom targeting"
