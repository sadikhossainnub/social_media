frappe.ui.form.on('Whatsapp Chat', {
    refresh: function (frm) {
        frm.add_custom_button(__('Send WhatsApp'), function () {
            frm.call('send_message').then(r => {
                if (!r.exc) {
                    frappe.show_alert({ message: __('Message Sent!'), indicator: 'green' });
                    frm.trigger('render_chat');
                }
            });
        }, __('Actions'));

        frm.add_custom_button(__('Check Number'), function () {
            frm.call('verify_number').then(r => {
                if (r.message && r.message[0] && r.message[0].exists) {
                    frappe.msgprint(__('This number is on WhatsApp! ✅'));
                } else {
                    frappe.msgprint(__('This number is NOT on WhatsApp or check failed. ❌'));
                }
            });
        }, __('Actions'));

        frm.trigger('render_chat');
    },

    recipient_number: function (frm) {
        frm.trigger('render_chat');
    },

    instance: function (frm) {
        frm.trigger('render_chat');
    },

    render_chat: function (frm) {
        if (!frm.doc.instance || !frm.doc.recipient_number) {
            frm.set_df_property('chat_html', 'options', '<div class="text-muted text-center" style="padding: 20px;">' + __('Select Instance and Enter Number to see chat history') + '</div>');
            return;
        }

        frm.call('load_chat_history').then(r => {
            let messages = r.message || [];
            let html = `
				<style>
					.wa-chat-container {
						background: #e5ddd5;
						padding: 20px;
						border-radius: 8px;
						max-height: 500px;
						overflow-y: auto;
						display: flex;
						flex-direction: column;
						gap: 10px;
						font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
					}
					.wa-msg {
						max-width: 75%;
						padding: 8px 12px;
						border-radius: 7.5px;
						font-size: 14px;
						line-height: 1.4;
						position: relative;
						box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
					}
					.wa-msg-inbound {
						align-self: flex-start;
						background: #ffffff;
						color: #000;
					}
					.wa-msg-outbound {
						align-self: flex-end;
						background: #dcf8c6;
						color: #000;
					}
					.wa-msg-time {
						font-size: 10px;
						color: #888;
						margin-top: 4px;
						text-align: right;
					}
					.wa-chat-input-row {
						margin-top: 15px;
						display: flex;
						gap: 10px;
					}
				</style>
				<div class="wa-chat-container" id="wa-chat-box">
			`;

            if (messages.length === 0) {
                html += `<div class="text-center text-muted" style="padding: 40px;">No message history found.</div>`;
            } else {
                messages.forEach(msg => {
                    let is_outbound = msg.direction === 'Outbound';
                    let time = frappe.datetime.obj_to_user(msg.creation).split(' ')[1];
                    html += `
						<div class="wa-msg ${is_outbound ? 'wa-msg-outbound' : 'wa-msg-inbound'}">
							<div class="wa-msg-body">${msg.message_body || ''}</div>
							<div class="wa-msg-time">${time}</div>
						</div>
					`;
                });
            }

            html += `</div>
				<div class="wa-chat-input-row">
					<input type="text" id="wa-quick-input" class="form-control" placeholder="${__('Type a message...')}" style="border-radius: 20px;">
					<button class="btn btn-primary btn-sm" id="wa-btn-send" style="border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
						<i class="fa fa-paper-plane"></i>
					</button>
				</div>
			`;

            frm.set_df_property('chat_html', 'options', html);

            // Attach events after rendering
            setTimeout(() => {
                const box = document.getElementById('wa-chat-box');
                if (box) box.scrollTop = box.scrollHeight;

                const btn = document.getElementById('wa-btn-send');
                const input = document.getElementById('wa-quick-input');

                if (btn && input) {
                    const send = () => {
                        let text = input.value;
                        if (text) {
                            input.disabled = true;
                            btn.disabled = true;
                            frm.call('send_quick_text', { text: text }).then(r => {
                                if (!r.exc) {
                                    input.value = '';
                                    frm.trigger('render_chat');
                                } else {
                                    input.disabled = false;
                                    btn.disabled = false;
                                }
                            });
                        }
                    };

                    btn.onclick = send;
                    input.onkeypress = (e) => {
                        if (e.which == 13) send();
                    };
                }
            }, 100);
        });
    }
});
