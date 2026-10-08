import { defineStore } from 'pinia';
import { callApi } from '../api/client';

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    summary: {
      total_followers: 0,
      total_reach: 0,
      total_engagement: 0,
      unread_messages: 0,
      pending_comments: 0
    },
    reachData: [],
    sentimentCounts: {
      Positive: 0,
      Neutral: 0,
      Negative: 0
    },
    chartRange: '7d',
    loading: false
  }),

  actions: {
    async fetchDashboardSummary(pageId = null) {
      this.loading = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_dashboard_summary', params);
      this.loading = false;

      if (res.success && res.data) {
        this.summary = { ...this.summary, ...res.data };
      }
    },

    async fetchInsightsData(pageId = null, range = '7d') {
      this.chartRange = range;
      const params = { period: range };
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_page_insights_data', params);
      if (res.success && res.data) {
        if (Array.isArray(res.data.reach)) {
          this.reachData = res.data.reach;
        }
        if (res.data.sentiment) {
          this.sentimentCounts = res.data.sentiment;
        }
      }
    }
  }
});
