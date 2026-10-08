<template>
  <div class="fixed top-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
    <TransitionGroup name="toast">
      <div 
        v-for="toast in authStore.toasts" 
        :key="toast.id"
        :class="[
          'pointer-events-auto px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs font-semibold border backdrop-blur-lg transition-all duration-300 transform',
          toast.type === 'error' ? 'bg-rose-950/90 border-rose-500/30 text-rose-200 shadow-rose-950/50' :
          toast.type === 'success' ? 'bg-emerald-950/90 border-emerald-500/30 text-emerald-200 shadow-emerald-950/50' :
          'bg-indigo-950/90 border-indigo-500/30 text-indigo-200 shadow-indigo-950/50'
        ]"
      >
        <component 
          :is="toast.type === 'error' ? AlertCircle : toast.type === 'success' ? CheckCircle2 : Info" 
          class="w-4 h-4 shrink-0" 
        />
        <span>{{ toast.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth';
import { AlertCircle, CheckCircle2, Info } from 'lucide-vue-next';

const authStore = useAuthStore();
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
