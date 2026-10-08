<template>
  <div class="space-y-6">
    <div class="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 class="font-display font-bold text-base text-slate-100 flex items-center gap-2">
            <MessageCircle class="w-5 h-5 text-brand-400" />
            Comments & Sentiment Moderation
          </h3>
          <p class="text-xs text-slate-400">Monitor post comments, sentiment scoring, and AI auto-replies</p>
        </div>

        <div class="flex items-center gap-2">
          <!-- Sub-tabs: Moderation vs AI Approvals -->
          <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
            <button 
              @click="commentsStore.activeTab = 'moderation'" 
              :class="['px-3 py-1.5 rounded-lg transition', commentsStore.activeTab === 'moderation' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200']"
            >
              Moderation Grid
            </button>
            <button 
              @click="switchToAiApprovals" 
              :class="['px-3 py-1.5 rounded-lg transition flex items-center gap-1.5', commentsStore.activeTab === 'ai_approvals' ? 'bg-amber-600 text-white shadow' : 'text-slate-400 hover:text-slate-200']"
            >
              <Sparkles class="w-3.5 h-3.5 text-amber-300" />
              <span>AI Approvals</span>
              <span v-if="commentsStore.pendingAiCount > 0" class="bg-amber-400 text-slate-950 text-[10px] font-extrabold px-1.5 py-0.2 rounded-full">
                {{ commentsStore.pendingAiCount }}
              </span>
            </button>
          </div>

          <button @click="refresh" class="text-xs text-slate-400 hover:text-slate-200 p-2">
            <RotateCw :class="['w-4 h-4', commentsStore.loading ? 'animate-spin text-brand-400' : '']" />
          </button>
        </div>
      </div>

      <!-- Sentiment Filter Pills -->
      <div v-if="commentsStore.activeTab === 'moderation'" class="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span class="text-slate-400 font-bold uppercase text-[10px]">Filter:</span>
        <button 
          v-for="s in ['all', 'Positive', 'Neutral', 'Negative', 'Spam']" 
          :key="s" 
          @click="commentsStore.sentimentFilter = s"
          :class="[
            'px-3 py-1 rounded-full border text-xs font-semibold transition',
            commentsStore.sentimentFilter === s ? 'bg-brand-600 text-white border-brand-500 shadow' : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
          ]"
        >
          {{ s === 'all' ? 'All Comments' : s }}
        </button>
      </div>
    </div>

    <!-- Moderation Grid Tab -->
    <div v-if="commentsStore.activeTab === 'moderation'" class="space-y-4">
      <div v-if="commentsStore.filteredComments.length === 0" class="p-12 text-center text-xs text-slate-500 glass-panel rounded-2xl">
        No comments match the selected filter.
      </div>

      <div 
        v-for="comment in commentsStore.filteredComments" 
        :key="comment.name" 
        class="glass-card p-5 rounded-2xl border border-slate-800 space-y-3"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-200">{{ comment.commenter_name || 'Facebook User' }}</span>
              <span 
                :class="[
                  'text-[10px] px-2.5 py-0.5 rounded-full font-bold',
                  comment.sentiment === 'Positive' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                  comment.sentiment === 'Negative' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                  comment.sentiment === 'Spam' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' :
                  'bg-slate-800 text-slate-400 border border-slate-700'
                ]"
              >
                {{ comment.sentiment || 'Neutral' }}
              </span>
              <span v-if="comment.is_hidden" class="bg-amber-500/20 text-amber-300 text-[10px] font-bold px-2 py-0.5 rounded-full border border-amber-500/30">
                Hidden
              </span>
            </div>
            <p class="text-xs text-slate-300 font-medium leading-relaxed">{{ comment.message }}</p>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <button 
              @click="toggleReplyInput(comment.name)" 
              class="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl shadow flex items-center gap-1"
            >
              <Reply class="w-3.5 h-3.5" /> Reply
            </button>
            <button 
              @click="handleToggleHide(comment)" 
              class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700"
            >
              {{ comment.is_hidden ? 'Unhide' : 'Hide' }}
            </button>
          </div>
        </div>

        <!-- Replied Message callout -->
        <div v-if="comment.reply_message" class="text-xs bg-brand-950/40 p-3 rounded-xl border border-brand-800/40 text-brand-200 space-y-1">
          <div class="font-bold text-brand-400 flex items-center gap-1.5">
            <CheckCircle2 class="w-3.5 h-3.5 text-brand-400" /> Replied by Page:
          </div>
          <p class="text-slate-300">{{ comment.reply_message }}</p>
        </div>

        <!-- Inline Reply Input Drawer -->
        <div v-if="activeReplyId === comment.name" class="pt-2 flex gap-2">
          <input 
            v-model="replyText" 
            @keyup.enter="handleSendReply(comment)"
            placeholder="Type comment reply..." 
            class="flex-1 bg-slate-900 text-xs rounded-xl px-3.5 py-2 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
          >
          <button 
            @click="handleSendReply(comment)" 
            class="px-4 py-2 bg-gradient-to-r from-brand-600 to-indigo-600 text-white font-semibold text-xs rounded-xl shadow"
          >
            Send Reply
          </button>
        </div>
      </div>
    </div>

    <!-- AI Approvals Tab -->
    <div v-else-if="commentsStore.activeTab === 'ai_approvals'" class="space-y-4">
      <div v-if="commentsStore.aiReplies.length === 0" class="p-12 text-center text-xs text-slate-500 glass-panel rounded-2xl">
        No pending AI-suggested comment replies.
      </div>

      <div 
        v-for="ai in commentsStore.aiReplies" 
        :key="ai.name" 
        class="glass-card p-5 rounded-2xl border border-amber-500/30 bg-gradient-to-r from-slate-900/90 via-amber-950/20 to-slate-900/90 space-y-3"
      >
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            <Sparkles class="w-4 h-4 text-amber-400" />
            <span class="font-bold text-slate-200">Original Comment from {{ ai.comment_author || 'User' }}</span>
          </div>
          <span 
            :class="[
              'px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase',
              ai.approval_status === 'Approved' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
              ai.approval_status === 'Rejected' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
              'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            ]"
          >
            {{ ai.approval_status }}
          </span>
        </div>

        <p class="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800 italic">
          "{{ ai.original_comment }}"
        </p>

        <div class="space-y-1">
          <div class="text-[11px] font-bold text-amber-300 flex items-center gap-1.5">
            AI Generated Suggested Reply (Confidence: {{ (ai.confidence_score * 100).toFixed(0) }}%):
          </div>
          <p class="text-xs font-semibold text-slate-100 bg-amber-500/10 p-3 rounded-xl border border-amber-500/20">
            {{ ai.generated_reply }}
          </p>
        </div>

        <div v-if="ai.approval_status === 'Pending'" class="flex items-center gap-3 pt-2">
          <button 
            @click="approveAi(ai.name)" 
            class="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl shadow flex items-center gap-1.5"
          >
            <Check class="w-4 h-4" /> Approve & Publish
          </button>
          <button 
            @click="rejectAi(ai.name)" 
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-rose-300 font-bold text-xs rounded-xl border border-slate-700 flex items-center gap-1.5"
          >
            <X class="w-4 h-4" /> Reject
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useCommentsStore } from '../stores/comments';
import { useAuthStore } from '../stores/auth';
import { MessageCircle, RotateCw, Sparkles, Reply, CheckCircle2, Check, X } from 'lucide-vue-next';

