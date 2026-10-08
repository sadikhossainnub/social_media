<template>
  <div class="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h3 class="font-display font-bold text-base text-slate-100 flex items-center gap-2">
          <UserCheck class="w-5 h-5 text-brand-400" />
          Team Roles & Page Permissions Matrix
        </h3>
        <p class="text-xs text-slate-400">Assign page access and operational permissions for team members</p>
      </div>

      <div class="flex items-center gap-3">
        <button 
          @click="openAddModal" 
          class="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl shadow-lg flex items-center gap-2 transition"
        >
          <UserPlus class="w-4 h-4" /> Assign Member Role
        </button>
        <button @click="refresh" class="text-xs text-slate-400 hover:text-slate-200 p-2">
          <RotateCw :class="['w-4 h-4', teamStore.loading ? 'animate-spin text-brand-400' : '']" />
        </button>
      </div>
    </div>

    <!-- Team Members Table Matrix -->
    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs text-slate-300">
        <thead class="bg-slate-900/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
          <tr>
            <th class="p-3">User Email</th>
            <th class="p-3">Facebook Page</th>
            <th class="p-3 text-center">Post</th>
            <th class="p-3 text-center">Comment</th>
            <th class="p-3 text-center">Message</th>
            <th class="p-3 text-center">Ads</th>
            <th class="p-3 text-center">Insights</th>
            <th class="p-3 text-center">Settings</th>
            <th class="p-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/60">
          <tr v-if="teamStore.teamMembers.length === 0">
            <td colspan="9" class="p-8 text-center text-slate-500">No custom team roles configured. Administrator has full access.</td>
          </tr>
          <tr v-for="member in teamStore.teamMembers" :key="`${member.user}_${member.page}`" class="hover:bg-slate-800/30 transition">
            <td class="p-3 font-bold text-slate-200">{{ member.user }}</td>
            <td class="p-3 font-medium text-brand-300">{{ member.page }}</td>
            <td class="p-3 text-center">
              <span :class="member.can_post ? 'text-emerald-400 font-bold' : 'text-slate-600'">{{ member.can_post ? '✓' : '✗' }}</span>
            </td>
            <td class="p-3 text-center">
              <span :class="member.can_comment ? 'text-emerald-400 font-bold' : 'text-slate-600'">{{ member.can_comment ? '✓' : '✗' }}</span>
            </td>
            <td class="p-3 text-center">
              <span :class="member.can_message ? 'text-emerald-400 font-bold' : 'text-slate-600'">{{ member.can_message ? '✓' : '✗' }}</span>
            </td>
            <td class="p-3 text-center">
              <span :class="member.can_ads ? 'text-emerald-400 font-bold' : 'text-slate-600'">{{ member.can_ads ? '✓' : '✗' }}</span>
            </td>
            <td class="p-3 text-center">
              <span :class="member.can_insights ? 'text-emerald-400 font-bold' : 'text-slate-600'">{{ member.can_insights ? '✓' : '✗' }}</span>
            </td>
            <td class="p-3 text-center">
              <span :class="member.can_settings ? 'text-emerald-400 font-bold' : 'text-slate-600'">{{ member.can_settings ? '✓' : '✗' }}</span>
            </td>
            <td class="p-3 text-right">
              <button 
                @click="handleRemove(member)" 
                class="text-rose-400 hover:text-rose-300 p-1" 
                title="Remove Role"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Role Assignment Modal -->
    <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div class="w-full max-w-md glass-panel p-6 rounded-2xl border border-slate-700 space-y-4 shadow-2xl">
        <h4 class="text-sm font-bold text-slate-100">Assign Member Page Role</h4>

        <div class="space-y-3">
          <div>
            <label class="text-xs text-slate-400 block mb-1">User Email / ID</label>
            <input 
              v-model="form.user" 
              placeholder="agent@example.com" 
              class="w-full bg-slate-900 text-xs rounded-xl p-2.5 border border-slate-700 text-slate-100"
            >
          </div>

          <div>
            <label class="text-xs text-slate-400 block mb-1">Target Page</label>
            <select v-model="form.page" class="w-full bg-slate-900 text-xs rounded-xl p-2.5 border border-slate-700 text-slate-100">
              <option v-for="p in authStore.pages" :key="p.name || p.page_id" :value="p.name || p.page_id">
                {{ p.page_name || p.name || p.page_id }}
              </option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3 pt-2">
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" v-model="form.can_post" class="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"> Can Post
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" v-model="form.can_comment" class="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"> Can Comment
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" v-model="form.can_message" class="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"> Can Message
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" v-model="form.can_ads" class="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"> Can Ads
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" v-model="form.can_insights" class="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"> Can Insights
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" v-model="form.can_settings" class="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"> Can Settings
            </label>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-3">
          <button @click="showModal = false" class="px-3.5 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl">Cancel</button>
          <button @click="handleSave" class="px-4 py-1.5 bg-brand-600 text-white text-xs font-bold rounded-xl shadow">Save Role</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useTeamStore } from '../stores/team';
import { useAuthStore } from '../stores/auth';
import { UserCheck, UserPlus, RotateCw, Trash2 } from 'lucide-vue-next';

const teamStore = useTeamStore();
const authStore = useAuthStore();

const showModal = ref(false);
const form = ref({
  user: '',
  page: '',
  can_post: true,
  can_comment: true,
  can_message: true,
  can_ads: false,
  can_insights: true,
  can_settings: false
});

onMounted(() => {
  teamStore.fetchTeamMembers();
});

function refresh() {
  teamStore.fetchTeamMembers();
}

function openAddModal() {
  form.value = {
    user: '',
    page: authStore.pages[0]?.name || authStore.pages[0]?.page_id || '',
    can_post: true,
    can_comment: true,
    can_message: true,
    can_ads: false,
    can_insights: true,
    can_settings: false
  };
  showModal.value = true;
}

async function handleSave() {
  if (!form.value.user || !form.value.page) return;
  const ok = await teamStore.saveTeamMember({
    ...form.value,
    can_post: form.value.can_post ? 1 : 0,
    can_comment: form.value.can_comment ? 1 : 0,
    can_message: form.value.can_message ? 1 : 0,
    can_ads: form.value.can_ads ? 1 : 0,
    can_insights: form.value.can_insights ? 1 : 0,
    can_settings: form.value.can_settings ? 1 : 0,
  });

  if (ok) {
    authStore.addToast('Team member permissions updated', 'success');
    showModal.value = false;
  }
}

async function handleRemove(member) {
  const ok = await teamStore.removeTeamMember(member.user, member.page);
  if (ok) {
    authStore.addToast('Role removed', 'info');
  }
}
</script>
