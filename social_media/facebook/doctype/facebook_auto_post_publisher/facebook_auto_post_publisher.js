frappe.ui.form.on("Facebook Auto Post Publisher", {
	refresh: function(frm) {
		// Add "Publish Now" custom button for non-published posts or drafts
		if (frm.doc.publish_status !== "Published" && !frm.is_new()) {
			frm.add_custom_button(__("Publish Now"), function() {
				frappe.confirm(
					__("Are you sure you want to publish this post to Facebook immediately?"),
					function() {
						frappe.call({
							method: "publish_now",
							doc: frm.doc,
							freeze: true,
							freeze_message: __("Publishing to Facebook..."),
							callback: function(r) {
								frm.reload_doc();
							}
						});
					}
				);
			}).addClass("btn-primary");
		}
	}
});
