frappe.ui.form.on("Scheduled Whatsapp Message", {
	refresh(frm) {
		toggle_recipient_fields(frm);
		toggle_schedule_fields(frm);
		add_send_now_button(frm);
	},
	recipient_type(frm) {
		toggle_recipient_fields(frm);
		if (frm.doc.recipient_type === "Employee" && !frm.doc.recipient_fields) {
			frm.set_value("recipient_fields", "cell_number");
		}
	},
	trigger_frequency(frm) {
		toggle_schedule_fields(frm);
	},
});

function toggle_recipient_fields(frm) {
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "employee", frm.doc.name).reqd = frm.doc.recipient_type === "Employee";
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "customer", frm.doc.name).reqd = frm.doc.recipient_type === "Customer";
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "recipient_fields", frm.doc.name).reqd = ["Employee", "Customer"].includes(frm.doc.recipient_type);
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "whatsapp_number", frm.doc.name).reqd = frm.doc.recipient_type === "Custom Number";
	frm.refresh_fields(["employee", "customer", "recipient_fields", "whatsapp_number"]);
}

function toggle_schedule_fields(frm) {
	const frequency = frm.doc.trigger_frequency || "Daily";
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "weekday", frm.doc.name).reqd = frequency === "Weekly";
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "day_of_month", frm.doc.name).reqd = ["Monthly", "Yearly"].includes(frequency);
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "month_of_year", frm.doc.name).reqd = frequency === "Yearly";
	frappe.meta.get_docfield("Scheduled Whatsapp Message", "specific_date", frm.doc.name).reqd = frequency === "Specific Date";
	frm.refresh_fields(["weekday", "day_of_month", "month_of_year", "specific_date"]);
}

function add_send_now_button(frm) {
	if (frm.is_new()) return;

	frm.add_custom_button(__("Send Now (Test)"), () => {
		frappe.call({
			method: "social_media.whatsapp.doctype.scheduled_whatsapp_message.scheduled_whatsapp_message.send_now",
			args: {
				name: frm.doc.name,
			},
			freeze: true,
			freeze_message: __("Sending test WhatsApp message..."),
			callback: (r) => {
				const count = (r.message?.recipient_numbers || []).length;
				frappe.show_alert({
					message: __("Message queued for {0} recipient(s)", [count || 0]),
					indicator: "green",
				});
			},
		});
	});
}
