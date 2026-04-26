import React, { useEffect, useState, useCallback } from 'react';
import { useTrialStore } from '../store';
import { Shield, Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API = 'http://localhost:8000';

const DECISION_CONFIG = {
  continue:       { color: '#10b981', icon: '✅', bg: 'rgba(16,185,129,0.12)' },
  modify_protocol:{ color: '#f59e0b', icon: '🔧', bg: 'rgba(245,158,11,0.12)' },
  stop_safety:    { color: '#ef4444', icon: '🛑', bg: 'rgba(239,68,68,0.15)' },
  stop_efficacy:  { color: '#3b82f6', icon: '🏆', bg: 'rgba(59,130,246,0.12)' },
  stop_futility:  { color: '#8b5cf6', icon: '⚠️', bg: 'rgba(139,92,246,0.12)' },
  pending_review: { color: '#475569', icon: '⏳', bg: 'rgba(71,85,105,0.12)' },
};

function CountdownRing({ weeksLeft, totalWeeks = 8 }) {
  const pct = Math.max(0, Math.min(1, weeksLeft / totalWeeks));
  const r = 42, circ = 2 * Math.PI * r;
  const color = pct > 0.5 ? '#10b981' : pct > 0.25 ? '#f59e0b' : '#ef4444';
  return (
    <svg width={100} height={100} viewBox="0 0 100 100">
      <circle cx={50} cy={50} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={10} />
      <circle cx={50} cy={50} r={r} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round"
        strokeDasharray={`${circ * pct} ${circ}`} transform="rotate(-90 50 50)"
        style={{ transition: 'stroke-dasharray 1s ease' }} />
      <text x={50} y={47} textAnchor="middle" fontSize={22} fontWeight={900} fill={color}>{weeksLeft}</text>
      <text x={50} y={62} textAnchor="middle" fontSize={9} fill="#475569">wks to review</text>
    </svg>
  );
}

export default function DSMBConsole() {
  const { sessionId } = useTrialStore();
  const [data, setData] = useState(null);

  const fetchData = useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo') return;
    try {
      const res = await window.fetch(`${API}/simulation/dsmb/${sessionId}`);
      const d = await res.json();
      setData(d);
    } catch {}
  }, [sessionId]);

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 5000); return () => clearInterval(id); }, [fetchData]);

  const decisions = data?.all_decisions || [];
  const latest = data?.latest_decision;
  const weeksLeft = data?.next_review_week ?? 8;
  const latestCfg = DECISION_CONFIG[latest?.decision || 'pending_review'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ padding: 12, background: 'rgba(239,68,68,0.15)', color: '#ef4444', borderRadius: 14 }}>
          <Shield size={24} />
        </div>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>DSMB Console</h2>
          <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>Data Safety Monitoring Board · O'Brien-Fleming boundaries · Review every 8 weeks</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 18, flex: 1, minHeight: 0 }}>
        {/* Left: countdown + latest decision */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="liquid-glass" style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#475569' }}>Next Review</div>
            <CountdownRing weeksLeft={weeksLeft} />
            <div style={{ fontSize: 10, color: '#334155', textAlign: 'center' }}>Week {data?.week ?? '—'}</div>
          </div>

          {/* AE rates */}
          <div className="liquid-glass" style={{ padding: 18 }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#475569', marginBottom: 10 }}>AE Rates</div>
            {[
              { label: 'Treatment', value: data?.ae_rate_treatment, threshold: 0.20, color: '#ef4444' },
              { label: 'Control', value: data?.ae_rate_control, threshold: 0.05, color: '#3b82f6' },
            ].map(r => (
              <div key={r.label} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                  <span style={{ color: '#94a3b8' }}>{r.label}</span>
                  <span style={{ fontWeight: 700, color: (r.value ?? 0) > r.threshold ? '#ef4444' : '#10b981' }}>
                    {((r.value ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 99 }}>
                  <div style={{
                    height: '100%', borderRadius: 99,
                    width: `${Math.min(100, (r.value ?? 0) * 100 / r.threshold)}%`,
                    background: (r.value ?? 0) > r.threshold ? '#ef4444' : r.color,
                    transition: 'width 0.5s ease',
                  }} />
                </div>
                <div style={{ fontSize: 9, color: '#334155', marginTop: 2 }}>Threshold: {(r.threshold * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>

          {/* Latest decision */}
          {latest && (
            <div className="liquid-glass" style={{
              padding: 16, borderLeft: `4px solid ${latestCfg.color}`,
              background: latestCfg.bg,
            }}>
              <div style={{ fontSize: 18, marginBottom: 6 }}>{latestCfg.icon}</div>
              <div style={{ fontWeight: 800, fontSize: 13, color: latestCfg.color, textTransform: 'uppercase' }}>
                {latest.decision.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: 10, color: '#64748b', marginTop: 4, lineHeight: 1.5 }}>{latest.reasoning}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 10, color: '#475569' }}>
                <span>p={latest.p_value?.toFixed(4)}</span>
                <span>·</span>
                <span>CP={((latest.conditional_power ?? 0) * 100).toFixed(0)}%</span>
                <span>·</span>
                <span>Z={latest.z_stat?.toFixed(2)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Decision log */}
        <div className="liquid-glass" style={{ padding: 24, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <h3 style={{ margin: '0 0 16px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>
            Decision Log ({decisions.length} review{decisions.length !== 1 ? 's' : ''})
          </h3>
          {decisions.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 10, color: '#334155' }}>
              <Shield size={32} style={{ opacity: 0.3 }} />
              <p style={{ fontSize: 13 }}>No DSMB reviews yet — first review at week 8</p>
            </div>
          ) : (
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[...decisions].reverse().map((d, i) => {
                const cfg = DECISION_CONFIG[d.decision] || DECISION_CONFIG.continue;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    style={{
                      padding: '12px 16px', borderRadius: 12, flexShrink: 0,
                      background: cfg.bg, borderLeft: `3px solid ${cfg.color}`,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                      <span style={{ fontWeight: 800, fontSize: 12, color: cfg.color }}>
                        {cfg.icon} Week {d.week} — {d.decision.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span style={{ fontSize: 10, color: '#334155' }}>p={d.p_value?.toFixed(4)}</span>
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>{d.reasoning}</div>
                    <div style={{ marginTop: 6, display: 'flex', gap: 10, fontSize: 10, color: '#475569' }}>
                      <span>Conditional Power: <b style={{ color: (d.conditional_power ?? 0) > 0.20 ? '#10b981' : '#ef4444' }}>
                        {((d.conditional_power ?? 0) * 100).toFixed(0)}%
                      </b></span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
