/**
 * WhatsApp Bubble Chat Widget
 * Floating chat interface for quick messaging
 */

class WhatsAppBubbleChat {
    constructor() {
        this.chatOpen = false;
        this.selectedChat = null;
        this.bubbleId = 'whatsapp-bubble-widget';
        this.chatWindowId = 'whatsapp-chat-window';
        this.init();
    }

    init() {
        // Only initialize if user is logged in and has permission
        if (frappe.session.user === 'Guest') return;
        
        // Check if user has WhatsApp access
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Whatsapp Chat',
                fields: ['count(*)'],
                limit_page_length: 1
            },
            callback: (r) => {
                if (!r.exc) {
                    this.createBubble();
                }
            }
        });
    }

    createBubble() {
        // Create bubble HTML
        const bubble = document.createElement('div');
        bubble.id = this.bubbleId;
        bubble.innerHTML = this.getBubbleHTML();
        bubble.style.cssText = this.getBubbleCSS();
        
        document.body.appendChild(bubble);
        this.attachBubbleEvents();
    }

    getBubbleHTML() {
        return `
            <div class="wa-bubble-main" id="wa-bubble-toggle">
                <i class="fa fa-whatsapp"></i>
            </div>
            <div class="wa-bubble-tooltip">WhatsApp Chat</div>
        `;
    }

    getBubbleCSS() {
        return `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        `;
    }

    attachBubbleEvents() {
        const toggle = document.getElementById('wa-bubble-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => this.toggleChat());
            toggle.style.cssText = `
                width: 60px;
                height: 60px;
                background: #25d366;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
                font-size: 28px;
                color: white;
            `;
            
            toggle.addEventListener('mouseenter', function() {
                this.style.boxShadow = '0 4px 16px rgba(0,0,0,0.3)';
                this.style.transform = 'scale(1.1)';
            });
            
            toggle.addEventListener('mouseleave', function() {
                this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
                this.style.transform = 'scale(1)';
            });
        }
    }

    toggleChat() {
        if (this.chatOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    openChat() {
        // Create chat window if not exists
        let chatWindow = document.getElementById(this.chatWindowId);
        if (!chatWindow) {
            chatWindow = document.createElement('div');
            chatWindow.id = this.chatWindowId;
            chatWindow.innerHTML = this.getChatWindowHTML();
            chatWindow.style.cssText = this.getChatWindowCSS();
            document.body.appendChild(chatWindow);
            
            this.attachChatWindowEvents(chatWindow);
            this.loadChatsList();
        }
        
        chatWindow.style.display = 'flex';
        this.chatOpen = true;
        
        // Animate
        chatWindow.style.opacity = '0';
        chatWindow.style.transform = 'translateY(20px)';
        setTimeout(() => {
            chatWindow.style.opacity = '1';
            chatWindow.style.transform = 'translateY(0)';
        }, 10);
    }

    closeChat() {
        const chatWindow = document.getElementById(this.chatWindowId);
        if (chatWindow) {
            chatWindow.style.opacity = '0';
            chatWindow.style.transform = 'translateY(20px)';
            setTimeout(() => {
                chatWindow.style.display = 'none';
            }, 300);
        }
        this.chatOpen = false;
    }

    getChatWindowHTML() {
        return `
            <div class="wa-chat-window-header">
                <div class="wa-chat-window-title">
                    <h4>WhatsApp Chats</h4>
                </div>
                <button class="wa-close-btn" id="wa-close-btn">
                    <i class="fa fa-times"></i>
                </button>
            </div>
            
            <div class="wa-chat-window-list" id="wa-chats-list">
                <div class="wa-loading">
                    <i class="fa fa-spinner fa-spin"></i> Loading chats...
                </div>
            </div>
            
            <div class="wa-chat-window-detail" id="wa-chat-detail" style="display: none;">
                <div class="wa-chat-detail-header">
                    <button class="wa-back-btn" id="wa-back-btn">
                        <i class="fa fa-arrow-left"></i>
                    </button>
                    <div class="wa-contact-info">
                        <h5 id="wa-contact-name">Contact</h5>
                        <small id="wa-contact-number">+1234567890</small>
                    </div>
                </div>
                
                <div class="wa-messages-container" id="wa-messages-container">
                    <!-- Messages will be loaded here -->
                </div>
                
                <div class="wa-message-input-row">
                    <input type="text" id="wa-msg-input" class="wa-msg-input" placeholder="Type a message...">
                    <button class="wa-send-btn" id="wa-send-msg-btn">
                        <i class="fa fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        `;
    }

    getChatWindowCSS() {
        return `
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 380px;
            height: 600px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 40px rgba(0,0,0,0.16);
            z-index: 9998;
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
            
            @media (max-width: 480px) {
                width: 100vw;
                height: 100vh;
                bottom: 0;
                right: 0;
                border-radius: 0;
            }
        `;
    }

    attachChatWindowEvents(chatWindow) {
        const closeBtn = chatWindow.querySelector('#wa-close-btn');
        const backBtn = chatWindow.querySelector('#wa-back-btn');
        const sendBtn = chatWindow.querySelector('#wa-send-msg-btn');
        const msgInput = chatWindow.querySelector('#wa-msg-input');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeChat());
        }
        
        if (backBtn) {
            backBtn.addEventListener('click', () => this.showChatsList());
        }
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (msgInput) {
            msgInput.addEventListener('keypress', (e) => {
                if (e.which === 13) {
                    this.sendMessage();
                }
            });
        }
    }

    loadChatsList() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Whatsapp Chat',
                fields: ['name', 'recipient_number', 'contact_name', 'message', 'status', 'modified'],
                order_by: 'modified desc',
                limit_page_length: 50
            },
            callback: (r) => {
                if (!r.exc && r.message) {
                    this.renderChatsList(r.message);
                }
            }
        });
    }

    renderChatsList(chats) {
        const listContainer = document.getElementById('wa-chats-list');
        if (!listContainer) return;
        
        let html = '';
        
        if (chats.length === 0) {
            html = '<div class="wa-empty-state"><p>No chats yet</p></div>';
        } else {
            chats.forEach(chat => {
                const name = chat.contact_name || chat.recipient_number || 'Unknown';
                const preview = chat.message ? chat.message.substring(0, 40) : 'No message';
                const time = this.formatTime(chat.modified);
                
                html += `
                    <div class="wa-chat-item" data-chat-name="${chat.name}">
                        <div class="wa-chat-avatar">
                            <i class="fa fa-user-circle"></i>
                        </div>
                        <div class="wa-chat-info">
                            <div class="wa-chat-name">${frappe.utils.sanitize_html(name)}</div>
                            <div class="wa-chat-preview">${frappe.utils.sanitize_html(preview)}</div>
                        </div>
                        <div class="wa-chat-time">${time}</div>
                    </div>
                `;
            });
        }
        
        listContainer.innerHTML = html;
        
        // Attach click events
        const items = listContainer.querySelectorAll('.wa-chat-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const chatName = item.getAttribute('data-chat-name');
                this.openChatDetail(chatName);
            });
        });
    }

    openChatDetail(chatName) {
        this.selectedChat = chatName;
        
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Whatsapp Chat',
                name: chatName
            },
            callback: (r) => {
                if (!r.exc) {
                    this.renderChatDetail(r.message);
                }
            }
        });
    }

    renderChatDetail(chat) {
        const contactName = document.getElementById('wa-contact-name');
        const contactNumber = document.getElementById('wa-contact-number');
        const msgContainer = document.getElementById('wa-messages-container');
        const detailDiv = document.getElementById('wa-chat-detail');
        const listDiv = document.querySelector('.wa-chat-window-list');
        
        if (contactName) contactName.textContent = chat.contact_name || chat.recipient_number || 'Contact';
        if (contactNumber) contactNumber.textContent = chat.recipient_number || 'Unknown';
        
        // Load chat history
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Whatsapp Message Log',
                filters: {
                    'instance': chat.instance,
                    'recipient_number': chat.recipient_number
                },
                fields: ['message_body', 'direction', 'status', 'creation'],
                order_by: 'creation asc',
                limit_page_length: 100
            },
            callback: (r) => {
                if (!r.exc && r.message) {
                    let html = '';
                    r.message.forEach(msg => {
                        const isOutbound = msg.direction === 'Outbound';
                        const time = this.formatTime(msg.creation);
                        html += `
                            <div class="wa-msg ${isOutbound ? 'wa-msg-out' : 'wa-msg-in'}">
                                <div class="wa-msg-text">${frappe.utils.sanitize_html(msg.message_body || '')}</div>
                                <div class="wa-msg-time">${time}</div>
                            </div>
                        `;
                    });
                    msgContainer.innerHTML = html;
                    msgContainer.scrollTop = msgContainer.scrollHeight;
                }
            }
        });
        
        if (listDiv && detailDiv) {
            listDiv.style.display = 'none';
            detailDiv.style.display = 'flex';
        }
    }

    showChatsList() {
        const detailDiv = document.getElementById('wa-chat-detail');
        const listDiv = document.querySelector('.wa-chat-window-list');
        
        if (listDiv && detailDiv) {
            detailDiv.style.display = 'none';
            listDiv.style.display = 'block';
        }
        this.selectedChat = null;
    }

    sendMessage() {
        const input = document.getElementById('wa-msg-input');
        const text = input.value.trim();
        
        if (!text || !this.selectedChat) return;
        
        input.disabled = true;
        
        frappe.call({
            method: 'frappe.client.call',
            args: {
                docs: [{
                    doctype: 'Whatsapp Chat',
                    name: this.selectedChat
                }],
                method: 'send_quick_text',
                args: {text: text}
            },
            callback: (r) => {
                input.disabled = false;
                if (!r.exc) {
                    input.value = '';
                    this.openChatDetail(this.selectedChat);
                }
            }
        });
    }

    formatTime(dateString) {
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diff = now - date;
            
            // Less than 1 minute
            if (diff < 60000) return 'now';
            // Less than 1 hour
            if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
            // Less than 1 day
            if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
            // Less than 1 week
            if (diff < 604800000) return Math.floor(diff / 86400000) + 'd ago';
            
            // Format as date
            return date.toLocaleDateString();
        } catch (e) {
            return 'unknown';
        }
    }
}

