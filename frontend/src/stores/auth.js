import { defineStore } from 'pinia';
import { callApi, setCsrfToken } from '../api/client';
import { realtimeSocket } from '../api/socket';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    userFullName: '',
    userEmail: '',
    userImage: '',
    roles: [],
    isAdmin: false,
    pages: [],
    selectedPageId: 'all',
    permissions: {},
    toasts: [],
    toastCounter: 0,
    socketConnected: false,
    socketReconnecting: false,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.user && state.user !== 'Guest',
    userInitials: (state) => {
      const name = state.userFullName || state.user || 'User';
      return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    },
    selectedPage: (state) => {
      if (state.selectedPageId === 'all') return null;
      return state.pages.find(p => p.name === state.selectedPageId || p.page_id === state.selectedPageId) || null;
    },
    canPost: (state) => {
      if (state.isAdmin) return true;
      if (state.selectedPageId === 'all') return true;
      return state.permissions[state.selectedPageId]?.can_post ?? true;
    },
    canComment: (state) => {
      if (state.isAdmin) return true;
      if (state.selectedPageId === 'all') return true;
      return state.permissions[state.selectedPageId]?.can_comment ?? true;
    },
    canMessage: (state) => {
      if (state.isAdmin) return true;
      if (state.selectedPageId === 'all') return true;
      return state.permissions[state.selectedPageId]?.can_message ?? true;
    },
    canAds: (state) => {
      if (state.isAdmin) return true;
      if (state.selectedPageId === 'all') return true;
      return state.permissions[state.selectedPageId]?.can_ads ?? true;
    },
    canInsights: (state) => {
      if (state.isAdmin) return true;
      if (state.selectedPageId === 'all') return true;
      return state.permissions[state.selectedPageId]?.can_insights ?? true;
    },
    canSettings: (state) => {
      if (state.isAdmin) return true;
      if (state.selectedPageId === 'all') return true;
      return state.permissions[state.selectedPageId]?.can_settings ?? true;
    }
  },

  actions: {
    initFromWindowData() {
      const initial = window.fbPortalData || {};
      if (initial.userEmail) {
        this.user = initial.userEmail;
        this.userEmail = initial.userEmail;
        this.userFullName = initial.userFullName || initial.userEmail;
        this.isAdmin = initial.isAdmin || false;
        this.pages = initial.pages || [];
        this.permissions = initial.permissions || {};
        if (initial.csrfToken) {
          setCsrfToken(initial.csrfToken);
        }
      }

      // Connect Socket.IO
      realtimeSocket.connect();
      realtimeSocket.on('connection_change', (status) => {
        this.socketConnected = status.connected;
        this.socketReconnecting = status.reconnecting;
      });

      realtimeSocket.on('fb_alert', (alert) => {
        this.addToast(alert.message || alert.title, 'info');
      });
    },

    async fetchSession() {
      this.loading = true;
      const res = await callApi('get_session');
      this.loading = false;
      
      if (res.success && res.data) {
        this.user = res.data.user;
        this.userFullName = res.data.full_name;
        this.userEmail = res.data.user;
        this.userImage = res.data.user_image || '';
        this.roles = res.data.roles || [];
        this.isAdmin = res.data.is_admin || false;
        if (res.data.csrf_token) {
          setCsrfToken(res.data.csrf_token);
        }
        await this.fetchUserPermissions();
        return true;
      }
      return false;
    },

    async fetchUserPermissions() {
      const res = await callApi('get_current_user_permissions');
      if (res.success && res.data) {
        this.isAdmin = res.data.is_admin || false;
        if (res.data.pages) {
          this.pages = res.data.pages;
        }
        if (res.data.permissions) {
          this.permissions = res.data.permissions;
        }
      }
    },

    async login(username, password) {
      this.loading = true;
      const res = await callApi('portal_login', { usr: username, pwd: password });
      this.loading = false;

      if (res.success) {
        this.user = username;
        this.userEmail = username;
        if (res.data?.csrf_token) {
          setCsrfToken(res.data.csrf_token);
        }
        await this.fetchSession();
        this.addToast('Logged in successfully', 'success');
        return true;
      } else {
        this.addToast(res.message || 'Login failed', 'error');
        return false;
      }
    },

    async logout() {
      try {
        await fetch('/api/method/logout', { method: 'POST', credentials: 'same-origin' });
      } catch (e) {
        console.error(e);
      }
      this.user = null;
      window.location.href = '/login';
    },

    setSelectedPage(pageId) {
      this.selectedPageId = pageId;
    },

    addToast(message, type = 'info', duration = 4000) {
      const id = ++this.toastCounter;
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, duration);
    }
  }
});
