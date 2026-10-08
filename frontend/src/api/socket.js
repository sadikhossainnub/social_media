/**
 * Frappe Socket.IO Real-time Connection Manager
 * Subscribes to Frappe doctype rooms for Facebook Messenger Chat & Facebook Comment.
 */

import { io } from 'socket.io-client';

class RealtimeSocketManager {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.connected = false;
    this.reconnecting = false;
    this.reconnectCount = 0;
  }

  connect(port = null) {
    if (this.socket) return;

    const protocol = window.location.protocol;
    const host = window.location.hostname;
    // Frappe socket.io port default is 9000 or same port in production
    const socketUrl = port ? `${protocol}//${host}:${port}` : `${protocol}//${window.location.host}`;

    try {
      this.socket = io(socketUrl, {
        withCredentials: true,
        reconnection: true,
        reconnectionAttempts: 10,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        transports: ['websocket', 'polling']
      });

      this.socket.on('connect', () => {
        console.log('[Realtime] Socket.IO Connected');
        this.connected = true;
        this.reconnecting = false;
        this.reconnectCount = 0;

        // Subscribe to Frappe doctype rooms
        this.subscribeDoctypeRooms();

        this.trigger('connection_change', { connected: true, reconnecting: false });
      });

      this.socket.on('disconnect', (reason) => {
        console.warn('[Realtime] Socket.IO Disconnected:', reason);
        this.connected = false;
        this.trigger('connection_change', { connected: false, reconnecting: this.reconnecting });
      });

      this.socket.on('reconnect_attempt', () => {
        this.reconnecting = true;
        this.reconnectCount++;
        this.trigger('connection_change', { connected: false, reconnecting: true, count: this.reconnectCount });
      });

      // Register standard Frappe realtime event listener
      this.socket.on('msgprint', (data) => this.trigger('msgprint', data));
      
      // FB custom real-time events
      const events = [
        'fb_new_message',
        'fb_thread_update',
        'fb_new_comment',
        'fb_alert',
        'fb_complaint_alert',
        'fb_typing_indicator',
        'fb_delivery_receipt',
        'fb_read_receipt'
      ];

      events.forEach(eventName => {
        this.socket.on(eventName, (data) => {
          console.log(`[Realtime Event] ${eventName}:`, data);
          this.trigger(eventName, data);
        });
      });

    } catch (e) {
      console.error('[Realtime] Error initializing Socket.IO:', e);
    }
  }

  subscribeDoctypeRooms() {
    if (!this.socket || !this.connected) return;

    // Frappe room subscription format
    this.socket.emit('doctype_subscribe', 'Facebook Messenger Chat');
    this.socket.emit('doctype_subscribe', 'Facebook Comment');
    this.socket.emit('doctype_subscribe', 'Facebook AI Comment Reply');
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  trigger(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(cb => {
        try {
          cb(data);
        } catch (e) {
          console.error(`Error in socket listener for ${event}:`, e);
        }
      });
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }
}

export const realtimeSocket = new RealtimeSocketManager();
