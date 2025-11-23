const PLANS_KEY = 'tutor_plans_v1';

function loadAllPlans() {
  try {
    const raw = localStorage.getItem(PLANS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

function saveAllPlans(data) {
  localStorage.setItem(PLANS_KEY, JSON.stringify(data));
}

export const planService = {
  getCurrentPlan(email) {
    const all = loadAllPlans();
    return all[email] || null;
  },
  createOrReplacePlan(email, plan) {
    const all = loadAllPlans();
    const now = new Date().toISOString();
    const saved = { ...plan, createdAt: now };
    all[email] = saved;
    saveAllPlans(all);
    return saved;
  },
  exportPlan(email) {
    const plan = this.getCurrentPlan(email);
    if (!plan) return null;
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
    return blob;
  }
};

export default planService;
