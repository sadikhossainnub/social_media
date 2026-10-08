<template>
  <div class="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h3 class="font-display font-bold text-base text-slate-100 flex items-center gap-2">
          <Users class="w-5 h-5 text-brand-400" />
          Captured Facebook Lead Gen Forms
        </h3>
        <p class="text-xs text-slate-400">Lead form submissions and 1-click ERPNext CRM creation</p>
      </div>

      <div class="flex items-center gap-2">
        <button 
          @click="leadsStore.exportCsv" 
          class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 flex items-center gap-1.5 transition"
        >
          <Download class="w-3.5 h-3.5" /> Export CSV
        </button>
        <button @click="refresh" class="text-xs text-slate-400 hover:text-slate-200 p-2">
          <RotateCw :class="['w-4 h-4', leadsStore.loading ? 'animate-spin text-brand-400' : '']" />
        </button>
      </div>
    </div>

    <!-- Filter & Search Bar -->
    <div class="flex flex-col sm:flex-row items-center gap-3">
      <div class="relative flex-1 w-full">
        <Search class="w-3.5 h-3.5 text-slate-500 absolute left-3.5 top-2.5" />
        <input 
          v-model="leadsStore.searchQuery" 
          placeholder="Search lead name, email, phone..." 
          class="w-full bg-slate-900 text-xs rounded-xl pl-9 pr-4 py-2 border border-slate-700 text-slate-200 focus:outline-none focus:border-brand-500"
        >
      </div>

      <select v-model="leadsStore.filterStatus" class="bg-slate-900 text-xs rounded-xl px-3 py-2 border border-slate-700 text-slate-200 w-full sm:w-auto">
        <option value="all">All Lead Statuses</option>
        <option value="New">New Leads</option>
        <option value="Converted">Converted to ERPNext</option>
        <option value="Ignored">Ignored</option>
      </select>
    </div>

    <!-- Leads Table -->
    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs text-slate-300">
        <thead class="bg-slate-900/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
          <tr>
            <th class="p-3">Full Name</th>
            <th class="p-3">Email</th>
            <th class="p-3">Phone</th>
            <th class="p-3">Form / Campaign</th>
            <th class="p-3">Status</th>
            <th class="p-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/60">
          <tr v-if="leadsStore.filteredLeads.length === 0">
            <td colspan="6" class="p-8 text-center text-slate-500">No matching leads found.</td>
          </tr>
          <tr v-for="lead in leadsStore.filteredLeads" :key="lead.name" class="hover:bg-slate-800/30 transition">
            <td class="p-3 font-bold text-slate-200">{{ lead.full_name || 'N/A' }}</td>
            <td class="p-3">{{ lead.email || 'N/A' }}</td>
            <td class="p-3">{{ lead.phone || 'N/A' }}</td>
            <td class="p-3">{{ lead.ad_name || lead.campaign_name || 'Facebook Lead Form' }}</td>
            <td class="p-3">
              <span 
                :class="[
                  'px-2.5 py-0.5 rounded-full text-[10px] font-bold',
                  lead.status === 'Converted' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                ]"
              >
                {{ lead.status || 'New' }}
              </span>
            </td>
            <td class="p-3 text-right">
              <button 
                v-if="lead.status !== 'Converted'" 
                @click="handleConvert(lead)" 
                class="px-3 py-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-[11px] rounded-lg shadow flex items-center gap-1 ml-auto"
              >
                <UserCheck class="w-3.5 h-3.5" /> Convert to CRM
              </button>
              <span v-else class="text-xs text-emerald-400 font-bold flex items-center gap-1 justify-end">
                <CheckCircle2 class="w-3.5 h-3.5" /> Converted
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useLeadsStore } from '../stores/leads';
import { useAuthStore } from '../stores/auth';
import { Users, Download, RotateCw, Search, UserCheck, CheckCircle2 } from 'lucide-vue-next';

const leadsStore = useLeadsStore();
const authStore = useAuthStore();

onMounted(() => {
  leadsStore.fetchLeads(authStore.selectedPageId);
});

function refresh() {
  leadsStore.fetchLeads(authStore.selectedPageId);
}

async function handleConvert(lead) {
  const ok = await leadsStore.convertToErpnextLead(lead.name);
  if (ok) {
    authStore.addToast(`Converted ${lead.full_name || 'Lead'} to ERPNext CRM Lead`, 'success');
  }
}
</script>