const commentsStore = useCommentsStore();
const authStore = useAuthStore();

const activeReplyId = ref(null);
const replyText = ref('');

onMounted(() => {
  commentsStore.fetchComments(authStore.selectedPageId);
});

function refresh() {
  commentsStore.fetchComments(authStore.selectedPageId);
  if (commentsStore.activeTab === 'ai_approvals') {
    commentsStore.fetchAiReplies();
  }
}

function switchToAiApprovals() {
  commentsStore.activeTab = 'ai_approvals';
  commentsStore.fetchAiReplies();
}

function toggleReplyInput(commentId) {
  if (activeReplyId.value === commentId) {
    activeReplyId.value = null;
  } else {
    activeReplyId.value = commentId;
    replyText.value = '';
  }
}

async function handleSendReply(comment) {
  if (!replyText.value.trim()) return;
  const ok = await commentsStore.replyToComment(comment.comment_id || comment.name, replyText.value);
  if (ok) {
    authStore.addToast('Reply published successfully', 'success');
    activeReplyId.value = null;
    replyText.value = '';
  }
}

async function handleToggleHide(comment) {
  const ok = await commentsStore.toggleHideComment(comment);
  if (ok) {
    authStore.addToast(comment.is_hidden ? 'Comment hidden' : 'Comment unhidden', 'info');
  }
}

async function approveAi(name) {
  const ok = await commentsStore.approveAiReply(name);
  if (ok) {
    authStore.addToast('AI Reply approved & published', 'success');
  }
}

async function rejectAi(name) {
  const ok = await commentsStore.rejectAiReply(name);
  if (ok) {
    authStore.addToast('AI Reply rejected', 'info');
  }
}
</script>
