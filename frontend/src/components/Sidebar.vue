<template>
  <aside class="w-full md:w-64 glass-panel flex flex-col border-r border-slate-800/80 shrink-0 z-20">
    <!-- Header Logo & Title -->
    <div class="p-5 flex items-center justify-between border-b border-slate-800/60">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-sky-400 flex items-center justify-center shadow-lg shadow-brand-500/30">
          <Share2 class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="font-display font-extrabold text-lg gradient-text leading-tight">Social Desk</h1>
          <span class="text-[10px] font-semibold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded-full border border-brand-500/20">Enterprise AI v3.0</span>
        </div>
      </div>
    </div>

    <!-- Connected Page Selector -->
    <div class="px-4 py-3 border-b border-slate-800/40 bg-slate-950/30">
      <label class="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">Active Meta Page</label>
      <select 
        :value="authStore.selectedPageId" 
        @change="onPageChange" 
        class="w-full bg-slate-900/90 text-xs font-semibold rounded-xl px-3 py-2 border border-slate-700/80 text-slate-200 focus:outline-none focus:border-brand-500 transition"
      >
        <option value="" disabled v-if="!authStore.pages || authStore.pages.length === 0">No Pages Available</option>
        <option value="all" v-if="authStore.pages && authStore.pages.length > 0">🌐 All Connected Pages</option>
        <option v-for="p in authStore.pages" :key="p.name || p.page_id" :value="p.name || p.page_id">
          {{ p.page_name || p.name || p.page_id }}
        </option>
      </select>
    </div>

    <!-- Navigation Menu -->
    <nav class="flex-1 px-3 py-3 space-y-1 overflow-y-auto">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        v-slot="{ isActive }"
        class="block"
      >
        <button 
          :class="[
            'w-full flex items-center gap-3 px-3.5 py-2.5 text-xs font-semibold rounded-xl transition-all duration-200',
            isActive ? 'active-nav-link' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/40'
          ]"
        >
          <component :is="item.icon" class="w-4 h-4 shrink-0" />
          <span class="truncate">{{ item.name }}</span>

          <span 
            v-if="item.badge && item.badge() > 0" 
            class="ml-auto bg-brand-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold shadow-sm shadow-brand-500/50"
          >
            {{ item.badge() }}
          </span>
        </button>
      </router-link>
    </nav>

    <!-- Realtime Connection Status Footer Pill -->
    <div class="px-4 py-2 bg-slate-950/40 border-t border-slate-800/40 flex items-center justify-between text-[11px]">
      <span class="text-slate-400 flex items-center gap-1.5">
        <span 
          :class="['w-2 h-2 rounded-full', authStore.socketConnected ? 'bg-emerald-400 animate-pulse' : authStore.socketReconnecting ? 'bg-amber-400 animate-ping' : 'bg-rose-500']"
        ></span>
        {{ authStore.socketConnected ? 'Realtime Live' : authStore.socketReconnecting ? 'Reconnecting...' : 'Socket Offline' }}
      </span>
    </div>

    <!-- User Profile Footer -->
    <div class="p-3 border-t border-slate-800/60 flex items-center gap-3 bg-slate-900/40">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 border border-brand-500/30 flex items-center justify-center font-bold text-xs text-white shrink-0 shadow">
        {{ authStore.userInitials }}
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-xs font-bold truncate text-slate-200">{{ authStore.userFullName }}</div>
        <div class="text-[10px] text-slate-400 truncate">{{ authStore.userEmail }}</div>
      </div>
      <button 
        @click="authStore.logout" 
        title="Logout" 
        class="p-2 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition"
      >
        <LogOut class="w-4 h-4" />
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useInboxStore } from '../stores/inbox';
import { useCommentsStore } from '../stores/comments';
import {
  Share2,
  MessageSquare,
  MessageCircle,
  LayoutDashboard,
  Calendar,
  PenTool,
  Users,
  Megaphone,
  UserCheck,
  LogOut
} from 'lucide-vue-next';

const authStore = useAuthStore();
const inboxStore = useInboxStore();
const commentsStore = useCommentsStore();

const navItems = computed(() => [
  { 
    name: 'Messenger Inbox', 
    path: '/inbox', 
    icon: MessageSquare, 
    badge: () => inboxStore.totalUnreadCount 
  },
  { 
    name: 'Comments Hub', 
    path: '/comments', 
    icon: MessageCircle, 
    badge: () => commentsStore.pendingAiCount 
  },
  { name: 'Analytics Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Content Calendar', path: '/calendar', icon: Calendar },
  { name: 'Post Composer', path: '/composer', icon: PenTool },
  { name: 'Leads Pipeline', path: '/leads', icon: Users },
  { name: 'Ads & Campaigns', path: '/ads', icon: Megaphone },
  { name: 'Team Permissions', path: '/team', icon: UserCheck },
]);

function onPageChange(e) {
  const selected = e.target.value;
  authStore.setSelectedPage(selected);
  inboxStore.fetchConversations(selected);
  commentsStore.fetchComments(selected);
}
</script>
