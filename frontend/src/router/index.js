import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

import LoginView from '../views/LoginView.vue';
import InboxView from '../views/InboxView.vue';
import CommentsView from '../views/CommentsView.vue';
import DashboardView from '../views/DashboardView.vue';
import CalendarView from '../views/CalendarView.vue';
import ComposerView from '../views/ComposerView.vue';
import LeadsView from '../views/LeadsView.vue';
import AdsView from '../views/AdsView.vue';
import TeamView from '../views/TeamView.vue';

const routes = [
  { path: '/login', name: 'Login', component: LoginView, meta: { public: true } },
  { path: '/inbox', name: 'Inbox', component: InboxView },
  { path: '/comments', name: 'Comments', component: CommentsView },
  { path: '/dashboard', name: 'Dashboard', component: DashboardView },
  { path: '/calendar', name: 'Calendar', component: CalendarView },
  { path: '/composer', name: 'Composer', component: ComposerView },
  { path: '/leads', name: 'Leads', component: LeadsView },
  { path: '/ads', name: 'Ads', component: AdsView },
  { path: '/team', name: 'Team', component: TeamView },
  { path: '/', redirect: '/inbox' },
  { path: '/:pathMatch(.*)*', redirect: '/inbox' }
];

const router = createRouter({
  // Use Hash history for seamless embedding within Frappe pages if needed
  history: createWebHashHistory(),
  routes
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  if (!authStore.user && !to.meta.public) {
    const success = await authStore.fetchSession();
    if (!success && to.path !== '/login') {
      return next({ name: 'Login' });
    }
  }

  if (to.name === 'Login' && authStore.isAuthenticated) {
    return next({ name: 'Inbox' });
  }

  next();
});

export default router;
