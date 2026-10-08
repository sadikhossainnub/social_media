import { defineStore } from 'pinia';
import { callApi } from '../api/client';

export const useAdsStore = defineStore('ads', {
  state: () => ({
    accounts: [],
    campaignsTree: [],
    selectedAccount: null,
    loading: false
  }),

  getters: {
    totalSpend: (state) => {
      return state.campaignsTree.reduce((acc, c) => acc + (parseFloat(c.spend) || 0), 0);
    },
    totalImpressions: (state) => {
      return state.campaignsTree.reduce((acc, c) => acc + (parseInt(c.impressions) || 0), 0);
    },
    totalClicks: (state) => {
      return state.campaignsTree.reduce((acc, c) => acc + (parseInt(c.clicks) || 0), 0);
    },
    avgCtr: (state) => {
      if (state.campaignsTree.length === 0) return 0;
      const sum = state.campaignsTree.reduce((acc, c) => acc + (parseFloat(c.ctr) || 0), 0);
      return (sum / state.campaignsTree.length).toFixed(2);
    }
  },

  actions: {
    async fetchAdAccounts() {
      const res = await callApi('get_ad_campaigns');
      if (res.success && Array.isArray(res.data)) {
        this.accounts = res.data;
      }
    },

    async fetchAdsTree(account = null) {
      this.loading = true;
      const res = await callApi('get_ads_tree', { account });
      this.loading = false;

      if (res.success && Array.isArray(res.data)) {
        this.campaignsTree = res.data;
      }
    }
  }
});
