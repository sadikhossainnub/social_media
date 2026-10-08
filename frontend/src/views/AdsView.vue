<template>
  <div class="space-y-6">
    <div class="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="font-display font-bold text-base text-slate-100 flex items-center gap-2">
            <Megaphone class="w-5 h-5 text-brand-400" />
            Facebook Ads & Campaign Hierarchy
          </h3>
          <p class="text-xs text-slate-400">Manage campaigns, ad sets, spend limits and performance stats</p>
        </div>

        <button @click="refresh" class="text-xs text-slate-400 hover:text-slate-200 p-2">
          <RotateCw :class="['w-4 h-4', adsStore.loading ? 'animate-spin text-brand-400' : '']" />
        </button>
      </div>

      <!-- Ads KPI Summary Row -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
        <div class="glass-card p-4 rounded-xl border border-slate-800 text-xs">
          <div class="text-slate-400 font-semibold mb-1">Total Ad Spend</div>
          <div class="text-xl font-extrabold text-slate-100">${{ adsStore.totalSpend.toFixed(2) }}</div>
        </div>
        <div class="glass-card p-4 rounded-xl border border-slate-800 text-xs">
          <div class="text-slate-400 font-semibold mb-1">Total Impressions</div>
          <div class="text-xl font-extrabold text-indigo-300">{{ adsStore.totalImpressions.toLocaleString() }}</div>
        </div>
        <div class="glass-card p-4 rounded-xl border border-slate-800 text-xs">
          <div class="text-slate-400 font-semibold mb-1">Total Clicks</div>
          <div class="text-xl font-extrabold text-brand-300">{{ adsStore.totalClicks.toLocaleString() }}</div>
        </div>
        <div class="glass-card p-4 rounded-xl border border-slate-800 text-xs">
          <div class="text-slate-400 font-semibold mb-1">Average CTR</div>
          <div class="text-xl font-extrabold text-emerald-300">{{ adsStore.avgCtr }}%</div>
        </div>
      </div>
    </div>

    <!-- Campaigns Tree View -->
    <div class="space-y-4">
      <div v-if="adsStore.campaignsTree.length === 0" class="p-12 text-center text-xs text-slate-500 glass-panel rounded-2xl">
        No active Facebook Ad campaigns found.
      </div>

      <div 
        v-for="camp in adsStore.campaignsTree" 
        :key="camp.name" 
        class="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4"
      >
        <!-- Campaign Header -->
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow">
              C
            </div>
            <div>
              <h4 class="text-sm font-bold text-slate-100">{{ camp.campaign_name || camp.name }}</h4>
              <div class="text-[10px] text-slate-400">Objective: {{ camp.objective || 'TRAFFIC' }} · ID: {{ camp.campaign_id || camp.name }}</div>
            </div>
          </div>

          <div class="flex items-center gap-4 text-xs">
            <span :class="['px-2.5 py-0.5 rounded-full font-extrabold text-[10px]', camp.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300']">
              {{ camp.status || 'PAUSED' }}
            </span>
            <div class="text-slate-300 font-bold">Spend: ${{ camp.spend || 0 }}</div>
          </div>
        </div>

        <!-- Ad Sets List -->
        <div class="pl-4 space-y-3 border-l-2 border-slate-800/80">
          <div 
            v-for="adset in camp.ad_sets" 
            :key="adset.name" 
            class="glass-card p-4 rounded-xl border border-slate-800 space-y-3"
          >
            <div class="flex items-center justify-between text-xs">
              <span class="font-bold text-brand-300 flex items-center gap-1.5">
                <Folder class="w-3.5 h-3.5" /> Ad Set: {{ adset.adset_name || adset.name }}
              </span>
              <span class="text-slate-400">Daily Budget: ${{ adset.daily_budget || 0 }}</span>
            </div>

            <!-- Ads List -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              <div 
                v-for="ad in adset.ads" 
                :key="ad.name" 
                class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-start gap-3 text-xs"
              >
                <div v-if="ad.image_url" class="w-12 h-12 rounded-lg bg-slate-900 overflow-hidden shrink-0">
                  <img :src="ad.image_url" class="w-full h-full object-cover">
                </div>
                <div class="flex-1 min-w-0">
                  <div class="font-bold text-slate-200 truncate">{{ ad.ad_name || ad.name }}</div>
                  <div class="text-[10px] text-slate-400 line-clamp-1">{{ ad.headline || ad.body_text }}</div>
                  <div class="mt-1 flex items-center justify-between text-[10px] text-slate-400">
                    <span>Clicks: {{ ad.clicks || 0 }}</span>
                    <span>Spend: ${{ ad.spend || 0 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useAdsStore } from '../stores/ads';
import { Megaphone, RotateCw, Folder } from 'lucide-vue-next';

const adsStore = useAdsStore();

onMounted(() => {
  adsStore.fetchAdsTree();
});

function refresh() {
  adsStore.fetchAdsTree();
}
</script>
