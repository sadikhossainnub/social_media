<template>
  <div class="h-screen w-screen flex items-center justify-center p-4 relative overflow-hidden">
    <!-- Animated Glass Background Glow -->
    <div class="absolute -top-32 -left-32 w-96 h-96 bg-brand-600/30 rounded-full blur-3xl animate-pulse"></div>
    <div class="absolute -bottom-32 -right-32 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl animate-pulse delay-1000"></div>

    <div class="w-full max-w-md glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl relative z-10 space-y-6">
      <div class="text-center space-y-2">
        <div class="w-16 h-16 rounded-3xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-sky-400 flex items-center justify-center mx-auto shadow-xl shadow-brand-500/30">
          <Share2 class="w-8 h-8 text-white" />
        </div>
        <h1 class="font-display font-extrabold text-2xl gradient-text">Social Desk</h1>
        <p class="text-xs text-slate-400">Log in to manage Facebook Page messages, comments, ads & team</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="text-xs font-semibold text-slate-300 block mb-1.5">Username or Email</label>
          <div class="relative">
            <User class="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            <input 
              v-model="username" 
              type="text" 
              required
              placeholder="Administrator or user@example.com" 
              class="w-full bg-slate-900/90 text-xs rounded-xl pl-10 pr-4 py-2.5 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500 transition"
            >
          </div>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-300 block mb-1.5">Password</label>
          <div class="relative">
            <Lock class="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            <input 
              v-model="password" 
              type="password" 
              required
              placeholder="••••••••" 
              class="w-full bg-slate-900/90 text-xs rounded-xl pl-10 pr-4 py-2.5 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500 transition"
            >
          </div>
        </div>

        <button 
          type="submit" 
          :disabled="authStore.loading" 
          class="w-full py-3 bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-700 hover:from-brand-500 hover:to-indigo-500 text-white font-extrabold text-xs rounded-xl shadow-lg shadow-brand-600/30 flex items-center justify-center gap-2 transition transform active:scale-95 disabled:opacity-50"
        >
          <Loader2 v-if="authStore.loading" class="w-4 h-4 animate-spin" />
          <LogIn v-else class="w-4 h-4" />
          <span>{{ authStore.loading ? 'Authenticating...' : 'Sign In to Portal' }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { Share2, User, Lock, LogIn, Loader2 } from 'lucide-vue-next';

const router = useRouter();
const authStore = useAuthStore();

const username = ref('');
const password = ref('');

async function handleLogin() {
  const ok = await authStore.login(username.value, password.value);
  if (ok) {
    router.push('/inbox');
  }
}
</script>
