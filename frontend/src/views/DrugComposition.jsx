import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { useTrialStore } from '../store';
import { Beaker } from 'lucide-react';
import { motion } from 'framer-motion';

const COMP_COLORS = { a: '#3b82f6', b: '#8b5cf6', c: '#ec4899' };

export default function DrugComposition() {
  const { history, observation } = useTrialStore();

  // Current composition from latest observation/state
  const current = observation?.composition ?? { a: 0.34, b: 0.33, c: 0.33 };
  const doseLevel = observation?.dose_level ?? 1.0;

  // Build time-series from history entries
  const timeData = useMemo(() =>
    history.map((h, i) => ({
      week: h.week ?? i,
      a: +(h.composition?.a ?? 0.34).toFixed(3),
      b: +(h.composition?.b ?? 0.33).toFixed(3),
      c: +(h.composition?.c ?? 0.33).toFixed(3),
      dose: +(h.dose_level ?? 1.0).toFixed(3),
    })),
  [history]);

  const pieData = [
    { name: 'Component A', value: current.a },
    { name: 'Component B', value: current.b },
    { name: 'Component C', value: current.c },
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
              Auto-updated from simulation state — {history.length} data points
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{
            padding: '8px 16px', borderRadius: 10, background: 'rgba(139,92,246,0.1)',
            border: '1px solid rgba(139,92,246,0.3)', fontSize: 13, fontWeight: 700, color: '#8b5cf6',
          }}>
            Dose: {doseLevel.toFixed(2)}
          </div>
          <div style={{
            padding: '8px 14px', borderRadius: 10, background: 'rgba(59,130,246,0.08)',
            border: '1px solid rgba(59,130,246,0.2)', fontSize: 12, color: '#475569',
          }}>
            Updates automatically with each simulation step
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: 24, flex: 1, minHeight: 0 }}>
        {/* Donut */}
        <div className="liquid-glass" style={{ padding: 28, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: '#475569', marginBottom: 16, margin: '0 0 16px 0' }}>
            Current Ratios
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={pieData} cx="50%" cy="50%"
                innerRadius={56} outerRadius={88}
                paddingAngle={4} dataKey="value" stroke="none"
                isAnimationActive={true}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={Object.values(COMP_COLORS)[i]} opacity={0.9} />
                ))}
              </Pie>
              <Tooltip
                formatter={val => `${(val * 100).toFixed(1)}%`}
                contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div style={{ display: 'flex', gap: 16, marginTop: 16, justifyContent: 'center' }}>
            {Object.entries(COMP_COLORS).map(([key, color]) => (
              <motion.div
                key={key}
                whileHover={{ scale: 1.05 }}
                style={{
                  textAlign: 'center', padding: '10px 14px', borderRadius: 12,
                  background: `${color}12`, border: `1px solid ${color}30`,
                }}
              >
                <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', marginBottom: 4 }}>
                  Comp {key.toUpperCase()}
                </div>
                <div style={{ fontSize: 22, fontWeight: 900, color }}>
                  {(current[key] * 100).toFixed(1)}%
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Time series */}
        <div className="liquid-glass" style={{ padding: 28, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: '#475569', margin: '0 0 16px 0' }}>
            Composition Evolution Over Time
          </h3>
          {timeData.length < 2 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
              Take at least 2 simulation steps to see composition changes
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 11, fill: '#475569' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 11, fill: '#475569' }} domain={[0, 1]} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
                <Tooltip
                  formatter={val => `${(val * 100).toFixed(1)}%`}
                  contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
                />
                <Legend iconType="circle" iconSize={8} />
                <Area type="monotone" dataKey="a" stackId="1" stroke={COMP_COLORS.a} fill={COMP_COLORS.a} fillOpacity={0.55} name="Comp A" isAnimationActive />
                <Area type="monotone" dataKey="b" stackId="1" stroke={COMP_COLORS.b} fill={COMP_COLORS.b} fillOpacity={0.55} name="Comp B" isAnimationActive />
                <Area type="monotone" dataKey="c" stackId="1" stroke={COMP_COLORS.c} fill={COMP_COLORS.c} fillOpacity={0.55} name="Comp C" isAnimationActive />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
