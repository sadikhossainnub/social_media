import { defineStore } from 'pinia';
import { callApi } from '../api/client';

export const useTeamStore = defineStore('team', {
  state: () => ({
    teamMembers: [],
    loading: false
  }),

  actions: {
    async fetchTeamMembers() {
      this.loading = true;
      const res = await callApi('get_team_members');
      this.loading = false;

      if (res.success && Array.isArray(res.data)) {
        this.teamMembers = res.data;
      }
    },

    async saveTeamMember(memberData) {
      const res = await callApi('save_team_member', memberData);
      if (res.success) {
        await this.fetchTeamMembers();
        return true;
      }
      return false;
    },

    async removeTeamMember(user, page) {
      const res = await callApi('remove_team_member', { user, page });
      if (res.success) {
        this.teamMembers = this.teamMembers.filter(m => !(m.user === user && m.page === page));
        return true;
      }
      return false;
    }
  }
});
