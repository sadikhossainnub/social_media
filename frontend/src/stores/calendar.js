import { defineStore } from 'pinia';
import { callApi } from '../api/client';

export const useCalendarStore = defineStore('calendar', {
  state: () => ({
    entries: [],
    loading: false,
    selectedMonth: new Date().toISOString().substring(0, 7), // YYYY-MM
  }),

  actions: {
    async fetchCalendarEntries(pageId = null) {
      this.loading = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_calendar_entries', params);
      this.loading = false;

      if (res.success && Array.isArray(res.data)) {
        this.entries = res.data;
      }
    },

    async reschedulePost(name, scheduledDatetime) {
      const res = await callApi('schedule_post', {
        name,
        scheduled_datetime: scheduledDatetime
      });

      if (res.success) {
        const item = this.entries.find(e => e.name === name);
        if (item) {
          const parts = scheduledDatetime.split(' ');
          item.scheduled_date = parts[0];
          if (parts[1]) item.scheduled_time = parts[1];
          item.status = 'Scheduled';
        }
        return true;
      }
      return false;
    }
  }
});
