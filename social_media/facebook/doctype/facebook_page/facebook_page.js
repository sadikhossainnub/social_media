// Copyright (c) 2026, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facebook Page', {
	onload: function(frm) {
		if (frm.is_new()) {
			fetch_and_populate_settings(frm);
		}
	},

	refresh: function(frm) {
		// Add a button to fetch details from settings
		frm.add_custom_button(__('Fetch from Facebook Settings'), function() {
			fetch_and_populate_settings(frm, true);
		}, __('Actions'));
	}
});

function fetch_and_populate_settings(frm, manual = false) {
	frappe.call({
		method: 'social_media.facebook.doctype.facebook_page.facebook_page.get_facebook_settings_credentials',
		callback: function(r) {
			if (r.message) {
				const creds = r.message;
				let updated = false;

				if (creds.page_id && frm.doc.page_id !== creds.page_id) {
					frm.set_value('page_id', creds.page_id);
					updated = true;
				}
				if (creds.page_name && frm.doc.page_name !== creds.page_name) {
					frm.set_value('page_name', creds.page_name);
					updated = true;
				}
				if (creds.access_token && frm.doc.access_token !== creds.access_token) {
					frm.set_value('access_token', creds.access_token);
					updated = true;
				}
				if (creds.app_id && frm.doc.app_id !== creds.app_id) {
					frm.set_value('app_id', creds.app_id);
					updated = true;
				}
				if (creds.app_secret && frm.doc.app_secret !== creds.app_secret) {
					frm.set_value('app_secret', creds.app_secret);
					updated = true;
				}

				if (updated && manual) {
					frappe.show_alert({
						message: __('Successfully fetched credentials from Facebook Settings'),
						indicator: 'green'
					});
				} else if (!updated && manual) {
					frappe.show_alert({
						message: __('Facebook Page credentials are already up-to-date with Facebook Settings'),
						indicator: 'info'
					});
				}
			}
		}
	});
}
