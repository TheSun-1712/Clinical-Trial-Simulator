import React, { useEffect, useState, useRef } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend
} from 'recharts';
import { motion } from 'framer-motion';
import { BarChart2, RefreshCw, TrendingUp } from 'lucide-react';
import { useTrialStore } from '../store';

const API_BASE = 'http://localhost:8000';

export default function PolicyBenchmarks() {
  const { sessionId } = useTrialStore();
  const [benchmarks, setBenchmarks] = useState({ heuristic_reward: 0, trained_reward: 0, random_reward: 0 });
  const [diseaseData, setDiseaseData] = useState([]);
  const [phaseData, setPhaseData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const timerRef = useRef(null);

  const fetchBenchmarks = async () => {
    const sid = sessionId || 'default';
    try {
      // Benchmark totals
      const bRes = await fetch(`${API_BASE}/simulation/benchmarks/${sid}`);
      if (bRes.ok) {
        const b = await bRes.json();
        setBenchmarks(b);
        setLastUpdated(new Date());
      }

      // Disease efficiency (trained)
      const dRes = await fetch(`${API_BASE}/analytics/efficiency-by-disease?policy=trained`);
      if (dRes.ok) {
        const d = await dRes.json();
        const entries = Object.entries(d.disease_metrics || {}).map(([k, v]) => ({
          disease: k.replace('_', ' '),
          mean_reward: +(v.mean_reward ?? 0).toFixed(2),
          success_rate: +(v.success_rate ?? 0).toFixed(2),
        }));
        setDiseaseData(entries);
      }

      // Phase efficiency (heuristic vs trained)
      const hRes = await fetch(`${API_BASE}/analytics/efficiency-by-phase?policy=heuristic`);
      const tRes = await fetch(`${API_BASE}/analytics/efficiency-by-phase?policy=trained`);
      if (hRes.ok && tRes.ok) {
        const hData = await hRes.json();
        const tData = await tRes.json();
        const phases = Object.keys({ ...hData.phase_metrics, ...tData.phase_metrics });
        const merged = phases.map(p => ({
          phase: p,
          heuristic: +((hData.phase_metrics[p]?.mean_reward ?? 0)).toFixed(2),
          trained: +((tData.phase_metrics[p]?.mean_reward ?? 0)).toFixed(2),
        }));
        setPhaseData(merged);
      }
    } catch (e) {
      console.error('Benchmarks fetch failed', e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchBenchmarks();
    timerRef.current = setInterval(fetchBenchmarks, 30000); // refresh every 30s
    return () => clearInterval(timerRef.current);
  }, [sessionId]);

  const summaryBars = [
    { name: 'Trained RL', value: benchmarks.trained_reward, color: '#3b82f6' },
    { name: 'Heuristic', value: benchmarks.heuristic_reward, color: '#10b981' },
    { name: 'Random', value: benchmarks.random_reward, color: '#ef4444' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ padding: 12, background: 'rgba(59,130,246,0.15)', color: '#3b82f6', borderRadius: 14 }}>
            <BarChart2 size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>Policy Benchmarks</h2>
            <p style={{ fontSize: 12, color: '#475569', margin: 0 }}>
              Live comparison: RL Agent vs Heuristic vs Random
              {lastUpdated && ` · Updated ${lastUpdated.toLocaleTimeString()}`}
            </p>
          </div>
        </div>
        <motion.button
          onClick={fetchBenchmarks}
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          style={{
            padding: '8px 14px', borderRadius: 10, border: '1px solid rgba(59,130,246,0.3)',
            background: 'rgba(59,130,246,0.1)', color: '#3b82f6',
            display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, fontWeight: 700,
          }}
        >
          <RefreshCw size={12} /> Refresh
        </motion.button>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {summaryBars.map((p) => (
          <motion.div key={p.name} whileHover={{ y: -3 }} className="liquid-glass"
            style={{ padding: 20, borderTop: `3px solid ${p.color}` }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, color: '#475569', marginBottom: 8 }}>
              {p.name}
            </div>
            <div style={{ fontSize: 30, fontWeight: 900, color: p.color }}>
              {p.value >= 0 ? '+' : ''}{p.value.toFixed(2)}
            </div>
            <div style={{ fontSize: 11, color: '#334155', marginTop: 4 }}>Mean Total Reward</div>
          </motion.div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, flex: 1, minHeight: 0 }}>
        {/* Disease bar chart */}
        <div className="liquid-glass" style={{ padding: 24, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: 15, fontWeight: 800, margin: '0 0 16px 0' }}>Reward by Disease (Trained)</h3>
          {diseaseData.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
              No benchmark report found — run a benchmark first
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%" minHeight={200}>
              <BarChart data={diseaseData} margin={{ top: 4, right: 8, left: -20, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="disease" stroke="#334155" tick={{ fontSize: 10, fill: '#64748b', angle: -20, textAnchor: 'end' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                <Bar dataKey="mean_reward" fill="#3b82f6" name="Mean Reward" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Phase comparison */}
        <div className="liquid-glass" style={{ padding: 24, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: 15, fontWeight: 800, margin: '0 0 16px 0' }}>Heuristic vs RL by Phase</h3>
          {phaseData.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
              No phase data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%" minHeight={200}>
              <BarChart data={phaseData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="phase" stroke="#334155" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                <Legend iconType="circle" iconSize={8} />
                <Bar dataKey="heuristic" fill="#10b981" name="Heuristic" radius={[3, 3, 0, 0]} />
                <Bar dataKey="trained" fill="#3b82f6" name="Trained RL" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
