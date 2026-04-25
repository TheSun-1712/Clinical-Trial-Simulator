import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useTrialStore } from '../store';
import { Beaker } from 'lucide-react';

export default function DrugComposition() {
  const { history } = useTrialStore();

  // If the backend history doesn't have composition, mock it based on step
  const data = history.map(h => ({
    week: h.week ?? h.step,
    a: h.composition?.a ?? Math.max(0, 0.4 - (h.step * 0.02)),
    b: h.composition?.b ?? Math.min(0.5, 0.3 + (h.step * 0.01)),
    c: h.composition?.c ?? Math.min(0.4, 0.3 + (h.step * 0.01)),
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ padding: 12, background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', borderRadius: 14 }}><Beaker size={24} /></div>
        <div>
          <h2 style={{ fontSize: 28, fontWeight: 900 }}>Drug Composition</h2>
          <p style={{ color: '#94a3b8', fontSize: 13 }}>Real-time optimization of component ratios (A/B/C)</p>
        </div>
      </div>

      <div className="liquid-glass" style={{ padding: 32, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 12, fill: '#475569' }} />
            <YAxis stroke="#334155" tick={{ fontSize: 12, fill: '#475569' }} />
            <Tooltip contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12 }} />
            <Area type="monotone" dataKey="a" stackId="1" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} name="Component A" />
            <Area type="monotone" dataKey="b" stackId="1" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} name="Component B" />
            <Area type="monotone" dataKey="c" stackId="1" stroke="#ec4899" fill="#ec4899" fillOpacity={0.6} name="Component C" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {['Component A', 'Component B', 'Component C'].map((name, i) => {
          const colors = ['#3b82f6', '#8b5cf6', '#ec4899'];
          const latest = data[data.length - 1] || { a: 0.33, b: 0.33, c: 0.33 };
          const val = i === 0 ? latest.a : i === 1 ? latest.b : latest.c;
          return (
            <div key={name} className="liquid-glass" style={{ padding: 20, borderTop: `4px solid ${colors[i]}` }}>
              <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{name}</div>
              <div style={{ fontSize: 28, fontWeight: 900, color: colors[i] }}>{(val * 100).toFixed(1)}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
