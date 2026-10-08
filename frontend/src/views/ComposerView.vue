<template>
  <div class="space-y-6">
    <!-- AI Caption Generator Bar -->
    <div class="glass-panel p-4 rounded-2xl border border-amber-500/30 bg-gradient-to-r from-slate-900/90 via-amber-950/20 to-slate-900/90 flex flex-col sm:flex-row items-center gap-3">
      <div class="flex items-center gap-2 shrink-0">
        <Sparkles class="w-5 h-5 text-amber-400" />
        <span class="text-xs font-bold text-slate-200">AI Magic Caption Writer:</span>
      </div>
      <input 
        v-model="aiTopic" 
        placeholder="Enter post topic (e.g., Weekend Special Discount, New Product Launch)..." 
        class="flex-1 bg-slate-800/90 text-xs rounded-xl px-3.5 py-2 border border-slate-700 text-slate-200 focus:outline-none focus:border-amber-400 w-full"
      >
      <button 
        @click="handleAiCaption" 
        :disabled="composerStore.generatingAiCaption || !aiTopic.trim()" 
        class="px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-extrabold text-xs rounded-xl shadow flex items-center gap-1.5 shrink-0 disabled:opacity-50"
      >
        <Sparkles class="w-4 h-4" />
        <span>{{ composerStore.generatingAiCaption ? 'Writing...' : 'Generate Caption' }}</span>
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Post Form Editor -->
      <div class="lg:col-span-1 glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 class="font-display font-bold text-sm text-slate-100 flex items-center gap-2">
          <PenTool class="w-4 h-4 text-brand-400" /> Post Editor
        </h3>

        <div>
          <label class="text-xs font-semibold text-slate-400 block mb-1">Post Type</label>
          <select v-model="composerStore.postForm.post_type" class="w-full bg-slate-900 text-xs rounded-xl px-3 py-2 border border-slate-700 text-slate-200">
            <option value="Text">Text Post</option>
            <option value="Image">Single Photo</option>
            <option value="Video">Video Post</option>
            <option value="Carousel">Multi-Image Carousel</option>
          </select>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-400 block mb-1">Caption / Message</label>
          <textarea 
            v-model="composerStore.postForm.message" 
            rows="5" 
            placeholder="Write your Facebook post content here..." 
            class="w-full bg-slate-900 text-xs rounded-xl p-3 border border-slate-700 text-slate-200 focus:outline-none focus:border-brand-500"
          ></textarea>
        </div>

        <div v-if="composerStore.postForm.post_type === 'Image' || composerStore.postForm.post_type === 'Carousel'">
          <label class="text-xs font-semibold text-slate-400 block mb-1">Image URL</label>
          <input 
            v-model="composerStore.postForm.media_url" 
            placeholder="https://..." 
            class="w-full bg-slate-900 text-xs rounded-xl px-3 py-2 border border-slate-700 text-slate-200"
          >
        </div>

        <div v-if="composerStore.postForm.post_type === 'Video'">
          <label class="text-xs font-semibold text-slate-400 block mb-1">Video URL</label>
          <input 
            v-model="composerStore.postForm.video_url" 
            placeholder="https://..." 
            class="w-full bg-slate-900 text-xs rounded-xl px-3 py-2 border border-slate-700 text-slate-200"
          >
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-400 block mb-1">Schedule Date & Time (Optional)</label>
          <input 
            type="datetime-local" 
            v-model="composerStore.postForm.schedule_time" 
            class="w-full bg-slate-900 text-xs rounded-xl px-3 py-2 border border-slate-700 text-slate-200"
          >
        </div>

        <div class="pt-2">
          <button 
            @click="handlePublish" 
            :disabled="composerStore.publishing || !composerStore.postForm.message.trim()" 
            class="w-full py-2.5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl text-xs shadow-lg shadow-brand-600/30 flex items-center justify-center gap-2 transition"
          >
            <Send class="w-4 h-4" />
            <span>{{ composerStore.postForm.schedule_time ? 'Schedule Post' : 'Publish Now' }}</span>
          </button>
        </div>
      </div>

      <!-- Live Facebook Post Mockup Preview & Feed -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Mockup Card -->
        <div class="glass-panel p-5 rounded-2xl border border-brand-500/40 bg-slate-900/70 space-y-3">
          <div class="flex items-center justify-between text-xs font-bold text-brand-300 uppercase tracking-wider">
            <span class="flex items-center gap-1.5"><Eye class="w-4 h-4 text-emerald-400" /> Live Meta Post Preview</span>
            <span class="bg-brand-500/20 text-brand-300 text-[10px] px-2 py-0.5 rounded border border-brand-500/30">Mockup</span>
          </div>

          <div class="glass-card p-4 rounded-2xl border border-slate-700 space-y-3 bg-slate-950">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-brand-600 flex items-center justify-center font-bold text-xs text-white">f</div>
              <div>
                <div class="text-xs font-bold text-slate-100">{{ authStore.selectedPage?.page_name || 'Paperware Factory' }}</div>
                <div class="text-[10px] text-slate-500">Just Now · 🌎 Public</div>
              </div>
            </div>

            <p class="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
              {{ composerStore.postForm.message || 'Your post caption will be dynamically previewed here in real time as you type...' }}
            </p>

            <div v-if="composerStore.postForm.media_url" class="rounded-xl overflow-hidden max-h-64 bg-slate-900">
              <img :src="composerStore.postForm.media_url" class="w-full h-full object-cover">
            </div>

            <div class="flex items-center justify-between pt-2 border-t border-slate-800 text-xs text-slate-400">
              <span class="flex items-center gap-1"><ThumbsUp class="w-3.5 h-3.5 text-blue-400" /> Like</span>
              <span class="flex items-center gap-1"><MessageSquare class="w-3.5 h-3.5 text-emerald-400" /> Comment</span>
              <span class="flex items-center gap-1"><Share2 class="w-3.5 h-3.5 text-purple-400" /> Share</span>
            </div>
          </div>
        </div>

        <!-- Page Feed -->
        <div class="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-display font-bold text-sm text-slate-100">Page Posts Feed</h3>
            <button @click="refreshFeed" class="text-xs text-slate-400 hover:text-slate-200"><RotateCw class="w-3.5 h-3.5" /></button>
          </div>

          <div class="space-y-4">
            <div v-for="post in composerStore.posts" :key="post.name" class="glass-card p-5 rounded-2xl border border-slate-800 space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center font-bold text-xs text-white">f</div>
                  <div>
                    <div class="text-xs font-bold text-slate-200">{{ post.page_name || 'Facebook Page' }}</div>
                    <div class="text-[10px] text-slate-500">{{ post.created_time || '' }}</div>
                  </div>
                </div>
                <span class="text-[10px] font-semibold bg-slate-800 text-brand-300 px-2.5 py-1 rounded-full border border-slate-700">{{ post.post_type }}</span>
              </div>

              <p class="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">{{ post.message }}</p>

              <div class="flex items-center gap-6 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
                <span class="flex items-center gap-1.5"><ThumbsUp class="w-4 h-4 text-blue-400" /> {{ post.like_count || 0 }} Likes</span>
                <span class="flex items-center gap-1.5"><MessageSquare class="w-4 h-4 text-emerald-400" /> {{ post.comment_count || 0 }} Comments</span>
                <span class="flex items-center gap-1.5"><Share2 class="w-4 h-4 text-purple-400" /> {{ post.share_count || 0 }} Shares</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useComposerStore } from '../stores/composer';
import { useAuthStore } from '../stores/auth';
import { Sparkles, PenTool, Send, Eye, ThumbsUp, MessageSquare, Share2, RotateCw } from 'lucide-vue-next';

const composerStore = useComposerStore();
const authStore = useAuthStore();

const aiTopic = ref('');

onMounted(() => {
  composerStore.fetchPosts(authStore.selectedPageId);
});

function refreshFeed() {
  composerStore.fetchPosts(authStore.selectedPageId);
}

async function handleAiCaption() {
  const caption = await composerStore.generateCaption(aiTopic.value);
  if (caption) {
    authStore.addToast('AI Caption generated', 'success');
  }
}

async function handlePublish() {
  const ok = await composerStore.publishPost(authStore.selectedPageId);
  if (ok) {
    authStore.addToast('Post published successfully', 'success');
  }
}
</script>
