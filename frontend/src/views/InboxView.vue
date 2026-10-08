<template>
  <div class="glass-panel rounded-2xl border border-slate-800 h-[calc(100vh-8.5rem)] flex overflow-hidden">
    <!-- Left Conversation List Pane -->
    <div class="w-80 border-r border-slate-800/80 flex flex-col shrink-0 bg-slate-900/50">
      <div class="p-3.5 border-b border-slate-800/80 space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            Inbox <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          </span>
          <button 
            @click="refresh" 
            class="text-slate-400 hover:text-slate-200 transition" 
            title="Refresh Conversations"
          >
            <RotateCw :class="['w-3.5 h-3.5', inboxStore.loadingConversations ? 'animate-spin text-brand-400' : '']" />
          </button>
        </div>

        <!-- Filter Pills -->
        <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-[11px] font-semibold">
          <button 
            @click="inboxStore.filterTab = 'all'" 
            :class="['flex-1 py-1 rounded-lg text-center transition', inboxStore.filterTab === 'all' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200']"
          >
            All
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
            placeholder="Search customer name..." 
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
          <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center font-bold text-xs text-white shrink-0 shadow-md">
            {{ (chat.sender_name || 'U')[0].toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between mb-1">
              <h4 class="text-xs font-bold text-slate-200 truncate">{{ chat.sender_name || 'Facebook User' }}</h4>
              <span class="text-[10px] text-slate-500">{{ fmtTime(chat.last_message_time) }}</span>
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
          <div class="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center font-bold text-xs text-white shadow">
            {{ inboxStore.selectedChat.sender_name[0] }}
          </div>
          <div>
            <div class="text-xs font-bold text-slate-200">{{ inboxStore.selectedChat.sender_name }}</div>
            <div class="text-[10px] flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-emerald-400 font-bold">Active Thread</span>
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
        <p class="text-xs font-semibold">Select a conversation thread from the inbox to start live chatting</p>
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
            placeholder="Type direct message to customer..." 
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
        <div class="w-14 h-14 rounded-full bg-brand-600 flex items-center justify-center font-bold text-lg text-white mx-auto shadow-lg">
          {{ inboxStore.selectedChat.sender_name[0] }}
        </div>
        <div class="text-sm font-extrabold text-slate-100">{{ inboxStore.selectedChat.sender_name }}</div>
        <div class="text-[10px] text-slate-500 font-mono">PSID: {{ inboxStore.selectedChat.sender_id }}</div>
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
          <span>Page:</span> <span class="font-bold text-slate-200">{{ inboxStore.selectedChat.page || 'N/A' }}</span>
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
    authStore.addToast('Message sent', 'success');
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
</script>
