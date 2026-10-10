import { defineStore } from 'pinia';
import { callApi } from '../api/client';
import { realtimeSocket } from '../api/socket';

export const useInboxStore = defineStore('inbox', {
  state: () => ({
    conversations: [],
    selectedChat: null,
    activeMessages: [],
    loadingConversations: false,
    loadingMessages: false,
    sendingMsg: false,
    generatingAiReply: false,
    filterTab: 'all', // 'all', 'unread', 'complaints'
    selectedChannel: 'all', // 'all', 'facebook', 'instagram', 'whatsapp'
    searchQuery: '',
    isCustomerTyping: false,
    typingTimer: null,
    showCustomerInfoPanel: true,
  }),

  getters: {
    filteredConversations: (state) => {
      let result = state.conversations;

      if (state.selectedChannel && state.selectedChannel !== 'all') {
        const chan = state.selectedChannel.toLowerCase();
        result = result.filter(c => (c.platform || 'facebook').toLowerCase() === chan);
      }

      if (state.filterTab === 'unread') {
        result = result.filter(c => c.unread_count > 0);
      } else if (state.filterTab === 'complaints') {
        result = result.filter(c => c.is_complaint);
      }

      if (state.searchQuery.trim()) {
        const q = state.searchQuery.toLowerCase();
        result = result.filter(c => 
          (c.sender_name && c.sender_name.toLowerCase().includes(q)) ||
          (c.last_message && c.last_message.toLowerCase().includes(q)) ||
          (c.sender_id && c.sender_id.toLowerCase().includes(q))
        );
      }

      return result;
    },

    totalUnreadCount: (state) => {
      return state.conversations.reduce((acc, c) => acc + (c.unread_count || 0), 0);
    },

    channelCounts: (state) => {
      const counts = { all: state.conversations.length, facebook: 0, instagram: 0, whatsapp: 0 };
      state.conversations.forEach(c => {
        const p = (c.platform || 'facebook').toLowerCase();
        if (counts[p] !== undefined) {
          counts[p]++;
        }
      });
      return counts;
    }
  },

  actions: {
    initRealtimeListeners() {
      // Listen for incoming message
      realtimeSocket.on('fb_new_message', (msg) => {
        this.handleIncomingRealtimeMessage(msg);
      });

      // Listen for thread updates
      realtimeSocket.on('fb_thread_update', (data) => {
        this.handleThreadUpdate(data);
      });

      // Listen for customer typing indicator
      realtimeSocket.on('fb_typing_indicator', (data) => {
        if (this.selectedChat && (data.conversation_id === this.selectedChat.conversation_id || data.sender_psid === this.selectedChat.sender_id)) {
          this.isCustomerTyping = !!data.is_typing;
          if (this.typingTimer) clearTimeout(this.typingTimer);
          if (data.is_typing) {
            this.typingTimer = setTimeout(() => {
              this.isCustomerTyping = false;
            }, 5000);
          }
        }
      });
    },

    async fetchConversations(pageId = null) {
      this.loadingConversations = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_conversations', params);
      this.loadingConversations = false;

      if (res.success && Array.isArray(res.data)) {
        this.conversations = res.data;
        // If current selectedChat is active, update reference
        if (this.selectedChat) {
          const match = this.conversations.find(c => c.conversation_id === this.selectedChat.conversation_id || c.sender_id === this.selectedChat.sender_id);
          if (match) {
            this.selectedChat = { ...this.selectedChat, ...match };
          }
        }
      }
    },

    async selectConversation(chat) {
      this.selectedChat = chat;
      this.activeMessages = [];
      this.loadingMessages = true;

      const res = await callApi('get_messages', {
        conversation_id: chat.conversation_id,
        sender_id: chat.sender_id
      });
      this.loadingMessages = false;

      if (res.success && Array.isArray(res.data)) {
        this.activeMessages = res.data;
        // Reset unread count locally
        const conv = this.conversations.find(c => c.conversation_id === chat.conversation_id);
        if (conv) {
          conv.unread_count = 0;
        }
      }
    },

    async sendMessage(text, pageId) {
      if (!text.trim() || !this.selectedChat) return false;

      this.sendingMsg = true;
      const targetPage = pageId || this.selectedChat.page;

      const res = await callApi('send_message', {
        recipient_id: this.selectedChat.sender_id,
        message: text,
        page: targetPage,
        platform: this.selectedChat.platform || 'Facebook'
      });
      this.sendingMsg = false;

      if (res.success) {
        // Append outgoing message locally
        const newMsg = {
          name: res.data?.name || `temp_${Date.now()}`,
          platform: this.selectedChat.platform || 'Facebook',
          sender_id: this.selectedChat.sender_id,
          sender_name: 'You',
          direction: 'Outgoing',
          timestamp: new Date().toISOString(),
          message: text,
          is_read: 1
        };
        this.activeMessages.push(newMsg);

        // Update conversation summary
        const conv = this.conversations.find(c => c.conversation_id === this.selectedChat.conversation_id || c.sender_id === this.selectedChat.sender_id);
        if (conv) {
          conv.last_message = text;
          conv.last_message_direction = 'Outgoing';
          conv.last_message_time = new Date().toISOString();
        }
        return true;
      }
      return false;
    },

    async generateAiReply() {
      if (!this.selectedChat || this.activeMessages.length === 0) return null;

      const lastIncoming = [...this.activeMessages].reverse().find(m => m.direction === 'Incoming');
      const textToReply = lastIncoming ? lastIncoming.message : this.selectedChat.last_message;

      this.generatingAiReply = true;
      const res = await callApi('generate_ai_chat_reply', {
        message: textToReply,
        customer_name: this.selectedChat.sender_name
      });
      this.generatingAiReply = false;

      if (res.success && res.data) {
        return typeof res.data === 'string' ? res.data : (res.data.reply || res.data.message);
      }
      return null;
    },

    async flagAsComplaint(priority = 'High') {
      if (!this.selectedChat) return false;

      const res = await callApi('flag_chat_as_complaint', {
        conversation_id: this.selectedChat.conversation_id,
        priority
      });

      if (res.success) {
        this.selectedChat.is_complaint = 1;
        this.selectedChat.priority = priority;
        const conv = this.conversations.find(c => c.conversation_id === this.selectedChat.conversation_id);
        if (conv) {
          conv.is_complaint = 1;
          conv.priority = priority;
        }
        return true;
      }
      return false;
    },

    async assignAgent(assignedAgent) {
      if (!this.selectedChat) return false;

      const res = await callApi('assign_conversation', {
        sender_id: this.selectedChat.sender_id,
        assigned_agent: assignedAgent
      });

      if (res.success) {
        this.selectedChat.assigned_agent = assignedAgent;
        const conv = this.conversations.find(c => c.conversation_id === this.selectedChat.conversation_id);
        if (conv) {
          conv.assigned_agent = assignedAgent;
        }
        return true;
      }
      return false;
    },

    async createCrmLead() {
      if (!this.selectedChat) return null;

      const res = await callApi('create_lead_from_chat', {
        sender_id: this.selectedChat.sender_id,
        sender_name: this.selectedChat.sender_name
      });

      if (res.success && res.data) {
        return res.data.erpnext_lead;
      }
      return null;
    },

    handleIncomingRealtimeMessage(msg) {
      if (!msg) return;

      // Check if message belongs to active chat
      if (this.selectedChat && (msg.conversation_id === this.selectedChat.conversation_id || msg.sender_id === this.selectedChat.sender_id || (msg.conversation_id && msg.conversation_id.includes(this.selectedChat.sender_id)))) {
        // Prevent duplicate appending
        if (!this.activeMessages.some(m => m.name === msg.name || (m.timestamp === msg.timestamp && m.message === msg.message))) {
          this.activeMessages.push(msg);
        }
      }

      // Update or insert conversation in list
      let conv = this.conversations.find(c => c.conversation_id === msg.conversation_id || (c.sender_id && msg.conversation_id && msg.conversation_id.includes(c.sender_id)));
      if (conv) {
        conv.last_message = msg.message;
        conv.last_message_direction = msg.direction;
        conv.last_message_time = msg.timestamp || new Date().toISOString();
        if (msg.platform) conv.platform = msg.platform;
        if (msg.direction === 'Incoming') {
          if (msg.sender_name && !['Paperware Factory', 'Page Admin', 'Page'].includes(msg.sender_name)) {
            conv.sender_name = msg.sender_name;
          }
          if (!this.selectedChat || this.selectedChat.conversation_id !== msg.conversation_id) {
            conv.unread_count = (conv.unread_count || 0) + 1;
          }
        }
      } else {
        // Determine platform from conversation_id or msg.platform
        let platform = msg.platform || 'Facebook';
        if (msg.conversation_id?.startsWith('wa_')) platform = 'WhatsApp';
        else if (msg.conversation_id?.startsWith('ig_')) platform = 'Instagram';

        const displayName = (msg.direction === 'Outgoing')
          ? (this.selectedChat?.sender_name || (platform === 'WhatsApp' ? `+${msg.sender_id}` : platform === 'Instagram' ? 'Instagram User' : 'Facebook Customer'))
          : (msg.sender_name || (platform === 'WhatsApp' ? `+${msg.sender_id}` : platform === 'Instagram' ? 'Instagram User' : 'Facebook Customer'));

        const psid = msg.conversation_id && (msg.conversation_id.startsWith('t_') || msg.conversation_id.startsWith('wa_') || msg.conversation_id.startsWith('ig_'))
          ? msg.conversation_id.substring(3)
          : msg.sender_id;

        this.conversations.unshift({
          conversation_id: msg.conversation_id || `t_${psid}`,
          platform: platform,
          sender_id: psid,
          sender_name: displayName,
          page: msg.page,
          last_message: msg.message,
          last_message_direction: msg.direction,
          last_message_time: msg.timestamp || new Date().toISOString(),
          unread_count: msg.direction === 'Incoming' ? 1 : 0,
          is_complaint: 0
        });
      }
    },

    handleThreadUpdate(data) {
      if (!data) return;
      const conv = this.conversations.find(c => c.conversation_id === data.conversation_id || (c.sender_id && data.conversation_id && data.conversation_id.includes(c.sender_id)));
      if (conv) {
        if (data.last_message) conv.last_message = data.last_message;
        if (data.last_message_time) conv.last_message_time = data.last_message_time;
        if (data.unread_count !== undefined) conv.unread_count = data.unread_count;
      }
    }
  }
});
