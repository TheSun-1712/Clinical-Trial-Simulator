import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { api } from '../api';
import { TrendingUp, Award, DollarSign, Percent, RefreshCw } from 'lucide-react';

const POLICY_COLORS = {
  'Random Baseline': '#ef4444',
  'Heuristic Rules': '#f59e0b',
  'Trained AI Policy': '#10b981',
};

const CURVE_KEYS = [
  { key: 'random', label: 'Random Baseline', color: '#ef4444' },
  { key: 'heuristic', label: 'Heuristic Rules', color: '#f59e0b' },
  { key: 'trained', label: 'Trained AI Policy', color: '#10b981' },
];

const SkeletonRow = () => (
  <tr>
    {[1, 2, 3, 4].map((i) => (
      <td key={i} style={{ padding: '14px 16px' }}>
        <motion.div animate={{ opacity: [0.3, 0.7, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.1 }}
          style={{ height: 14, background: 'rgba(255,255,255,0.08)', borderRadius: 6 }} />
      </td>
    ))}
  </tr>
);

export default function PolicyBenchmarks() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const res = await api.runBenchmark();
    setData(res);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 800 }}>Policy <span style={{ color: '#3b82f6' }}>Benchmarks</span></h2>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Comparing trial coordinator strategies across key metrics</p>
        </div>
        <motion.button
          id="btn-refresh-benchmark"
          onClick={load}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', background: 'rgba(59,130,246,0.15)', border: '1px solid #3b82f640', borderRadius: 12, color: '#3b82f6', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
        >
          <RefreshCw size={14} /> Refresh
        </motion.button>
      </div>

      {/* Leaderboard Table */}
      <div className="liquid-glass" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {['Policy', 'Total Reward', 'Success Rate', 'Avg. Cost'].map((h) => (
                <th key={h} style={{ padding: '14px 16px', textAlign: 'left', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#475569', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <><SkeletonRow /><SkeletonRow /><SkeletonRow /></>
            ) : data?.results?.map((row, i) => (
              <motion.tr
                key={row.policy}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: i === data.results.length - 1 ? 'rgba(16,185,129,0.06)' : 'transparent' }}
              >
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {i === data.results.length - 1 && <Award size={14} style={{ color: '#10b981' }} />}
                    <span style={{ fontWeight: 700, color: POLICY_COLORS[row.policy] ?? '#f8fafc' }}>{row.policy}</span>
                  </div>
                </td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <TrendingUp size={14} style={{ color: row.total_reward >= 0 ? '#10b981' : '#ef4444' }} />
                    <span style={{ fontWeight: 700, color: row.total_reward >= 0 ? '#10b981' : '#ef4444' }}>{row.total_reward >= 0 ? '+' : ''}{row.total_reward}</span>
                  </div>
                </td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Percent size={12} style={{ color: '#94a3b8' }} />
                    <span style={{ fontWeight: 600 }}>{(row.success_rate * 100).toFixed(0)}%</span>
                    <div style={{ flex: 1, marginLeft: 6, height: 4, background: 'rgba(255,255,255,0.07)', borderRadius: 99, maxWidth: 80 }}>
                      <motion.div initial={{ width: 0 }} animate={{ width: `${row.success_rate * 100}%` }} transition={{ duration: 0.8, delay: i * 0.1 }}
                        style={{ height: '100%', background: POLICY_COLORS[row.policy], borderRadius: 99 }} />
                    </div>
                  </div>
                </td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8' }}>
                    <DollarSign size={12} />
                    <span style={{ fontWeight: 600 }}>{(row.avg_cost / 1_000_000).toFixed(1)}M</span>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Reward Curves Chart */}
      <div className="liquid-glass" style={{ padding: '20px', flex: 1, minHeight: 280 }}>
        <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 14 }}>Cumulative Reward Curves</h3>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={data?.reward_curves ?? []} margin={{ top: 4, right: 12, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="step" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} label={{ value: 'Episode Step', position: 'insideBottom', offset: -4, fill: '#475569', fontSize: 10 }} />
            <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
            <Tooltip contentStyle={{ background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12 }} />
            <Legend wrapperStyle={{ paddingTop: 12, fontSize: 12, color: '#94a3b8' }} />
            {CURVE_KEYS.map((c) => (
              <Line key={c.key} type="monotone" dataKey={c.key} name={c.label} stroke={c.color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
