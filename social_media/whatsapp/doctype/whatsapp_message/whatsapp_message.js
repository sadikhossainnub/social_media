frappe.ui.form.on('WhatsApp Message', {
	refresh: function(frm) {
		// Auto set timestamp when form loads for new documents
		if (frm.doc.__islocal && !frm.doc.timestamp) {
			frm.set_value('timestamp', frappe.datetime.now_datetime());
		}
	}
});