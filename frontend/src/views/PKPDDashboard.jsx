import React, { useEffect, useState, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { useTrialStore } from '../store';
import { Beaker, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const API = 'http://localhost:8000';
const COLORS = { c_central: '#3b82f6', c_peripheral: '#8b5cf6', auc: '#10b981' };

function RangeBadge({ range }) {
  const cfg = {
    therapeutic: { color: '#10b981', bg: 'rgba(16,185,129,0.15)', label: '✅ Therapeutic' },
    sub_therapeutic: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)', label: '⚠️ Sub-Therapeutic' },
    toxic: { color: '#ef4444', bg: 'rgba(239,68,68,0.15)', label: '🔴 Toxic' },
  }[range] || { color: '#475569', bg: 'rgba(71,85,105,0.15)', label: range };
  return (
    <span style={{ padding: '4px 12px', borderRadius: 8, background: cfg.bg, color: cfg.color, fontWeight: 700, fontSize: 12 }}>
      {cfg.label}
    </span>
  );
}

export default function PKPDDashboard() {
  const { sessionId } = useTrialStore();
  const [data, setData] = useState(null);

  const fetch = useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo') return;
    try {
      const res = await window.fetch(`${API}/simulation/pkpd/${sessionId}`);
      const d = await res.json();
      setData(d);
    } catch {}
  }, [sessionId]);

  useEffect(() => { fetch(); const id = setInterval(fetch, 5000); return () => clearInterval(id); }, [fetch]);

  const ts = data?.timeseries || [];
  const mec = data?.mec ?? 0.15;
  const mtc = data?.mtc ?? 0.80;

  const stats = [
    { label: 'C Central (mg/L)', value: data?.c_central?.toFixed(4) ?? '—', color: '#3b82f6' },
    { label: 'C Peripheral', value: data?.c_peripheral?.toFixed(4) ?? '—', color: '#8b5cf6' },
    { label: 'AUC (mg·wk/L)', value: data?.auc?.toFixed(2) ?? '—', color: '#10b981' },
    { label: 'Cmax (mg/L)', value: data?.cmax?.toFixed(4) ?? '—', color: '#f59e0b' },
    { label: 't½ (weeks)', value: data?.t_half_weeks?.toFixed(2) ?? '—', color: '#06b6d4' },
    { label: 'Dose Level', value: data?.dose_level?.toFixed(2) ?? '—', color: '#a78bfa' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ padding: 12, background: 'rgba(59,130,246,0.15)', color: '#3b82f6', borderRadius: 14 }}>
            <Beaker size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>PK/PD Dashboard</h2>
            <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>Two-compartment pharmacokinetic model · Hill-equation PD</p>
          </div>
        </div>
        {data && <RangeBadge range={data.therapeutic_range} />}
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12 }}>
        {stats.map(s => (
          <motion.div key={s.label} whileHover={{ y: -2 }} className="liquid-glass" style={{ padding: '14px 16px' }}>
            <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: 1, color: '#475569', marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontSize: 20, fontWeight: 900, color: s.color }}>{s.value}</div>
          </motion.div>
        ))}
      </div>

      {/* Concentration-time chart */}
      <div className="liquid-glass" style={{ flex: 1, padding: 24, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>
            Plasma Concentration vs Time
          </h3>
          <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#475569' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 24, height: 2, background: '#f59e0b', display: 'inline-block' }} /> MEC ({mec})
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 24, height: 2, background: '#ef4444', display: 'inline-block' }} /> MTC ({mtc})
            </span>
          </div>
        </div>
        {ts.length < 2 ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
            Take simulation steps to build the PK curve
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={ts} margin={{ top: 4, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} label={{ value: 'Week', position: 'insideBottom', offset: -4, fill: '#475569', fontSize: 10 }} />
              <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} label={{ value: 'Conc (mg/L)', angle: -90, position: 'insideLeft', fill: '#475569', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
              <Legend iconSize={8} />
              <ReferenceLine y={mec} stroke="#f59e0b" strokeDasharray="6 3" label={{ value: 'MEC', fill: '#f59e0b', fontSize: 9 }} />
              <ReferenceLine y={mtc} stroke="#ef4444" strokeDasharray="6 3" label={{ value: 'MTC', fill: '#ef4444', fontSize: 9 }} />
              <Line type="monotone" dataKey="c_central" stroke={COLORS.c_central} strokeWidth={2.5} dot={false} name="Central" />
              <Line type="monotone" dataKey="c_peripheral" stroke={COLORS.c_peripheral} strokeWidth={1.5} strokeDasharray="5 3" dot={false} name="Peripheral" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Dose recommendation */}
      {data?.dose_recommendation && data.dose_recommendation !== data.dose_level && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="liquid-glass"
          style={{ padding: '14px 20px', borderLeft: '4px solid #f59e0b', display: 'flex', alignItems: 'center', gap: 12 }}
        >
          <AlertTriangle size={18} style={{ color: '#f59e0b', flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>PK Agent Dose Recommendation</div>
            <div style={{ fontSize: 12, color: '#94a3b8' }}>
              Current: {data.dose_level?.toFixed(2)} → Recommended: <strong style={{ color: '#f59e0b' }}>{data.dose_recommendation?.toFixed(2)}</strong>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
