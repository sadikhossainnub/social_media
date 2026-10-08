<template>
  <div class="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h3 class="font-display font-bold text-base text-slate-100 flex items-center gap-2">
          <CalendarIcon class="w-5 h-5 text-brand-400" />
          Content Publishing Calendar
        </h3>
        <p class="text-xs text-slate-400">Schedule and manage automated Facebook page posts</p>
      </div>

      <div class="flex items-center gap-3">
        <router-link to="/composer" class="block">
          <button class="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl shadow-lg flex items-center gap-2 transition">
            <Plus class="w-4 h-4" /> Schedule New Post
          </button>
        </router-link>
        <button @click="refresh" class="text-xs text-slate-400 hover:text-slate-200 p-2">
          <RotateCw :class="['w-4 h-4', calendarStore.loading ? 'animate-spin text-brand-400' : '']" />
        </button>
      </div>
    </div>

    <!-- Calendar Entries Grid -->
    <div v-if="calendarStore.entries.length === 0" class="p-12 text-center text-xs text-slate-500 glass-card rounded-2xl">
      No posts scheduled in the calendar yet.
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div 
        v-for="cal in calendarStore.entries" 
        :key="cal.name" 
        class="glass-card p-5 rounded-2xl border border-slate-800 space-y-3 relative group"
      >
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center gap-1.5 font-bold text-brand-300">
            <Clock class="w-3.5 h-3.5 text-brand-400" />
            <span>{{ cal.scheduled_date }} {{ cal.scheduled_time || '' }}</span>
          </div>
          <span 
            :class="[
              'text-[10px] px-2.5 py-0.5 rounded-full font-bold',
              cal.status === 'Published' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
              cal.status === 'Failed' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
              'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            ]"
          >
            {{ cal.status }}
          </span>
        </div>

        <h4 class="text-xs font-bold text-slate-100 truncate">{{ cal.title || 'Untitled Post' }}</h4>
        <p class="text-[11px] text-slate-400 line-clamp-3 leading-relaxed font-medium">
          {{ cal.content_preview || 'No content preview available' }}
        </p>

        <div class="pt-2 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500">
          <span>Page: {{ cal.page || 'Default' }}</span>
          <button 
            @click="openRescheduleModal(cal)" 
            class="text-brand-400 hover:text-brand-300 font-semibold text-[11px] flex items-center gap-1"
          >
            Reschedule <CalendarIcon class="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>

    <!-- Reschedule Modal -->
    <div v-if="editingCal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div class="w-full max-w-sm glass-panel p-6 rounded-2xl border border-slate-700 space-y-4 shadow-2xl">
        <h4 class="text-sm font-bold text-slate-100">Reschedule Post</h4>
        <div>
          <label class="text-xs text-slate-400 block mb-1">New Schedule Date & Time</label>
          <input 
            type="datetime-local" 
            v-model="newDateTime" 
            class="w-full bg-slate-900 text-xs rounded-xl p-2.5 border border-slate-700 text-slate-200"
          >
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button @click="editingCal = null" class="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl">Cancel</button>
          <button @click="saveReschedule" class="px-4 py-1.5 bg-brand-600 text-white text-xs font-bold rounded-xl shadow">Save Date</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useCalendarStore } from '../stores/calendar';
import { useAuthStore } from '../stores/auth';
import { Calendar as CalendarIcon, Plus, RotateCw, Clock } from 'lucide-vue-next';

const calendarStore = useCalendarStore();
const authStore = useAuthStore();

const editingCal = ref(null);
const newDateTime = ref('');

onMounted(() => {
  calendarStore.fetchCalendarEntries(authStore.selectedPageId);
});

function refresh() {
  calendarStore.fetchCalendarEntries(authStore.selectedPageId);
}

function openRescheduleModal(cal) {
  editingCal.value = cal;
  newDateTime.value = `${cal.scheduled_date}T${cal.scheduled_time || '12:00'}`;
}

async function saveReschedule() {
  if (!editingCal.value || !newDateTime.value) return;
  const dtFormatted = newDateTime.value.replace('T', ' ') + ':00';
  const ok = await calendarStore.reschedulePost(editingCal.value.name, dtFormatted);
  if (ok) {
    authStore.addToast('Post rescheduled successfully', 'success');
    editingCal.value = null;
  }
}
</script>
