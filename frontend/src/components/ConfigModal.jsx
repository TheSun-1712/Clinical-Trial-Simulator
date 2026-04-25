import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTrialStore } from '../store';
import { X, RotateCcw, Sliders } from 'lucide-react';

const DISEASES = [
  { value: 'type2_diabetes', label: 'Type 2 Diabetes' },
  { value: 'hypertension', label: 'Hypertension' },
  { value: 'nsclc', label: 'NSCLC (Lung Cancer)' },
];

const REWARD_MODES = [
  { value: 'text', label: 'Text Heuristic', desc: 'Fast — scores JSON validity & action quality' },
  { value: 'env_rollout', label: 'Env Rollout', desc: 'Accurate — full simulator rollout per step' },
];

export default function ConfigModal({ onClose }) {
  const { seed, rewardMode, disease, resetTrial } = useTrialStore();
  const [localSeed, setLocalSeed] = useState(seed);
  const [localMode, setLocalMode] = useState(rewardMode);
  const [localDisease, setLocalDisease] = useState(disease);
  const [loading, setLoading] = useState(false);

  const handleReset = async () => {
    setLoading(true);
    await resetTrial(Number(localSeed), localMode, localDisease);
    setLoading(false);
    onClose();
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 100,
          background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
        }}
      >
        <motion.div
          initial={{ scale: 0.92, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.92, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="liquid-glass"
          style={{ width: '100%', maxWidth: 480, padding: '28px 32px' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Sliders size={18} style={{ color: '#3b82f6' }} />
              <h2 style={{ fontWeight: 800, fontSize: 18 }}>Setup & Configuration</h2>
            </div>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}>
              <X size={20} />
            </button>
          </div>

          {/* Seed */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 8 }}>
              Random Seed (for determinism)
            </label>
            <input
              id="config-seed"
              type="number"
              value={localSeed}
              onChange={(e) => setLocalSeed(e.target.value)}
              style={{
                width: '100%', padding: '10px 14px', background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10,
                color: '#f8fafc', fontSize: 15, fontFamily: 'monospace', outline: 'none',
              }}
            />
          </div>

          {/* Disease */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 8 }}>Disease Model</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {DISEASES.map((d) => (
                <button
                  key={d.value}
                  id={`config-disease-${d.value}`}
                  onClick={() => setLocalDisease(d.value)}
                  style={{
                    padding: '10px 14px', borderRadius: 10, fontSize: 13, fontWeight: 600, textAlign: 'left', cursor: 'pointer',
                    background: localDisease === d.value ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.03)',
                    border: localDisease === d.value ? '1px solid #3b82f660' : '1px solid rgba(255,255,255,0.07)',
                    color: localDisease === d.value ? '#3b82f6' : '#94a3b8',
                    transition: 'all 0.2s',
                  }}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Reward Mode */}
          <div style={{ marginBottom: 28 }}>
            <label style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 8 }}>Reward Mode</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {REWARD_MODES.map((m) => (
                <button
                  key={m.value}
                  id={`config-mode-${m.value}`}
                  onClick={() => setLocalMode(m.value)}
                  style={{
                    padding: '10px 14px', borderRadius: 10, fontSize: 13, fontWeight: 600, textAlign: 'left', cursor: 'pointer',
                    background: localMode === m.value ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.03)',
                    border: localMode === m.value ? '1px solid #8b5cf660' : '1px solid rgba(255,255,255,0.07)',
                    color: localMode === m.value ? '#8b5cf6' : '#94a3b8',
                    transition: 'all 0.2s',
                  }}
                >
                  <div>{m.label}</div>
                  <div style={{ fontSize: 11, fontWeight: 400, marginTop: 2, color: localMode === m.value ? '#8b5cf6aa' : '#475569' }}>{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <motion.button
            id="btn-apply-reset"
            onClick={handleReset}
            disabled={loading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            style={{
              width: '100%', padding: '13px 20px', borderRadius: 12,
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              color: '#fff', fontWeight: 800, fontSize: 14, border: 'none', cursor: loading ? 'wait' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              boxShadow: '0 0 24px rgba(59,130,246,0.3)',
            }}
          >
            <RotateCcw size={15} />
            {loading ? 'Resetting Environment...' : 'Apply & Reset Trial'}
          </motion.button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
