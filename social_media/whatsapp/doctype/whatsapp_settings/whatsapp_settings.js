frappe.ui.form.on('Whatsapp Settings', {
	onload: function(frm) {
		// Generate webhook URL on load
		frm.set_value('webhook_url', get_webhook_url());
		
		// Render copy button
		render_copy_button(frm);
	},

	after_save: function(frm) {
		// Regenerate URL after save
		frm.set_value('webhook_url', get_webhook_url());
		render_copy_button(frm);
	},

	refresh: function(frm) {
		// Render copy button on refresh
		render_copy_button(frm);

		// Add custom button for quick copy
		frm.add_custom_button(__('Copy Webhook URL'), function() {
			copy_to_clipboard(frm.doc.webhook_url);
		}).addClass('btn-primary');
	}
});

function get_webhook_url() {
	// Get the base URL from frappe
	const base_url = frappe.urllib.get_base_url();
	
	// Use Frappe's /api/method/ endpoint format
	// This is the only format that works without custom routing
	// and handles authentication properly
	return `${base_url}/api/method/social_media.whatsapp.api.webhook`;
}

function render_copy_button(frm) {
	// Clear existing content
	frm.set_df_property('webhook_copy_button', 'options', '');

	const webhook_url = frm.doc.webhook_url;
	if (!webhook_url) {
		frm.set_df_property('webhook_copy_button', 'options', 
			'<div class="alert alert-warning"><i class="fa fa-warning"></i> Unable to generate webhook URL</div>'
		);
		return;
	}

	// Create HTML with copy button
	const html = `
		<div class="webhook-button-container" style="margin-top: 10px;">
			<div style="display: flex; gap: 10px; align-items: center;">
				<input type="text" id="webhook_url_input" value="${webhook_url}" 
					readonly style="flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; font-size: 12px;">
				<button type="button" class="btn btn-primary" id="copy_webhook_btn" style="white-space: nowrap;">
					<i class="fa fa-copy"></i> Copy
				</button>
			</div>
			<p style="margin-top: 10px; color: #666; font-size: 12px;">
				<strong>ব্যবহার করুন:</strong> এই URL টি Evolution API এর webhook configuration এ paste করুন।
			</p>
			<p style="color: #666; font-size: 12px;">
				<strong>Webhook Events:</strong> messages.upsert, send.message, connection.update, qrcode.updated
			</p>
		</div>
	`;

	frm.set_df_property('webhook_copy_button', 'options', html);
	frm.refresh_field('webhook_copy_button');

	// Add click handler to copy button
	setTimeout(() => {
		const copy_btn = document.getElementById('copy_webhook_btn');
		if (copy_btn) {
			copy_btn.addEventListener('click', function() {
				copy_to_clipboard(webhook_url);
			});
		}
	}, 100);
}

function copy_to_clipboard(text) {
	if (!text) {
		frappe.msgprint({
			message: 'কোনো URL নেই কপি করার জন্য',
			title: 'Error',
			indicator: 'red'
		});
		return;
	}

	// Modern approach using Clipboard API
	if (navigator.clipboard && navigator.clipboard.writeText) {
		navigator.clipboard.writeText(text).then(function() {
			frappe.show_alert({
				message: __('Webhook URL copied to clipboard!'),
				indicator: 'green'
			});
		}).catch(function(err) {
			// Fallback to old method
			fallback_copy(text);
		});
	} else {
		// Fallback for older browsers
		fallback_copy(text);
	}
}

function fallback_copy(text) {
	// Create temporary textarea
	const textarea = document.createElement('textarea');
	textarea.value = text;
	document.body.appendChild(textarea);
	
	try {
		textarea.select();
		document.execCommand('copy');
		frappe.show_alert({
			message: __('Webhook URL copied to clipboard!'),
			indicator: 'green'
		});
	} catch (e) {
		frappe.msgprint({
			message: 'Failed to copy URL. Please copy manually: ' + text,
			title: 'Copy Failed',
			indicator: 'red'
		});
	} finally {
		document.body.removeChild(textarea);
	}
}