// Initialize when page is ready
frappe.ready(() => {
    if (!window.whatsappBubble) {
        window.whatsappBubble = new WhatsAppBubbleChat();
    }
});

// CSS Styles
const style = document.createElement('style');
style.textContent = `
    #whatsapp-bubble-widget {
        all: initial;
    }
    
    #whatsapp-chat-window {
        all: revert;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    .wa-chat-window-header {
        background: #25d366;
        color: white;
        padding: 16px;
        border-radius: 12px 12px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-shrink: 0;
    }
    
    .wa-chat-window-title h4 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
    }
    
    .wa-close-btn {
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .wa-close-btn:hover {
        background: rgba(255,255,255,0.2);
        border-radius: 50%;
    }
    
    .wa-chat-window-list {
        flex: 1;
        overflow-y: auto;
        border-right: 1px solid #e5e5e5;
    }
    
    .wa-chat-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        cursor: pointer;
        border-bottom: 1px solid #f0f0f0;
        transition: background 0.2s;
    }
    
    .wa-chat-item:hover {
        background: #f5f5f5;
    }
    
    .wa-chat-avatar {
        width: 48px;
        height: 48px;
        background: #e5e5ea;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        color: #666;
        margin-right: 12px;
        flex-shrink: 0;
    }
    
    .wa-chat-info {
        flex: 1;
        min-width: 0;
    }
    
    .wa-chat-name {
        font-size: 14px;
        font-weight: 500;
        color: #000;
        margin-bottom: 4px;
    }
    
    .wa-chat-preview {
        font-size: 12px;
        color: #999;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .wa-chat-time {
        font-size: 11px;
        color: #999;
        margin-left: 8px;
        flex-shrink: 0;
    }
    
    .wa-empty-state {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: #999;
        font-size: 14px;
    }
    
    .wa-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: #666;
    }
    
    .wa-chat-window-detail {
        display: flex;
        flex-direction: column;
        border-left: 1px solid #e5e5e5;
    }
    
    .wa-chat-detail-header {
        background: #f5f5f5;
        padding: 12px 16px;
        border-bottom: 1px solid #e5e5e5;
        display: flex;
        align-items: center;
        flex-shrink: 0;
    }
    
    .wa-back-btn {
        background: none;
        border: none;
        color: #25d366;
        font-size: 18px;
        cursor: pointer;
        padding: 0;
        margin-right: 12px;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .wa-back-btn:hover {
        background: rgba(37, 211, 102, 0.1);
        border-radius: 50%;
    }
    
    .wa-contact-info {
        flex: 1;
    }
    
    .wa-contact-info h5 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
    }
    
    .wa-contact-info small {
        color: #999;
        font-size: 12px;
    }
    
    .wa-messages-container {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        background: #e5ddd5;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .wa-msg {
        display: flex;
        flex-direction: column;
        max-width: 75%;
        word-wrap: break-word;
    }
    
    .wa-msg-in {
        align-self: flex-start;
    }
    
    .wa-msg-out {
        align-self: flex-end;
    }
    
    .wa-msg-text {
        padding: 8px 12px;
        border-radius: 7.5px;
        font-size: 13px;
        line-height: 1.4;
        word-wrap: break-word;
    }
    
    .wa-msg-in .wa-msg-text {
        background: #ffffff;
        color: #000;
        border-bottom-left-radius: 0;
    }
    
    .wa-msg-out .wa-msg-text {
        background: #dcf8c6;
        color: #000;
        border-bottom-right-radius: 0;
    }
    
    .wa-msg-time {
        font-size: 11px;
        color: #888;
        margin-top: 4px;
        padding: 0 12px;
    }
    
    .wa-msg-in .wa-msg-time {
        text-align: left;
    }
    
    .wa-msg-out .wa-msg-time {
        text-align: right;
    }
    
    .wa-message-input-row {
        display: flex;
        gap: 8px;
        padding: 12px 16px;
        background: #f5f5f5;
        border-top: 1px solid #e5e5e5;
        flex-shrink: 0;
    }
    
    .wa-msg-input {
        flex: 1;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 8px 16px;
        font-size: 13px;
        outline: none;
        font-family: inherit;
    }
    
    .wa-msg-input:focus {
        border-color: #25d366;
        box-shadow: 0 0 0 3px rgba(37, 211, 102, 0.1);
    }
    
    .wa-send-btn {
        background: #25d366;
        color: white;
        border: none;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        font-size: 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
    }
    
    .wa-send-btn:hover {
        background: #20ba5a;
    }
    
    .wa-send-btn:active {
        transform: scale(0.95);
    }
`;
document.head.appendChild(style);
