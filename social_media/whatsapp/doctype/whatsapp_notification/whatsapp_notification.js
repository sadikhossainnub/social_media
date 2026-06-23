frappe.ui.form.on('Whatsapp Notification', {
    refresh: function (frm) {
        setup_fieldname_select(frm);
    },
    document_type: function (frm) {
        setup_fieldname_select(frm);

        if (frm.doc.document_type) {
            frappe.model.with_doctype(frm.doc.document_type, function () {
                let fields = frappe.get_meta(frm.doc.document_type).fields
                    .filter(df => ["Data", "Phone", "Select", "Link"].includes(df.fieldtype))
                    .map(df => df.fieldname);

                frm.set_df_property('send_to', 'description',
                    "Available fields: <b>" + fields.join(", ") + "</b> or enter a fixed number.");
            });
        }
    }
});

function setup_fieldname_select(frm) {
    if (!frm.doc.document_type) return;

    frappe.model.with_doctype(frm.doc.document_type, function () {
        let get_select_options = function (df) {
            return {
                value: df.fieldname,
                label: df.fieldname + " (" + __(df.label, null, df.parent) + ")",
            };
        };

        let fields = frappe.get_doc("DocType", frm.doc.document_type).fields;

        let get_date_change_options = function () {
            let date_options = $.map(fields, function (d) {
                return d.fieldtype == "Date" || d.fieldtype == "Datetime"
                    ? get_select_options(d)
                    : null;
            });
            return date_options.concat([
                { value: "creation", label: `creation (${__("Created On")})` },
                { value: "modified", label: `modified (${__("Last Modified Date")})` },
            ]);
        };

        frm.set_df_property("date_changed", "options", [""].concat(get_date_change_options()));
    });
}
