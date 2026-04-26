import React, { useEffect, useState, useCallback } from 'react';
import { useTrialStore } from '../store';
import { FileCheck, AlertTriangle, Clock, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const API = 'http://localhost:8000';

const MILESTONES_META = [
  { key: 'ind_filed',       label: 'IND Filed',           icon: '📄', week: 0  },
  { key: 'phase1_start',    label: 'Phase I Start',       icon: '🔬', week: 4  },
  { key: 'phase1_complete', label: 'Phase I Complete',    icon: '✅', week: 26 },
  { key: 'eop2_meeting',    label: 'End-of-Phase 2',      icon: '🤝', week: 34 },
  { key: 'phase3_start',    label: 'Phase III Start',     icon: '🏥', week: 40 },
  { key: 'phase3_complete', label: 'Phase III Complete',  icon: '🎯', week: 92 },
  { key: 'nda_filed',       label: 'NDA Filed',           icon: '📋', week: 100},
];

const FDA_FLAG_CONFIG = {
  monitoring: { color: '#3b82f6', label: '📊 Monitoring', bg: 'rgba(59,130,246,0.1)' },
  clear:      { color: '#10b981', label: '✅ Clear', bg: 'rgba(16,185,129,0.1)' },
  warning:    { color: '#f59e0b', label: '⚠️ Warning', bg: 'rgba(245,158,11,0.1)' },
  hold:       { color: '#ef4444', label: '🛑 Clinical Hold', bg: 'rgba(239,68,68,0.15)' },
};

export default function RegulatoryTimeline() {
  const { sessionId } = useTrialStore();
  const [data, setData] = useState(null);

  const fetchData = useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo') return;
    try {
      const res = await window.fetch(`${API}/simulation/milestones/${sessionId}`);
      const d = await res.json();
      setData(d);
    } catch {}
  }, [sessionId]);

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 6000); return () => clearInterval(id); }, [fetchData]);

  const milestones = data?.milestones || {};
  const saeLog = data?.sae_log || [];
  const fdaCfg = FDA_FLAG_CONFIG[data?.fda_flag || 'monitoring'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ padding: 12, background: 'rgba(245,158,11,0.15)', color: '#f59e0b', borderRadius: 14 }}>
          <FileCheck size={24} />
        </div>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>Regulatory Timeline</h2>
          <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>IND → Phase I → EOP2 → Phase III → NDA · SAE reporting · FDA sentiment</p>
        </div>
        <div style={{
          marginLeft: 'auto', padding: '8px 16px', borderRadius: 10,
          background: fdaCfg.bg, color: fdaCfg.color, fontWeight: 700, fontSize: 13,
        }}>
          {fdaCfg.label}
        </div>
      </div>

      {/* Milestone timeline */}
      <div className="liquid-glass" style={{ padding: 28, position: 'relative' }}>
        <h3 style={{ margin: '0 0 24px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>
          Regulatory Milestones
        </h3>
        {/* Track line */}
        <div style={{ position: 'absolute', top: 76, left: 60, right: 60, height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 99 }}>
          <div style={{
            height: '100%', borderRadius: 99, background: 'linear-gradient(90deg, #10b981, #3b82f6)',
            width: `${(Object.values(milestones).filter(Boolean).length / MILESTONES_META.length) * 100}%`,
            transition: 'width 1s ease',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative' }}>
          {MILESTONES_META.map((ms, i) => {
            const done = milestones[ms.key];
            const isNext = !done && !MILESTONES_META.slice(0, i).some(m => !milestones[m.key] && m.key !== 'ind_filed');
            return (
              <motion.div
                key={ms.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, maxWidth: 90 }}
              >
                <div style={{
                  width: 44, height: 44, borderRadius: '50%', fontSize: 20,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: done ? 'rgba(16,185,129,0.2)' : isNext ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.04)',
                  border: `2px solid ${done ? '#10b981' : isNext ? '#3b82f6' : 'rgba(255,255,255,0.1)'}`,
                  boxShadow: isNext ? '0 0 12px rgba(59,130,246,0.4)' : 'none',
                  transition: 'all 0.4s ease',
                }}>
                  {done ? '✅' : ms.icon}
                </div>
                <div style={{ textAlign: 'center', fontSize: 10, fontWeight: done ? 700 : 400, color: done ? '#10b981' : isNext ? '#93c5fd' : '#334155', lineHeight: 1.3 }}>
                  {ms.label}
                </div>
                <div style={{ fontSize: 9, color: '#334155' }}>Wk {ms.week}</div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, flex: 1, minHeight: 0 }}>
        {/* FDA status */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ margin: 0, fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>FDA Status</h3>
          <div style={{ padding: '12px 16px', borderRadius: 12, background: fdaCfg.bg, borderLeft: `4px solid ${fdaCfg.color}` }}>
            <div style={{ fontWeight: 800, color: fdaCfg.color, marginBottom: 4 }}>{fdaCfg.label}</div>
            <div style={{ fontSize: 12, color: '#94a3b8' }}>{data?.recommendation || 'Awaiting data...'}</div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            {[
              { label: 'Sentiment', value: `${((data?.fda_sentiment ?? 0) * 100).toFixed(0)}%`, color: '#10b981' },
              { label: 'Amendments', value: data?.amendment_count ?? 0, color: '#8b5cf6' },
              { label: 'Pending SAEs', value: data?.pending_saes ?? 0, color: '#f59e0b' },
              { label: 'Overdue', value: data?.overdue_saes ?? 0, color: '#ef4444' },
            ].map(s => (
              <div key={s.label} style={{ flex: 1, textAlign: 'center', padding: '10px 6px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: 18, fontWeight: 900, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 9, color: '#475569', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
          {/* FDA sentiment gauge */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#475569', marginBottom: 4 }}>
              <span>FDA Sentiment</span><span>{((data?.fda_sentiment ?? 0) * 100).toFixed(0)}%</span>
            </div>
            <div style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 99 }}>
              <div style={{
                height: '100%', borderRadius: 99, transition: 'width 0.8s ease',
                width: `${Math.min(100, (data?.fda_sentiment ?? 0) * 100)}%`,
                background: `hsl(${Math.floor((data?.fda_sentiment ?? 0) * 120)}, 70%, 50%)`,
              }} />
            </div>
          </div>
        </div>

        {/* SAE log */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <h3 style={{ margin: '0 0 12px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>
            SAE Report Queue
          </h3>
          {saeLog.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 12 }}>
              <CheckCircle size={20} style={{ marginRight: 8, color: '#10b981' }} /> No SAEs reported
            </div>
          ) : (
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {saeLog.map((sae, i) => (
                <div key={i} style={{
                  padding: '8px 12px', borderRadius: 10, flexShrink: 0,
                  background: sae.filed ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.08)',
                  borderLeft: `3px solid ${sae.filed ? '#10b981' : '#ef4444'}`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>{sae.report_id} — {sae.term}</div>
                    <div style={{ fontSize: 10, color: '#475569' }}>
                      Grade {sae.grade} · Week {sae.week} · {sae.causality?.replace(/_/g, ' ')}
                    </div>
                  </div>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
                    color: sae.filed ? '#10b981' : '#ef4444',
                    background: sae.filed ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                  }}>
                    {sae.filed ? 'Filed' : 'Pending'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
