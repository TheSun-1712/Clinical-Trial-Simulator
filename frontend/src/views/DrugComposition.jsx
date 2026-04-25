import React, { useEffect, useState, useRef } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { useTrialStore } from '../store';
import { Beaker, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';

const API_BASE = 'http://localhost:8000';
const COLORS = { a: '#3b82f6', b: '#8b5cf6', c: '#ec4899' };

export default function DrugComposition() {
  const { sessionId, history } = useTrialStore();
  const [composition, setComposition] = useState({ a: 0.33, b: 0.33, c: 0.34 });
  const [doseLevel, setDoseLevel] = useState(1.0);
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef(null);

  const fetchComposition = async () => {
    if (!sessionId || sessionId === 'offline-demo') {
      // Derive composition changes from history via dose_level movements
      const mapped = history.map((h, i) => {
        const dose = h.dose_level ?? 1.0;
        const base = Math.max(0, 0.40 - i * 0.005);
        const shift = Math.min(0.35, 0.30 + i * 0.005);
        return {
          week: h.week ?? i,
          a: +(base).toFixed(3),
          b: +(shift).toFixed(3),
          c: +(Math.max(0, 1 - base - shift)).toFixed(3),
          dose,
        };
      });
      setHistoryData(mapped);
      if (mapped.length) {
        const last = mapped[mapped.length - 1];
        setComposition({ a: last.a, b: last.b, c: last.c });
        setDoseLevel(last.dose ?? 1.0);
      }
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulation/drug_composition/${sessionId}`);
      if (res.ok) {
        const json = await res.json();
        const comp = json.composition || { a: 0.33, b: 0.33, c: 0.34 };
        setComposition(comp);
        setDoseLevel(json.dose_level ?? 1.0);
        setHistoryData(prev => [...prev.slice(-29), {
          week: prev.length,
          a: comp.a, b: comp.b, c: comp.c, dose: json.dose_level,
        }]);
      }
    } catch (err) {
      console.error('Composition fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComposition();
    timerRef.current = setInterval(fetchComposition, 5000);
    return () => clearInterval(timerRef.current);
  }, [sessionId, history.length]);

  const pieData = [
    { name: 'Component A', value: composition.a },
    { name: 'Component B', value: composition.b },
    { name: 'Component C', value: composition.c },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ padding: 12, background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', borderRadius: 14 }}>
            <Beaker size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>Drug Composition</h2>
            <p style={{ color: '#94a3b8', fontSize: 13, margin: 0 }}>
              Auto-updated from simulation state — read-only
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            padding: '8px 16px', borderRadius: 10, background: 'rgba(139,92,246,0.1)',
            border: '1px solid rgba(139,92,246,0.3)', fontSize: 13, fontWeight: 700, color: '#8b5cf6',
          }}>
            Dose Level: {doseLevel.toFixed(2)}
          </div>
          <motion.button
            onClick={fetchComposition}
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            style={{
              padding: '8px 14px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.05)', color: '#64748b',
              display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12,
            }}
          >
            <RefreshCw size={12} /> Sync
          </motion.button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, flex: 1, minHeight: 0 }}>
        {/* Donut Chart */}
        <div className="liquid-glass" style={{ padding: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <h3 style={{ fontSize: 14, textTransform: 'uppercase', letterSpacing: 1.5, color: '#475569', marginBottom: 16 }}>Current Ratios</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                {pieData.map((entry, index) => (
                  <Cell key={index} fill={Object.values(COLORS)[index]} opacity={0.9} />
                ))}
              </Pie>
              <Tooltip
                formatter={(val) => `${(val * 100).toFixed(1)}%`}
                contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div style={{ display: 'flex', gap: 20, marginTop: 12 }}>
            {Object.entries(COLORS).map(([key, color]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
                <div>
                  <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Component {key.toUpperCase()}</div>
                  <div style={{ fontSize: 18, fontWeight: 900, color }}>{(composition[key] * 100).toFixed(1)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Time Series */}
        <div className="liquid-glass" style={{ padding: 32, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: 14, textTransform: 'uppercase', letterSpacing: 1.5, color: '#475569', marginBottom: 16 }}>Composition Over Time</h3>
          {historyData.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
              Start the simulation to see composition changes
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historyData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 11, fill: '#475569' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 11, fill: '#475569' }} domain={[0, 1]} />
                <Tooltip
                  formatter={(val) => `${(val * 100).toFixed(1)}%`}
                  contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
                />
                <Legend iconType="circle" iconSize={8} />
                <Area type="monotone" dataKey="a" stackId="1" stroke={COLORS.a} fill={COLORS.a} fillOpacity={0.6} name="Comp A" />
                <Area type="monotone" dataKey="b" stackId="1" stroke={COLORS.b} fill={COLORS.b} fillOpacity={0.6} name="Comp B" />
                <Area type="monotone" dataKey="c" stackId="1" stroke={COLORS.c} fill={COLORS.c} fillOpacity={0.6} name="Comp C" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
