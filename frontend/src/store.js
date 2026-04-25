import { create } from 'zustand';
import { api } from './api';

function mockObs(week = 0) {
  return {
    week,
    active: 24 + Math.round(Math.random() * 8),
    drug_concentration: parseFloat((0.45 + Math.random() * 0.4).toFixed(4)),
    efficacy_signal_estimate: parseFloat((0.38 + Math.random() * 0.35).toFixed(4)),
    cumulative_toxicity: parseFloat((0.08 + Math.random() * 0.18).toFixed(4)),
    fda_sentiment: parseFloat((0.62 + Math.random() * 0.25).toFixed(4)),
    fda_flag: ['monitoring', 'clear', 'monitoring'][Math.floor(Math.random() * 3)],
    disease_progression: parseFloat((45 + Math.random() * 30).toFixed(2)),
  };
}

function buildMockHistory(steps = 6) {
  return Array.from({ length: steps }, (_, i) => ({
    ...mockObs(i),
    drug_concentration: parseFloat((0.3 + i * 0.04 + Math.random() * 0.05).toFixed(4)),
    efficacy_signal_estimate: parseFloat((0.2 + i * 0.06 + Math.random() * 0.04).toFixed(4)),
    cumulative_toxicity: parseFloat((0.05 + i * 0.015 + Math.random() * 0.01).toFixed(4)),
  }));
}

