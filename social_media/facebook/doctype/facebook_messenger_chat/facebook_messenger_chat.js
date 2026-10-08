// Copyright (c) 2026, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facebook Messenger Chat', {
    refresh: function(frm) {
        // Add "View Conversation" button
        if (frm.doc.conversation_id) {
            frm.add_custom_button(__('View Full Conversation'), function() {
                show_conversation_dialog(frm.doc.conversation_id, frm.doc.sender_name);
            }, __('Actions'));
        }
    }
});


// ── Conversation List View ───────────────────────────────────────
frappe.listview_settings['Facebook Messenger Chat'] = {
    hide_name_column: true,
    
    onload: function(listview) {
        // Add "Conversation View" button to list view
        listview.page.add_inner_button(__('Conversation View'), function() {
            show_conversations_page();
        });

        // Add "Sync Old Messages" button
        listview.page.add_inner_button(__('Sync Old Messages'), function() {
            frappe.confirm(
                __('This will fetch all old messages from your Facebook Page inbox. Continue?'),
                function() {
                    frappe.call({
                        method: 'social_media.facebook.messenger.enqueue_sync_old_messages',
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint(__('Sync has been queued in the background. You will be notified when it completes.'));
                            }
                        }
                    });
                }
            );
        });
    },

    get_indicator: function(doc) {
        if (doc.direction === 'Incoming') {
            return [__('Incoming'), 'blue', 'direction,=,Incoming'];
        } else {
            return [__('Outgoing'), 'green', 'direction,=,Outgoing'];
        }
    }
};


// ── Conversation Dialog ──────────────────────────────────────────

function show_conversation_dialog(conversation_id, title) {
    frappe.call({
        method: 'social_media.facebook.messenger.get_conversation_thread',
        args: { conversation_id: conversation_id },
        callback: function(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint(__('No messages found in this conversation.'));
                return;
            }

            let messages = r.message;
            let chat_html = build_chat_html(messages);

            let d = new frappe.ui.Dialog({
                title: __('Conversation: {0}', [title || conversation_id.substring(0, 15) + '...']),
                size: 'large',
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'chat_view',
                        options: chat_html
                    }
                ]
            });

            d.show();
            
            // Scroll to bottom of chat
            setTimeout(function() {
                let chat_container = d.$wrapper.find('.chat-conversation-container');
                if (chat_container.length) {
                    chat_container.scrollTop(chat_container[0].scrollHeight);
                }
            }, 200);
        }
    });
}


