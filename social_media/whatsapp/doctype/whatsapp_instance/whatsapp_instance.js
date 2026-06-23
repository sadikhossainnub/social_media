frappe.ui.form.on('Whatsapp Instance', {
    refresh: function (frm) {
        if (!frm.doc.__islocal) {
            // ── Primary Action: Connect / Refresh QR ──
            frm.add_custom_button(__('Connect / Refresh QR'), function () {
                frappe.call({
                    method: 'connect',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Connecting to WhatsApp...'),
                    callback: function () {
                        frm.reload_doc();
                    }
                });
            });

            // ── Refresh Status ──
            frm.add_custom_button(__('Refresh Status'), function () {
                frappe.call({
                    method: 'refresh_status',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Checking connection...'),
                    callback: function () {
                        frm.reload_doc();
                    }
                });
            });

            // ── Actions Group ──
            frm.add_custom_button(__('Set Webhook'), function () {
                frappe.call({
                    method: 'configure_webhook',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Configuring webhook...'),
                    callback: function () {
                        frappe.show_alert({ message: __('Webhook configured'), indicator: 'green' });
                    }
                });
            }, __('Actions'));

            frm.add_custom_button(__('Test Message'), function () {
                frappe.prompt([
                    {
                        label: __('Phone Number'),
                        fieldtype: 'Data',
                        fieldname: 'number',
                        reqd: 1,
                        description: __('With country code (e.g., 8801XXXXXXXXX)')
                    },
                    {
                        label: __('Message'),
                        fieldtype: 'Small Text',
                        fieldname: 'message',
                        reqd: 1,
                        default: 'Hello from Frappe! 🚀'
                    }
                ], (values) => {
                    frappe.call({
                        method: 'send_test_message',
                        doc: frm.doc,
                        args: {
                            number: values.number,
                            message: values.message
                        },
                        freeze: true,
                        freeze_message: __('Sending message...'),
                        callback: function () {
                            frappe.show_alert({ message: __('Message Sent ✓'), indicator: 'green' });
                        }
                    });
                }, __('Send Test Message'), __('Send'));
            }, __('Actions'));

            frm.add_custom_button(__('Restart Instance'), function () {
                frappe.confirm(__('Restart this WhatsApp instance?'), function () {
                    frappe.call({
                        method: 'restart',
                        doc: frm.doc,
                        freeze: true,
                        freeze_message: __('Restarting instance...'),
                        callback: function () {
                            frm.reload_doc();
                        }
                    });
                });
            }, __('Actions'));

            frm.add_custom_button(__('Logout'), function () {
                frappe.confirm(__('Logout will disconnect this WhatsApp session. Continue?'), function () {
                    frappe.call({
                        method: 'logout',
                        doc: frm.doc,
                        freeze: true,
                        callback: function () {
                            frm.reload_doc();
                        }
                    });
                });
            }, __('Danger'));

            frm.add_custom_button(__('Delete from API'), function () {
                frappe.confirm(__('This will permanently delete the instance from Evolution API. This cannot be undone. Continue?'), function () {
                    frappe.call({
                        method: 'delete_remote',
                        doc: frm.doc,
                        freeze: true,
                        callback: function () {
                            frappe.msgprint(__('Remote instance deleted. You can now delete this document.'));
                            frm.reload_doc();
                        }
                    });
                });
            }, __('Danger'));
        }

        // ── QR Code Display ──
        if (frm.doc.qr_code_base64) {
            let src = frm.doc.qr_code_base64;
            if (!src.startsWith('data:image')) {
                src = 'data:image/png;base64,' + src;
            }

            frm.set_df_property('qr_code_image', 'options',
                `<div style="text-align:center; padding: 20px;">
                    <div style="background: white; display: inline-block; padding: 15px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);">
                        <img src="${src}" style="width: 250px; height: 250px;" />
                    </div>
                    <br><small style="color: #888; margin-top: 10px; display: block;">Scan with WhatsApp to connect</small>
                </div>`
            );
        } else {
            frm.set_df_property('qr_code_image', 'options',
                `<div style="text-align:center; padding: 40px; background: #f8f9fa; border-radius: 8px; color: #666;">
                    <div style="font-size: 40px; margin-bottom: 10px;">📱</div>
                    <div>Click <b>Connect / Refresh QR</b> to get the QR code</div>
                </div>`
            );
        }

        // ── Status indicator color ──
        if (frm.doc.status === 'Connected') {
            frm.dashboard.set_headline_alert(
                '<div style="display:flex;align-items:center;gap:8px;"><span style="width:10px;height:10px;background:#36b37e;border-radius:50%;display:inline-block;"></span> Connected to WhatsApp</div>',
                'green'
            );
        } else if (frm.doc.status === 'Connecting') {
            frm.dashboard.set_headline_alert(
                '<div style="display:flex;align-items:center;gap:8px;"><span style="width:10px;height:10px;background:#ff9f43;border-radius:50%;display:inline-block;"></span> Waiting for QR scan...</div>',
                'orange'
            );
        }
    }
});