export const useTrialStore = create((set, get) => ({
  // Session
  sessionId: null,
  seed: 42,
  rewardMode: 'text',
  disease: 'type2_diabetes',

  // State
  observation: null,
  metadata: null,
  diseases: {},
  totalReward: 0,
  stepNumber: 0,
  trialPhase: 'PRE-TRIAL',

  // History & Logs
  history: [],
  eventLog: [],

  // UI
  loading: true,
  actionLoading: false,
  error: null,

  // Actions
  initialize: async () => {
    set({ loading: true, error: null });
    try {
      const [metaRes, diseasesRes, resetRes] = await Promise.all([
        api.getMetadata().catch(() => ({ name: 'Clinical Trial Simulator', version: '1.0' })),
        api.getDiseaseProfiles(),
        api.reset(get().seed, get().rewardMode, get().disease),
      ]);
      const obs = resetRes.observation ?? resetRes;
      set({
        metadata: metaRes,
        diseases: diseasesRes.profiles ?? {},
        sessionId: resetRes.session_id ?? 'offline-demo',
        observation: obs,
        totalReward: 0,
        stepNumber: 0,
        trialPhase: 'PHASE I',
        history: buildMockHistory(6).map((h, i) => ({ ...h, step: i })),
        eventLog: [{
          id: Date.now(),
          time: new Date().toLocaleTimeString(),
          type: 'system',
          message: 'Environment initialized. Trial session started.',
          reward: null,
        }],
        loading: false,
      });
    } catch (err) {
      // Backend unavailable — run in full mock/demo mode
      const mockHistory = buildMockHistory(8);
      const obs = mockHistory[mockHistory.length - 1];
      set({
        error: err.message,
        sessionId: 'offline-demo',
        metadata: { name: 'Clinical Trial Simulator', version: '1.0' },
        diseases: {
          type2_diabetes: { name: 'Type 2 Diabetes', metric_name: 'HbA1c (%)' },
          hypertension:   { name: 'Hypertension',   metric_name: 'Systolic BP (mmHg)' },
          nsclc:          { name: 'NSCLC',           metric_name: 'Tumor Volume (cm³)' },
        },
        observation: obs,
        totalReward: parseFloat((Math.random() * 30 + 5).toFixed(2)),
        stepNumber: mockHistory.length - 1,
        trialPhase: 'PHASE I',
        history: mockHistory.map((h, i) => ({ ...h, step: i })),
        eventLog: [
          { id: Date.now() - 5000, time: new Date(Date.now() - 5000).toLocaleTimeString(), type: 'system',   message: 'Demo mode active — backend not reachable on port 8000.', reward: null },
          { id: Date.now() - 4000, time: new Date(Date.now() - 4000).toLocaleTimeString(), type: 'system',   message: 'Loaded synthetic patient cohort: Type 2 Diabetes (seed=42).', reward: null },
          { id: Date.now() - 3000, time: new Date(Date.now() - 3000).toLocaleTimeString(), type: 'positive', message: 'Action: recruit (magnitude=5)', reward: 3.14 },
          { id: Date.now() - 2000, time: new Date(Date.now() - 2000).toLocaleTimeString(), type: 'positive', message: 'Action: adjust_dose (magnitude=0.1)', reward: 1.87 },
          { id: Date.now() - 1000, time: new Date(Date.now() - 1000).toLocaleTimeString(), type: 'negative', message: 'Action: adjust_dose (magnitude=0.1) — toxicity spike', reward: -0.52 },
        ],
        loading: false,
      });
    }
  },

  resetTrial: async (seed, rewardMode, disease) => {
    set({ loading: true, error: null, seed, rewardMode, disease });
    try {
      const res = await api.reset(seed, rewardMode, disease);
      const obs = res.observation ?? res;
      set({
        sessionId: res.session_id ?? 'offline-demo',
        observation: obs,
        totalReward: 0,
        stepNumber: 0,
        trialPhase: 'PHASE I',
        history: [{ ...obs, step: 0 }],
        eventLog: [{ id: Date.now(), time: new Date().toLocaleTimeString(), type: 'system', message: `Trial reset. Seed: ${seed}, Mode: ${rewardMode}, Disease: ${disease}`, reward: null }],
        loading: false,
      });
    } catch (_) {
      // Mock reset in offline mode
      const mockHistory = buildMockHistory(4);
      const obs = mockHistory[mockHistory.length - 1];
      set({
        sessionId: 'offline-demo',
        observation: obs,
        totalReward: 0,
        stepNumber: 0,
        trialPhase: 'PHASE I',
        history: mockHistory.map((h, i) => ({ ...h, step: i })),
        eventLog: [{ id: Date.now(), time: new Date().toLocaleTimeString(), type: 'system', message: `[Mock] Reset. Seed: ${seed}, Mode: ${rewardMode}, Disease: ${disease}`, reward: null }],
        loading: false,
      });
    }
  },

  takeAction: async (action) => {
    const { sessionId, stepNumber, totalReward, history, eventLog } = get();
    if (!sessionId) return;
    set({ actionLoading: true });
    try {
      const res = await api.step(sessionId, action);
      const obs = res.observation ?? res;
      const reward = res.reward ?? 0;
      const newStep = stepNumber + 1;
      const newTotal = totalReward + reward;
      const phase = newStep < 5 ? 'PHASE I' : newStep < 12 ? 'PHASE II' : 'PHASE III';
      set({
        observation: obs, stepNumber: newStep, totalReward: newTotal, trialPhase: phase,
        history: [...history, { ...obs, step: newStep }],
        eventLog: [...eventLog, { id: Date.now(), time: new Date().toLocaleTimeString(), type: reward >= 0 ? 'positive' : 'negative', message: `Action: ${action.action_type ?? JSON.stringify(action)}`, reward }],
        actionLoading: false,
      });
    } catch (_) {
      // Mock step in offline mode
      const prev = get().observation;
      const reward = parseFloat((Math.random() * 6 - 1.5).toFixed(3));
      const newStep = stepNumber + 1;
      const obs = {
        ...prev,
        step: newStep,
        drug_concentration: parseFloat(Math.min(2, (prev.drug_concentration ?? 0.5) + (action.action_type === 'adjust_dose' ? (action.magnitude ?? 0) : 0) + (Math.random() - 0.48) * 0.04).toFixed(4)),
        efficacy_signal_estimate: parseFloat(Math.min(1, (prev.efficacy_signal_estimate ?? 0.4) + 0.02 + Math.random() * 0.03).toFixed(4)),
        cumulative_toxicity: parseFloat(Math.min(1, (prev.cumulative_toxicity ?? 0.1) + 0.01 + Math.random() * 0.015).toFixed(4)),
        fda_sentiment: parseFloat(Math.min(1, (prev.fda_sentiment ?? 0.6) + (Math.random() - 0.4) * 0.05).toFixed(4)),
        active: Math.max(0, (prev.active ?? 24) + (action.action_type === 'recruit' ? (action.magnitude ?? 5) : 0)),
        disease_progression: parseFloat(Math.max(0, (prev.disease_progression ?? 50) - 0.5 - Math.random()).toFixed(2)),
        fda_flag: reward > 2 ? 'clear' : reward < -1 ? 'warning' : 'monitoring',
      };
      const phase = newStep < 5 ? 'PHASE I' : newStep < 12 ? 'PHASE II' : 'PHASE III';
      set({
        observation: obs, stepNumber: newStep, totalReward: totalReward + reward, trialPhase: phase,
        history: [...history, obs],
        eventLog: [...eventLog, { id: Date.now(), time: new Date().toLocaleTimeString(), type: reward >= 0 ? 'positive' : 'negative', message: `[Mock] Action: ${action.action_type ?? JSON.stringify(action)}`, reward }],
        actionLoading: false,
      });
    }
  },
}));
