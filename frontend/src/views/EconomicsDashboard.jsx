import React, { useEffect, useState, useCallback } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useTrialStore } from '../store';
import { DollarSign, TrendingDown, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

const API = 'http://localhost:8000';

const COST_COLORS = {
  drug: '#3b82f6',
  site: '#8b5cf6',
  recruitment: '#f59e0b',
  regulatory: '#ef4444',
  overhead: '#475569',
};

const WTP = 100_000;

function ICERGauge({ icer }) {
  const pct = Math.min(1, icer / (WTP * 2));
  const color = icer <= WTP ? '#10b981' : icer <= WTP * 1.5 ? '#f59e0b' : '#ef4444';
  const angle = -135 + pct * 270;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const cx = 80, cy = 80, r = 56;
  const x = cx + r * Math.cos(toRad(angle));
  const y = cy + r * Math.sin(toRad(angle));
  return (
    <svg width={160} height={140} viewBox="0 0 160 140">
      {/* Track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={14}
        strokeDasharray={`${r * Math.PI * 1.5} ${r * Math.PI * 0.5}`} transform={`rotate(-225 ${cx} ${cy})`} />
      {/* Green zone */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(16,185,129,0.3)" strokeWidth={14}
        strokeDasharray={`${r * Math.PI * 0.75} ${r * Math.PI * 1.25}`} transform={`rotate(-225 ${cx} ${cy})`} />
      {/* Needle */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={14} strokeLinecap="round"
        strokeDasharray={`${r * Math.PI * 1.5 * pct} ${r * Math.PI * 2}`} transform={`rotate(-225 ${cx} ${cy})`}
        style={{ transition: 'stroke-dasharray 1s ease, stroke 0.5s ease' }} />
      {/* Value */}
      <text x={cx} y={cy + 8} textAnchor="middle" fontSize={12} fontWeight={900} fill={color}>
        ${Math.round(icer / 1000)}k
      </text>
      <text x={cx} y={cy + 22} textAnchor="middle" fontSize={8} fill="#475569">/QALY</text>
      {/* Labels */}
      <text x={18} y={130} fontSize={8} fill="#10b981">$0</text>
      <text x={130} y={130} fontSize={8} fill="#ef4444">${(WTP * 2 / 1000).toFixed(0)}k</text>
      <text x={cx} y={138} textAnchor="middle" fontSize={8} fill="#475569">WTP: ${WTP / 1000}k</text>
    </svg>
  );
}

export default function EconomicsDashboard() {
  const { sessionId } = useTrialStore();
  const [data, setData] = useState(null);

  const fetchData = useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo') return;
    try {
      const res = await window.fetch(`${API}/simulation/economics/${sessionId}`);
      const d = await res.json();
      setData(d);
    } catch {}
  }, [sessionId]);

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 7000); return () => clearInterval(id); }, [fetchData]);

  // Cost waterfall data
  const costBreakdown = data?.cost_breakdown ? Object.entries(data.cost_breakdown).map(([k, v]) => ({
    name: k.charAt(0).toUpperCase() + k.slice(1),
    value: Math.round(v / 1000),
    color: COST_COLORS[k] || '#475569',
  })) : [];

  const costHistory = (data?.cost_history || []).map(h => ({
    ...h,
    total_m: +(h.total_cost / 1_000_000).toFixed(2),
    icer_k: +(h.icer / 1000).toFixed(1),
  }));

  const isWTP = (data?.icer ?? WTP * 2) <= WTP;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ padding: 12, background: 'rgba(245,158,11,0.15)', color: '#f59e0b', borderRadius: 14 }}>
          <DollarSign size={24} />
        </div>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>Pharmacoeconomics</h2>
          <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>ICER · QALY · NDA probability · Cost waterfall</p>
        </div>
        {data?.recommendation && (
          <div style={{
            marginLeft: 'auto', padding: '8px 14px', borderRadius: 10, maxWidth: 360,
            background: isWTP ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
            border: `1px solid ${isWTP ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
            fontSize: 12,
          }}>
            {data.recommendation}
          </div>
        )}
      </div>

      {/* Top stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        {[
          { label: 'Total Cost', value: `$${((data?.total_trial_cost ?? 0) / 1_000_000).toFixed(1)}M`, color: '#ef4444' },
          { label: 'Cost / Patient', value: `$${((data?.cost_per_patient ?? 0)).toLocaleString()}`, color: '#f59e0b' },
          { label: 'Δ QALY', value: (data?.incremental_qaly ?? 0).toFixed(3), color: '#3b82f6' },
          { label: 'NDA Probability', value: `${((data?.nda_probability ?? 0) * 100).toFixed(0)}%`, color: '#10b981' },
          { label: 'WTP Status', value: isWTP ? '✅ Acceptable' : '⚠️ Borderline', color: isWTP ? '#10b981' : '#f59e0b' },
        ].map(s => (
          <motion.div key={s.label} whileHover={{ y: -2 }} className="liquid-glass" style={{ padding: '14px 16px' }}>
            <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: 1, color: '#475569', marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 16, fontWeight: 900, color: s.color }}>{s.value}</div>
          </motion.div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 1fr', gap: 18, flex: 1, minHeight: 0 }}>
        {/* ICER gauge */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#475569' }}>ICER</div>
          <ICERGauge icer={data?.icer ?? 0} />
          <div style={{ fontSize: 10, color: '#334155', textAlign: 'center' }}>
            {isWTP ? '✅ Cost-effective' : '⚠️ Above WTP threshold'}
          </div>
        </div>

        {/* Cost waterfall */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 12px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>Cost Breakdown ($k)</h3>
          {costBreakdown.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 12 }}>Take steps to build cost data</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={costBreakdown} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} tickFormatter={v => `$${v}k`} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} formatter={v => `$${v}k`} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} name="Cost ($k)">
                  {costBreakdown.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* ICER trend */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 12px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>Cost & ICER Trend</h3>
          {costHistory.length < 2 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 12 }}>Take steps to build history</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={costHistory} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} />
                <YAxis yAxisId="cost" stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} tickFormatter={v => `$${v}M`} />
                <YAxis yAxisId="icer" orientation="right" stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} tickFormatter={v => `${v}k`} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                <Line yAxisId="cost" type="monotone" dataKey="total_m" stroke="#ef4444" strokeWidth={2} dot={false} name="Total Cost ($M)" />
                <Line yAxisId="icer" type="monotone" dataKey="icer_k" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="ICER ($k/QALY)" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
