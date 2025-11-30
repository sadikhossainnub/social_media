frappe.ui.form.on('Instagram Settings', {
	test_connection: function(frm) {
		frappe.call({
			method: 'test_connection',
			doc: frm.doc,
			btn: frm.fields_dict.test_connection.$input,
			callback: function(r) {
				if (r.message && r.message.success) {
					frappe.show_alert({
						message: __('Instagram connection test successful!'),
						indicator: 'green'
					});
				}
			}
		});
	}
});