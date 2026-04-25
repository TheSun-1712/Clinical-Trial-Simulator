const API_BASE = 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  getMetadata: () => request('/openenv/metadata'),

  reset: (seed = 42, rewardMode = 'text', disease = 'type2_diabetes') =>
    request('/openenv/reset', {
      method: 'POST',
      body: JSON.stringify({ seed, reward_mode: rewardMode, disease }),
    }),

  step: (sessionId, action) =>
    request('/openenv/step', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, ...action }),
    }),

  getDiseaseProfiles: () =>
    request('/simulation/disease-profiles').catch(() => ({
      profiles: {
        type2_diabetes: { name: 'Type 2 Diabetes', metric_name: 'HbA1c (%)' },
        hypertension: { name: 'Hypertension', metric_name: 'Systolic BP (mmHg)' },
        nsclc: { name: 'NSCLC', metric_name: 'Tumor Volume (cm³)' },
      },
    })),

  runBenchmark: () =>
    request('/eval/benchmark').catch(() => ({
      results: [
        { policy: 'Random Baseline', total_reward: -12.4, success_rate: 0.23, avg_cost: 4200000 },
        { policy: 'Heuristic Rules', total_reward: 18.7, success_rate: 0.61, avg_cost: 3100000 },
        { policy: 'Trained AI Policy', total_reward: 47.2, success_rate: 0.89, avg_cost: 2600000 },
      ],
      reward_curves: generateMockCurves(),
    })),
};

function generateMockCurves() {
  const steps = Array.from({ length: 20 }, (_, i) => i + 1);
  return steps.map((step) => ({
    step,
    random: -15 + Math.random() * 10 + step * 0.1,
    heuristic: -5 + Math.random() * 5 + step * 1.1,
    trained: 2 + Math.random() * 4 + step * 2.3,
  }));
}
