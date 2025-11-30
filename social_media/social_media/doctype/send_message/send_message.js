frappe.ui.form.on('Send Message', {
	platform: function(frm) {
		// Update recipient placeholder based on platform
		if (frm.doc.platform === 'WhatsApp') {
			frm.set_df_property('recipient', 'description', 'Enter phone number with country code (e.g., +1234567890)');
		} else {
			frm.set_df_property('recipient', 'description', 'Enter User ID for Facebook/Instagram');
		}
	},
	
	refresh: function(frm) {
		// Add custom buttons
		if (frm.doc.status === 'Failed') {
			frm.add_custom_button(__('Retry Send'), function() {
				frappe.call({
					method: 'retry_send',
					doc: frm.doc,
					callback: function(r) {
						if (r.message.success) {
							frappe.msgprint(__('Message retry initiated'));
							frm.reload_doc();
						} else {
							frappe.msgprint(__('Error: ') + r.message.message);
						}
					}
				});
			});
		}
		
		if (frm.doc.status === 'Draft' && !frm.doc.__islocal) {
			frm.add_custom_button(__('Send Now'), function() {
				frappe.call({
					method: 'send_message',
					doc: frm.doc,
					callback: function(r) {
						frappe.msgprint(__('Message sending initiated'));
						frm.reload_doc();
					}
				});
			});
		}
	},
	
	message_type: function(frm) {
		// Show/hide fields based on message type
		frm.toggle_display('media_url', frm.doc.message_type !== 'text');
		frm.toggle_display('template_name', frm.doc.message_type === 'template');
	}
});