function build_chat_html(messages) {
    let html = `
        <style>
            .chat-conversation-container {
                max-height: 500px;
                overflow-y: auto;
                padding: 15px;
                background: var(--bg-color);
                border-radius: 8px;
                border: 1px solid var(--border-color);
            }
            .chat-bubble {
                max-width: 75%;
                padding: 10px 14px;
                margin-bottom: 8px;
                border-radius: 12px;
                font-size: 13px;
                line-height: 1.5;
                word-wrap: break-word;
                position: relative;
            }
            .chat-bubble.incoming {
                background: var(--control-bg);
                color: var(--text-color);
                margin-right: auto;
                border-bottom-left-radius: 4px;
            }
            .chat-bubble.outgoing {
                background: var(--primary);
                color: white;
                margin-left: auto;
                border-bottom-right-radius: 4px;
            }
            .chat-bubble .chat-sender {
                font-size: 11px;
                font-weight: 600;
                margin-bottom: 3px;
                opacity: 0.8;
            }
            .chat-bubble .chat-time {
                font-size: 10px;
                opacity: 0.6;
                margin-top: 4px;
                text-align: right;
            }
            .chat-bubble.outgoing .chat-time {
                color: rgba(255,255,255,0.7);
            }
            .chat-date-separator {
                text-align: center;
                margin: 12px 0;
                font-size: 11px;
                color: var(--text-muted);
            }
            .chat-date-separator span {
                background: var(--bg-color);
                padding: 3px 12px;
                border-radius: 10px;
                border: 1px solid var(--border-color);
            }
            .chat-row {
                display: flex;
                margin-bottom: 4px;
            }
            .chat-row.incoming { justify-content: flex-start; }
            .chat-row.outgoing { justify-content: flex-end; }
        </style>
        <div class="chat-conversation-container">
    `;

    let last_date = '';
    messages.forEach(function(msg) {
        // Date separator
        let msg_date = msg.timestamp ? frappe.datetime.str_to_user(msg.timestamp).split(' ')[0] : '';
        if (msg_date && msg_date !== last_date) {
            html += `<div class="chat-date-separator"><span>${msg_date}</span></div>`;
            last_date = msg_date;
        }

        let direction_class = (msg.direction === 'Outgoing') ? 'outgoing' : 'incoming';
        let time_str = msg.timestamp ? frappe.datetime.str_to_user(msg.timestamp).split(' ').slice(1).join(' ') : '';
        let message_text = frappe.utils.xss_sanitise(msg.message || '(no text)');

        html += `
            <div class="chat-row ${direction_class}">
                <div class="chat-bubble ${direction_class}">
                    <div class="chat-sender">${frappe.utils.xss_sanitise(msg.sender_name || 'Unknown')}</div>
                    <div class="chat-text">${message_text}</div>
                    <div class="chat-time">${time_str}</div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}


// ── Conversations Page ───────────────────────────────────────────

function show_conversations_page() {
    frappe.call({
        method: 'social_media.facebook.messenger.get_all_conversations',
        callback: function(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint(__('No conversations found.'));
                return;
            }

            let conversations = r.message;
            let list_html = build_conversations_list_html(conversations);

            let d = new frappe.ui.Dialog({
                title: __('Facebook Messenger Conversations'),
                size: 'extra-large',
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'conversations_list',
                        options: list_html
                    }
                ]
            });

            d.show();

            // Bind click events
            d.$wrapper.find('.conversation-item').on('click', function() {
                let conv_id = $(this).data('conversation-id');
                let conv_name = $(this).data('sender-name');
                d.hide();
                show_conversation_dialog(conv_id, conv_name);
            });
        }
    });
}


function build_conversations_list_html(conversations) {
    let html = `
        <style>
            .conversations-list {
                max-height: 600px;
                overflow-y: auto;
            }
            .conversation-item {
                display: flex;
                align-items: center;
                padding: 12px 15px;
                border-bottom: 1px solid var(--border-color);
                cursor: pointer;
                transition: background 0.15s;
            }
            .conversation-item:hover {
                background: var(--control-bg);
            }
            .conv-avatar {
                width: 42px;
                height: 42px;
                border-radius: 50%;
                background: var(--primary);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                font-size: 16px;
                margin-right: 12px;
                flex-shrink: 0;
            }
            .conv-info {
                flex: 1;
                min-width: 0;
            }
            .conv-name {
                font-weight: 600;
                font-size: 14px;
                color: var(--text-color);
                margin-bottom: 2px;
            }
            .conv-last-msg {
                font-size: 12px;
                color: var(--text-muted);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .conv-meta {
                text-align: right;
                flex-shrink: 0;
                margin-left: 10px;
            }
            .conv-time {
                font-size: 11px;
                color: var(--text-muted);
            }
            .conv-count {
                display: inline-block;
                background: var(--primary);
                color: white;
                font-size: 11px;
                padding: 1px 7px;
                border-radius: 10px;
                margin-top: 4px;
            }
        </style>
        <div class="conversations-list">
    `;

    conversations.forEach(function(conv) {
        let initial = (conv.participant_name || '?')[0].toUpperCase();
        let last_msg = frappe.utils.xss_sanitise((conv.last_message || '').substring(0, 60));
        let time_str = conv.last_timestamp ? frappe.datetime.prettyDate(conv.last_timestamp) : '';

        html += `
            <div class="conversation-item" 
                 data-conversation-id="${frappe.utils.xss_sanitise(conv.conversation_id)}"
                 data-sender-name="${frappe.utils.xss_sanitise(conv.participant_name || '')}">
                <div class="conv-avatar">${initial}</div>
                <div class="conv-info">
                    <div class="conv-name">${frappe.utils.xss_sanitise(conv.participant_name || 'Unknown')}</div>
                    <div class="conv-last-msg">${last_msg || '(no text)'}</div>
                </div>
                <div class="conv-meta">
                    <div class="conv-time">${time_str}</div>
                    <div class="conv-count">${conv.message_count}</div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}
