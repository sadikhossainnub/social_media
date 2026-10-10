<template>
  <div class="glass-panel rounded-2xl border border-slate-800 h-[calc(100vh-8.5rem)] flex overflow-hidden shadow-2xl">
    <!-- Left Conversation List Pane -->
    <div class="w-80 border-r border-slate-800/80 flex flex-col shrink-0 bg-slate-900/50">
      <div class="p-3.5 border-b border-slate-800/80 space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            Omnichannel Inbox <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          </span>
          <button 
            @click="refresh" 
            class="text-slate-400 hover:text-slate-200 transition p-1 rounded-lg hover:bg-slate-800" 
            title="Refresh Conversations"
          >
            <RotateCw :class="['w-3.5 h-3.5', inboxStore.loadingConversations ? 'animate-spin text-brand-400' : '']" />
          </button>
        </div>

        <!-- Channel Selector Bar -->
        <div class="grid grid-cols-4 gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-[10px] font-semibold">
          <button 
            @click="inboxStore.selectedChannel = 'all'" 
            :class="[
              'py-1.5 rounded-lg text-center transition flex items-center justify-center gap-1 font-bold', 
              inboxStore.selectedChannel === 'all' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            All <span class="text-[9px] opacity-75">({{ inboxStore.channelCounts.all }})</span>
          </button>
          <button 
            @click="inboxStore.selectedChannel = 'facebook'" 
            :class="[
              'py-1.5 rounded-lg text-center transition flex items-center justify-center gap-1 font-bold', 
              inboxStore.selectedChannel === 'facebook' ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30' : 'text-slate-400 hover:text-blue-400'
            ]"
          >
            FB <span class="text-[9px] opacity-75">({{ inboxStore.channelCounts.facebook }})</span>
          </button>
          <button 
            @click="inboxStore.selectedChannel = 'instagram'" 
            :class="[
              'py-1.5 rounded-lg text-center transition flex items-center justify-center gap-1 font-bold', 
              inboxStore.selectedChannel === 'instagram' ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-md shadow-pink-500/30' : 'text-slate-400 hover:text-pink-400'
            ]"
          >
            IG <span class="text-[9px] opacity-75">({{ inboxStore.channelCounts.instagram }})</span>
          </button>
          <button 
            @click="inboxStore.selectedChannel = 'whatsapp'" 
            :class="[
              'py-1.5 rounded-lg text-center transition flex items-center justify-center gap-1 font-bold', 
              inboxStore.selectedChannel === 'whatsapp' ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30' : 'text-slate-400 hover:text-emerald-400'
            ]"
          >
            WA <span class="text-[9px] opacity-75">({{ inboxStore.channelCounts.whatsapp }})</span>
          </button>
        </div>

        <!-- Filter Pills -->
        <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-[11px] font-semibold">
          <button 
            @click="inboxStore.filterTab = 'all'" 
            :class="['flex-1 py-1 rounded-lg text-center transition', inboxStore.filterTab === 'all' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200']"
          >
            All Threads
          </button>
          <button 
            @click="inboxStore.filterTab = 'unread'" 
            :class="['flex-1 py-1 rounded-lg text-center transition', inboxStore.filterTab === 'unread' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200']"
          >
            Unread
          </button>
          <button 
            @click="inboxStore.filterTab = 'complaints'" 
            :class="['flex-1 py-1 rounded-lg text-center transition', inboxStore.filterTab === 'complaints' ? 'bg-rose-600 text-white shadow' : 'text-slate-400 hover:text-slate-200']"
          >
            Complaints
          </button>
        </div>

        <!-- Search Box -->
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input 
            v-model="inboxStore.searchQuery" 
            placeholder="Search name, phone or message..." 
            class="w-full bg-slate-800/90 text-xs rounded-xl pl-8 pr-3 py-1.5 border border-slate-700/80 text-slate-200 focus:outline-none focus:border-brand-500"
          >
        </div>
      </div>

      <!-- Conversations Scrollable Area -->
      <div class="flex-1 overflow-y-auto divide-y divide-slate-800/40">
        <div v-if="inboxStore.filteredConversations.length === 0" class="p-8 text-center text-xs text-slate-500">
          No matching conversations found.
        </div>
        <div 
          v-for="chat in inboxStore.filteredConversations" 
          :key="chat.conversation_id" 
          @click="inboxStore.selectConversation(chat)"
          :class="[
            'p-3.5 flex items-start gap-3 cursor-pointer hover:bg-slate-800/40 transition',
            inboxStore.selectedChat && inboxStore.selectedChat.conversation_id === chat.conversation_id ? 'bg-slate-800/70 border-l-4 border-brand-500' : ''
          ]"
        >
          <!-- Customer Avatar with Platform Badge -->
          <div class="relative shrink-0">
            <div :class="['w-10 h-10 rounded-full flex items-center justify-center font-extrabold text-xs text-white shadow-md', getPlatformBg(chat.platform)]">
              {{ (chat.sender_name || 'U')[0].toUpperCase() }}
            </div>
            <!-- Platform Mini-Badge -->
            <div 
              :class="['absolute -bottom-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black text-white border-2 border-slate-900 shadow-sm', getPlatformBadge(chat.platform)]"
              :title="chat.platform || 'Facebook'"
            >
              {{ (chat.platform || 'F')[0].toUpperCase() }}
            </div>
          </div>

          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between mb-0.5">
              <h4 class="text-xs font-bold text-slate-200 truncate flex items-center gap-1.5">
                {{ chat.sender_name || 'Customer' }}
              </h4>
              <span class="text-[10px] text-slate-500 shrink-0">{{ fmtTime(chat.last_message_time) }}</span>
            </div>

            <!-- Channel Tag Pill -->
            <div class="flex items-center gap-1 mb-1">
              <span :class="['text-[9px] font-extrabold px-1.5 py-0.2 rounded uppercase tracking-wider', getPlatformPill(chat.platform)]">
                {{ chat.platform || 'Facebook' }}
              </span>
            </div>

            <p class="text-[11px] text-slate-400 truncate font-medium">
              <span v-if="chat.last_message_direction === 'Outgoing'" class="text-brand-400 font-bold">You: </span>
              {{ chat.last_message || 'Attachment' }}
            </p>
            <div class="mt-1 flex items-center gap-1.5">
              <span v-if="chat.unread_count > 0" class="bg-emerald-500/20 text-emerald-300 text-[9px] font-extrabold px-2 py-0.5 rounded-full border border-emerald-500/30">
                {{ chat.unread_count }} unread
              </span>
              <span v-if="chat.is_complaint" class="bg-rose-500/20 text-rose-300 text-[9px] font-extrabold px-2 py-0.5 rounded-full border border-rose-500/30">
                Complaint
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Middle Chat Thread Pane -->
    <div class="flex-1 flex flex-col bg-slate-950/40 min-w-0">
      <div v-if="inboxStore.selectedChat" class="h-14 px-5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/60 shrink-0">
        <div class="flex items-center gap-3">
          <div class="relative shrink-0">
            <div :class="['w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs text-white shadow', getPlatformBg(inboxStore.selectedChat.platform)]">
              {{ (inboxStore.selectedChat.sender_name || 'U')[0].toUpperCase() }}
            </div>
            <div :class="['absolute -bottom-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black text-white border-2 border-slate-900', getPlatformBadge(inboxStore.selectedChat.platform)]">
              {{ (inboxStore.selectedChat.platform || 'F')[0].toUpperCase() }}
            </div>
          </div>

          <div>
            <div class="text-xs font-bold text-slate-200 flex items-center gap-2">
              <span>{{ inboxStore.selectedChat.sender_name }}</span>
              <span :class="['text-[9px] font-extrabold px-2 py-0.5 rounded-full border', getPlatformPillBorder(inboxStore.selectedChat.platform)]">
                {{ inboxStore.selectedChat.platform || 'Facebook' }}
              </span>
            </div>
            <div class="text-[10px] flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-emerald-400 font-bold">Active Thread</span>
              <span class="text-slate-500">• {{ inboxStore.selectedChat.page || 'Connected Account' }}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button 
            @click="handleAiSuggest" 
            :disabled="inboxStore.generatingAiReply" 
            class="text-xs text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 px-3 py-1.5 rounded-lg border border-amber-500/30 flex items-center gap-1.5 font-semibold transition"
          >
            <Sparkles class="w-3.5 h-3.5 text-amber-400" />
            <span>{{ inboxStore.generatingAiReply ? 'Thinking...' : 'AI Smart Reply' }}</span>
          </button>
          <button 
            @click="inboxStore.showCustomerInfoPanel = !inboxStore.showCustomerInfoPanel" 
            class="p-1.5 text-slate-400 hover:text-slate-200 bg-slate-800 rounded-lg border border-slate-700" 
            title="Customer Details"
          >
            <Info class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Chat Messages Container -->
      <div 
        v-if="inboxStore.selectedChat" 
        class="flex-1 p-5 overflow-y-auto space-y-3" 
        id="chatThreadContainer"
      >
        <div 
          v-for="msg in inboxStore.activeMessages" 
          :key="msg.name"
          :class="['flex flex-col max-w-[75%]', msg.direction === 'Outgoing' ? 'ml-auto items-end' : 'mr-auto items-start']"
        >
          <div 
            :class="[
              'px-4 py-2.5 rounded-2xl text-xs font-medium shadow-md leading-relaxed whitespace-pre-wrap',
              msg.direction === 'Outgoing' ? 'bg-gradient-to-r from-brand-600 to-indigo-600 text-white rounded-br-none' : 'bg-slate-800 text-slate-200 border border-slate-700/80 rounded-bl-none'
            ]"
          >
            {{ msg.message }}
          </div>
          <span class="text-[9px] text-slate-500 mt-1 px-1 flex items-center gap-1">
            {{ fmtTime(msg.timestamp) }}
            <span v-if="msg.direction === 'Outgoing'" class="flex items-center gap-0.5 ml-1">
              <CheckCheck v-if="msg.is_read" class="w-3.5 h-3.5 text-sky-400 font-extrabold" title="Seen" />
              <Check v-else class="w-3 h-3 text-slate-500" title="Sent" />
            </span>
          </span>
        </div>
      </div>

      <!-- Typing Indicator Bubble -->
      <div 
        v-if="inboxStore.isCustomerTyping && inboxStore.selectedChat" 
        class="px-5 py-2 flex items-center gap-2 text-xs text-brand-300 font-semibold bg-slate-900/60 border-t border-slate-800/80 shrink-0"
      >
        <span class="flex items-center gap-1">
          <span class="w-1.5 h-1.5 bg-brand-400 rounded-full animate-ping"></span>
          <span class="w-1.5 h-1.5 bg-brand-400 rounded-full animate-ping delay-150"></span>
          <span class="w-1.5 h-1.5 bg-brand-400 rounded-full animate-ping delay-300"></span>
        </span>
        <span>{{ inboxStore.selectedChat.sender_name }} is typing...</span>
      </div>

      <!-- Empty Chat State -->
      <div v-else-if="!inboxStore.selectedChat" class="flex-1 flex flex-col items-center justify-center text-slate-500 p-8">
        <MessageSquare class="w-12 h-12 stroke-1 mb-3 text-slate-600" />
        <p class="text-xs font-semibold">Select a conversation thread from the universal inbox to start chatting</p>
      </div>

      <!-- Chat Input Composer -->
      <div v-if="inboxStore.selectedChat" class="p-4 border-t border-slate-800/80 bg-slate-900/60 shrink-0 space-y-2.5">
        <!-- Quick Reply Pills -->
        <div class="flex items-center gap-2 overflow-x-auto pb-1">
          <span class="text-[10px] text-slate-500 font-bold uppercase shrink-0">Quick Replies:</span>
          <button 
            v-for="qr in quickReplies" 
            :key="qr" 
            @click="sendText = qr" 
            class="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-full border border-slate-700/80 whitespace-nowrap"
          >
            {{ qr }}
          </button>
        </div>

        <div class="flex items-center gap-2">
          <input 
            v-model="sendText" 
            @keyup.enter="handleSend" 
            :placeholder="`Type direct reply via ${inboxStore.selectedChat.platform || 'Facebook'}...`" 
            class="flex-1 bg-slate-800/90 text-xs rounded-xl px-4 py-2.5 border border-slate-700 text-slate-200 focus:outline-none focus:border-brand-500"
          >
          <button 
            @click="handleSend" 
            :disabled="inboxStore.sendingMsg || !sendText.trim()" 
            class="px-4 py-2.5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl shadow-lg shadow-brand-600/30 text-xs flex items-center gap-2 transition transform active:scale-95"
          >
            <Send class="w-4 h-4" /> Send
          </button>
        </div>
      </div>
    </div>

    <!-- Right Customer CRM Context Panel -->
    <div 
      v-if="inboxStore.selectedChat && inboxStore.showCustomerInfoPanel" 
      class="w-72 border-l border-slate-800/80 p-4 bg-slate-900/40 flex flex-col space-y-4 shrink-0 overflow-y-auto"
    >
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Customer Info</h4>
        <button @click="inboxStore.showCustomerInfoPanel = false" class="text-slate-500 hover:text-slate-300">
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="text-center space-y-2">
        <div :class="['w-14 h-14 rounded-full flex items-center justify-center font-bold text-lg text-white mx-auto shadow-lg', getPlatformBg(inboxStore.selectedChat.platform)]">
          {{ (inboxStore.selectedChat.sender_name || 'U')[0].toUpperCase() }}
        </div>
        <div class="text-sm font-extrabold text-slate-100">{{ inboxStore.selectedChat.sender_name }}</div>
        <div class="text-[10px] text-slate-500 font-mono">ID: {{ inboxStore.selectedChat.sender_id }}</div>
        
        <div class="flex justify-center pt-1">
          <span :class="['text-[10px] font-extrabold px-3 py-0.5 rounded-full border', getPlatformPillBorder(inboxStore.selectedChat.platform)]">
            Channel: {{ inboxStore.selectedChat.platform || 'Facebook' }}
          </span>
        </div>
      </div>

      <!-- CRM Action Buttons -->
      <div class="space-y-2 pt-3 border-t border-slate-800/80">
        <button 
          @click="handleCreateLead" 
          class="w-full py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs rounded-xl shadow flex items-center justify-center gap-2"
        >
          <UserPlus class="w-3.5 h-3.5" /> Convert to CRM Lead
        </button>
        <button 
          @click="handleFlagComplaint" 
          class="w-full py-2 bg-slate-800 hover:bg-slate-700 text-rose-300 font-semibold text-xs rounded-xl border border-slate-700 flex items-center justify-center gap-2"
        >
          <AlertCircle class="w-3.5 h-3.5" /> Flag as Complaint
        </button>
      </div>

      <!-- Details Summary -->
      <div class="glass-card p-3 rounded-xl border border-slate-800 text-xs space-y-2">
        <div class="flex justify-between text-slate-400">
          <span>Channel:</span> <span class="font-bold text-slate-200">{{ inboxStore.selectedChat.platform || 'Facebook' }}</span>
        </div>
        <div class="flex justify-between text-slate-400">
          <span>Account/Instance:</span> <span class="font-bold text-slate-200 truncate ml-2 max-w-[120px]">{{ inboxStore.selectedChat.page || 'N/A' }}</span>
        </div>
        <div class="flex justify-between text-slate-400">
          <span>Status:</span> <span class="font-bold text-slate-200">{{ inboxStore.selectedChat.conversation_status || 'Open' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useInboxStore } from '../stores/inbox';
import { useAuthStore } from '../stores/auth';
import {
  MessageSquare,
  Search,
  RotateCw,
  Sparkles,
  Info,
  Send,
  Check,
  CheckCheck,
  UserPlus,
  AlertCircle,
  X
} from 'lucide-vue-next';

const inboxStore = useInboxStore();
const authStore = useAuthStore();

const sendText = ref('');
const quickReplies = [
  'Hi there! How can we help you today?',
  'Thanks for reaching out! What product details are you interested in?',
  'Our office hours are 9 AM to 6 PM. We will get back to you shortly!'
];

let pollTimer = null;

onMounted(() => {
  inboxStore.fetchConversations(authStore.selectedPageId);
  pollTimer = setInterval(() => {
    if (inboxStore.selectedChat) {
      inboxStore.selectConversation(inboxStore.selectedChat);
    } else {
      inboxStore.fetchConversations(authStore.selectedPageId);
    }
  }, 4000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});

function refresh() {
  inboxStore.fetchConversations(authStore.selectedPageId);
}

async function handleSend() {
  if (!sendText.value.trim()) return;
  const text = sendText.value;
  sendText.value = '';
  const ok = await inboxStore.sendMessage(text, authStore.selectedPageId);
  if (ok) {
    authStore.addToast('Message sent successfully', 'success');
  }
}

async function handleAiSuggest() {
  const reply = await inboxStore.generateAiReply();
  if (reply) {
    sendText.value = reply;
    authStore.addToast('AI Smart Reply generated', 'info');
  }
}

async function handleCreateLead() {
  const lead = await inboxStore.createCrmLead();
  if (lead) {
    authStore.addToast(`Converted to Lead: ${lead}`, 'success');
  }
}

async function handleFlagComplaint() {
  const ok = await inboxStore.flagAsComplaint('High');
  if (ok) {
    authStore.addToast('Conversation flagged as Complaint', 'warning');
  }
}

function fmtTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return ts;
  }
}

