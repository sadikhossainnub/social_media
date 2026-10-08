<template>
  <header class="h-16 glass-panel border-b border-slate-800/80 flex items-center justify-between px-6 shrink-0 z-10">
    <div class="flex items-center gap-3">
      <h2 class="font-display font-bold text-base text-slate-100">{{ currentRouteTitle }}</h2>
      <span 
        v-if="authStore.selectedPage" 
        class="bg-brand-500/10 text-brand-300 text-xs px-3 py-1 rounded-full border border-brand-500/20 font-semibold flex items-center gap-1.5"
      >
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        {{ authStore.selectedPage.page_name }}
      </span>
      <span 
        v-else 
        class="bg-slate-800/80 text-slate-300 text-xs px-3 py-1 rounded-full border border-slate-700 font-medium"
      >
        🌐 All Pages Active
      </span>
    </div>

    <div class="flex items-center gap-3">
      <router-link to="/composer" class="block">
        <button class="px-3.5 py-1.5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-600/25 flex items-center gap-2 transition transform active:scale-95">
          <Plus class="w-4 h-4" />
          <span>New Post</span>
        </button>
      </router-link>

      <button 
        @click="triggerSync" 
        :disabled="syncing" 
        class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 flex items-center gap-2 transition"
      >
        <RefreshCw :class="['w-3.5 h-3.5', syncing ? 'animate-spin text-brand-400' : '']" />
        <span>{{ syncing ? 'Syncing...' : 'Sync Messages' }}</span>
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useInboxStore } from '../stores/inbox';
import { Plus, RefreshCw } from 'lucide-vue-next';

const route = useRoute();
const authStore = useAuthStore();
const inboxStore = useInboxStore();

const syncing = ref(false);

const currentRouteTitle = computed(() => {
  return route.name || 'Social Desk';
});

async function triggerSync() {
  syncing.value = true;
  await inboxStore.fetchConversations(authStore.selectedPageId);
  authStore.addToast('Messenger synced successfully', 'success');
  syncing.value = false;
}
</script>
