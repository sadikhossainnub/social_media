import { defineStore } from 'pinia';
import { callApi } from '../api/client';

export const useLeadsStore = defineStore('leads', {
  state: () => ({
    leads: [],
    loading: false,
    filterStatus: 'all', // 'all', 'New', 'Converted', 'Ignored'
    searchQuery: '',
  }),

  getters: {
    filteredLeads: (state) => {
      let result = state.leads;
      if (state.filterStatus !== 'all') {
        result = result.filter(l => l.status === state.filterStatus);
      }
      if (state.searchQuery.trim()) {
        const q = state.searchQuery.toLowerCase();
        result = result.filter(l => 
          (l.full_name && l.full_name.toLowerCase().includes(q)) ||
          (l.email && l.email.toLowerCase().includes(q)) ||
          (l.phone && l.phone.toLowerCase().includes(q))
        );
      }
      return result;
    }
  },

  actions: {
    async fetchLeads(pageId = null) {
      this.loading = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_leads', params);
      this.loading = false;

      if (res.success && Array.isArray(res.data)) {
        this.leads = res.data;
      }
    },

    async convertToErpnextLead(leadName) {
      const res = await callApi('convert_lead_to_erpnext', { lead_name: leadName });
      if (res.success) {
        const lead = this.leads.find(l => l.name === leadName);
        if (lead) {
          lead.status = 'Converted';
          if (res.data?.erpnext_lead) {
            lead.erpnext_lead = res.data.erpnext_lead;
          }
        }
        return true;
      }
      return false;
    },

    exportCsv() {
      if (this.filteredLeads.length === 0) return;

      const headers = ['Full Name', 'Email', 'Phone', 'Ad / Campaign', 'Status', 'Date'];
      const rows = this.filteredLeads.map(l => [
        `"${l.full_name || ''}"`,
        `"${l.email || ''}"`,
        `"${l.phone || ''}"`,
        `"${l.ad_name || l.campaign_name || ''}"`,
        `"${l.status || ''}"`,
        `"${l.created_at || ''}"`
      ]);

      const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `facebook_leads_${new Date().toISOString().substring(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }
});