function getPlatformBg(platform) {
  const p = (platform || 'facebook').toLowerCase();
  if (p === 'whatsapp') return 'bg-gradient-to-tr from-emerald-600 to-teal-500';
  if (p === 'instagram') return 'bg-gradient-to-tr from-purple-600 via-pink-500 to-amber-500';
  return 'bg-gradient-to-tr from-blue-600 to-indigo-600';
}

function getPlatformBadge(platform) {
  const p = (platform || 'facebook').toLowerCase();
  if (p === 'whatsapp') return 'bg-emerald-500';
  if (p === 'instagram') return 'bg-gradient-to-tr from-purple-500 to-pink-500';
  return 'bg-blue-600';
}

function getPlatformPill(platform) {
  const p = (platform || 'facebook').toLowerCase();
  if (p === 'whatsapp') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (p === 'instagram') return 'bg-pink-500/20 text-pink-300 border border-pink-500/30';
  return 'bg-blue-500/20 text-blue-300 border border-blue-500/30';
}

function getPlatformPillBorder(platform) {
  const p = (platform || 'facebook').toLowerCase();
  if (p === 'whatsapp') return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
  if (p === 'instagram') return 'bg-pink-500/10 text-pink-300 border-pink-500/30';
  return 'bg-blue-500/10 text-blue-300 border-blue-500/30';
}
</script>
