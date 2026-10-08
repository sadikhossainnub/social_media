import { defineStore } from 'pinia';
import { callApi } from '../api/client';
import { realtimeSocket } from '../api/socket';

export const useCommentsStore = defineStore('comments', {
  state: () => ({
    comments: [],
    aiReplies: [],
    loading: false,
    loadingAiReplies: false,
    sentimentFilter: 'all', // 'all', 'Positive', 'Neutral', 'Negative', 'Spam'
    activeTab: 'moderation', // 'moderation', 'ai_approvals'
  }),

  getters: {
    filteredComments: (state) => {
      if (state.sentimentFilter === 'all') return state.comments;
      return state.comments.filter(c => c.sentiment === state.sentimentFilter);
    },
    pendingAiCount: (state) => {
      return state.aiReplies.filter(r => r.approval_status === 'Pending').length;
    }
  },

  actions: {
    initRealtimeListeners() {
      realtimeSocket.on('fb_new_comment', (comment) => {
        if (!this.comments.some(c => c.comment_id === comment.comment_id || c.name === comment.name)) {
          this.comments.unshift(comment);
        }
      });
    },

    async fetchComments(pageId = null) {
      this.loading = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_comments', params);
      this.loading = false;

      if (res.success && Array.isArray(res.data)) {
        this.comments = res.data;
      }
    },

    async fetchAiReplies() {
      this.loadingAiReplies = true;
      const res = await callApi('get_ai_replies');
      this.loadingAiReplies = false;

      if (res.success && Array.isArray(res.data)) {
        this.aiReplies = res.data;
      }
    },

    async replyToComment(commentId, message) {
      if (!commentId || !message.trim()) return false;

      const res = await callApi('reply_to_comment', {
        comment_id: commentId,
        reply_message: message
      });

      if (res.success) {
        const comment = this.comments.find(c => c.comment_id === commentId || c.name === commentId);
        if (comment) {
          comment.reply_message = message;
          comment.replied_time = new Date().toISOString();
        }
        return true;
      }
      return false;
    },

    async toggleHideComment(comment) {
      if (!comment) return false;

      const newHideState = comment.is_hidden ? 0 : 1;
      const res = await callApi('hide_comment', {
        comment_id: comment.comment_id || comment.name,
        hide: newHideState
      });

      if (res.success) {
        comment.is_hidden = newHideState;
        return true;
      }
      return false;
    },

    async approveAiReply(name) {
      const res = await callApi('approve_ai_reply', { name });
      if (res.success) {
        const item = this.aiReplies.find(r => r.name === name);
        if (item) {
          item.approval_status = 'Approved';
        }
        return true;
      }
      return false;
    },

    async rejectAiReply(name) {
      const res = await callApi('reject_ai_reply', { name });
      if (res.success) {
        const item = this.aiReplies.find(r => r.name === name);
        if (item) {
          item.approval_status = 'Rejected';
        }
        return true;
      }
      return false;
    }
  }
});
