import React, { useEffect, useState, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts';
import { useTrialStore } from '../store';
import { BarChart2, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const API = 'http://localhost:8000';

function PowerGauge({ power }) {
  const pct = Math.min(1, power);
  const color = power >= 0.80 ? '#10b981' : power >= 0.60 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width={120} height={66} viewBox="0 0 120 66">
        <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={14} strokeLinecap="round" />
        <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke={color} strokeWidth={14} strokeLinecap="round"
          strokeDasharray={`${157 * pct} 157`} style={{ transition: 'stroke-dasharray 0.8s ease' }} />
        <text x={60} y={58} textAnchor="middle" fontSize={18} fontWeight={900} fill={color}>{(pct * 100).toFixed(0)}%</text>
        <text x={60} y={70} textAnchor="middle" fontSize={9} fill="#475569">POWER</text>
      </svg>
    </div>
  );
}

export default function StatisticalEngine() {
  const { sessionId } = useTrialStore();
  const [data, setData] = useState(null);

  const fetchData = useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo') return;
    try {
      const res = await window.fetch(`${API}/simulation/statistics/${sessionId}`);
      const d = await res.json();
      setData(d);
    } catch {}
  }, [sessionId]);

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 5000); return () => clearInterval(id); }, [fetchData]);

  const history = data?.stat_history || [];
  const subgroups = data?.subgroup_analysis || {};
  const pOk = (data?.p_value ?? 1) < 0.05;

  // Forest plot data
  const forestData = Object.entries(subgroups).map(([key, val]) => ({
    name: key.replace(/_/g, ' '),
    n: val.n,
    efficacy: +(val.mean_efficacy * 100).toFixed(1),
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ padding: 12, background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', borderRadius: 14 }}>
          <BarChart2 size={24} />
        </div>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>Statistical Engine</h2>
          <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>O'Brien-Fleming · Power analysis · Subgroup forest plot</p>
        </div>
        {data?.recommendation && (
          <div style={{
            marginLeft: 'auto', padding: '8px 14px', borderRadius: 10,
            background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.25)',
            fontSize: 12, maxWidth: 360,
          }}>
            {data.recommendation}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 14 }}>
        {[
          { label: 'p-Value', value: data?.p_value?.toFixed(5) ?? '—', color: pOk ? '#10b981' : '#ef4444', sub: pOk ? 'Significant' : 'Not significant' },
          { label: 'Effect Size (d)', value: data?.effect_size?.toFixed(3) ?? '—', color: '#3b82f6', sub: 'Cohen\'s d' },
          { label: '95% CI Lower', value: data?.ci_lower?.toFixed(3) ?? '—', color: '#8b5cf6', sub: 'Confidence interval' },
          { label: '95% CI Upper', value: data?.ci_upper?.toFixed(3) ?? '—', color: '#8b5cf6', sub: 'Confidence interval' },
        ].map(c => (
          <motion.div key={c.label} whileHover={{ y: -2 }} className="liquid-glass" style={{ padding: '16px 18px' }}>
            <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: 1, color: '#475569', marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: c.color }}>{c.value}</div>
            <div style={{ fontSize: 10, color: '#334155', marginTop: 2 }}>{c.sub}</div>
          </motion.div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 1fr', gap: 18, flex: 1, minHeight: 0 }}>
        {/* Power gauge */}
        <div className="liquid-glass" style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#475569' }}>Statistical Power</div>
          <PowerGauge power={data?.power ?? 0} />
          <div style={{ fontSize: 10, color: '#334155', textAlign: 'center' }}>
            N trt: {data?.n_treatment ?? '—'}<br />N ctrl: {data?.n_control ?? '—'}
          </div>
          <div style={{ fontSize: 10, color: '#475569', textAlign: 'center' }}>
            α spent: {((data?.alpha_spent ?? 0) * 100).toFixed(2)}%
          </div>
        </div>

        {/* Power curve over time */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 12px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>Power Curve Over Time</h3>
          {history.length < 2 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 12 }}>Take steps to build power history</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} formatter={v => `${(v * 100).toFixed(1)}%`} />
                <ReferenceLine y={0.80} stroke="#10b981" strokeDasharray="5 3" label={{ value: '80%', fill: '#10b981', fontSize: 9 }} />
                <Line type="monotone" dataKey="power" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Power" />
                <Line type="monotone" dataKey="p_value" stroke="#ef4444" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="p-value" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Forest plot */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 12px 0', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b' }}>Subgroup Forest Plot</h3>
          {forestData.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 12 }}>No patient data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={forestData} layout="vertical" margin={{ top: 4, right: 12, left: 60, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 9, fill: '#475569' }} tickFormatter={v => `${v}%`} stroke="#334155" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: '#94a3b8' }} stroke="#334155" width={56} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} formatter={v => `${v}%`} />
                <Bar dataKey="efficacy" radius={[0, 4, 4, 0]} name="Mean Efficacy">
                  {forestData.map((_, i) => <Cell key={i} fill={i % 2 === 0 ? '#3b82f6' : '#8b5cf6'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
