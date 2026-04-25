import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTrialStore } from '../store';
import { Terminal, CheckCircle2, XCircle, AlertCircle, Info } from 'lucide-react';

const TYPE_CONFIG = {
  system: { icon: <Info size={13} />, color: '#3b82f6', label: 'SYS' },
  positive: { icon: <CheckCircle2 size={13} />, color: '#10b981', label: 'OK+' },
  negative: { icon: <XCircle size={13} />, color: '#ef4444', label: 'NEG' },
  error: { icon: <AlertCircle size={13} />, color: '#f59e0b', label: 'ERR' },
};

export default function SystemLogs() {
  const { eventLog, sessionId, seed, rewardMode, disease, stepNumber, totalReward, trialPhase } = useTrialStore();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: 22, fontWeight: 800 }}>System <span style={{ color: '#3b82f6' }}>Logs</span></h2>
        <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Full audit trail of environment events and agent actions</p>
      </div>

      {/* Session Meta */}
      <div className="liquid-glass" style={{ padding: '16px 20px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {[
          { label: 'Session ID', value: sessionId ? sessionId.slice(0, 12) + '...' : '—' },
          { label: 'Seed', value: seed },
          { label: 'Reward Mode', value: rewardMode },
          { label: 'Disease', value: disease },
          { label: 'Current Phase', value: trialPhase },
          { label: 'Total Reward', value: typeof totalReward === 'number' ? totalReward.toFixed(3) : '—' },
        ].map((item) => (
          <div key={item.label}>
            <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, color: '#475569', marginBottom: 2 }}>{item.label}</div>
            <div style={{ fontWeight: 700, fontSize: 14, fontFamily: 'monospace', color: '#f8fafc' }}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* Log Terminal */}
      <div className="liquid-glass" style={{ flex: 1, padding: '16px 20px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Terminal size={14} style={{ color: '#3b82f6' }} />
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>Event Log</span>
          <div style={{ marginLeft: 'auto', padding: '2px 8px', background: 'rgba(59,130,246,0.15)', border: '1px solid #3b82f630', borderRadius: 99, fontSize: 11, color: '#3b82f6', fontWeight: 700 }}>
            {eventLog.length} events
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
          <AnimatePresence initial={false}>
            {eventLog.map((e, idx) => {
              const cfg = TYPE_CONFIG[e.type] ?? TYPE_CONFIG.system;
              return (
                <motion.div
                  key={e.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 10px', borderRadius: 8,
                    background: idx % 2 === 0 ? 'rgba(255,255,255,0.015)' : 'transparent',
                    fontFamily: 'monospace', fontSize: 12,
                  }}
                >
                  <span style={{ color: '#334155', minWidth: 55 }}>{e.time}</span>
                  <span style={{
                    padding: '2px 6px', borderRadius: 4, fontSize: 10, fontWeight: 700,
                    background: cfg.color + '20', color: cfg.color, minWidth: 34, textAlign: 'center',
                  }}>{cfg.label}</span>
                  <span style={{ color: cfg.color, flexShrink: 0 }}>{cfg.icon}</span>
                  <span style={{ color: '#94a3b8', flex: 1 }}>{e.message}</span>
                  {e.reward !== null && (
                    <span style={{ fontWeight: 800, color: e.reward >= 0 ? '#10b981' : '#ef4444' }}>
                      {e.reward >= 0 ? '+' : ''}{e.reward.toFixed(3)}
                    </span>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>

          {eventLog.length === 0 && (
            <div style={{ color: '#334155', fontSize: 13, textAlign: 'center', marginTop: 40 }}>
              No events yet. Initialize the environment to begin.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
