<template>
  <div class="h-full font-sans antialiased text-slate-100">
    <ToastContainer />

    <div v-if="isLoginRoute" class="h-full">
      <router-view />
    </div>

    <div v-else class="h-full flex flex-col md:flex-row overflow-hidden">
      <Sidebar />
      <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <Navbar />
        <div class="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from './stores/auth';
import { useInboxStore } from './stores/inbox';
import { useCommentsStore } from './stores/comments';
import Sidebar from './components/Sidebar.vue';
import Navbar from './components/Navbar.vue';
import ToastContainer from './components/ToastContainer.vue';

const route = useRoute();
const authStore = useAuthStore();
const inboxStore = useInboxStore();
const commentsStore = useCommentsStore();

const isLoginRoute = computed(() => route.name === 'Login');

onMounted(() => {
  authStore.initFromWindowData();
  inboxStore.initRealtimeListeners();
  commentsStore.initRealtimeListeners();
});
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
