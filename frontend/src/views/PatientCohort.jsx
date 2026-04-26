import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Users, Activity, AlertTriangle } from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, CartesianGrid, XAxis, YAxis, Tooltip, LineChart, Line
} from 'recharts';
import { useTrialStore } from '../store';

const STATUS_COLORS = {
  active: '#10b981',
  dropped_out: '#ef4444',
  completed: '#3b82f6',
};

export default function PatientCohort() {
  const { history, observation } = useTrialStore();

  // Get the latest patient list: from last history entry with patient_states, or generate from observation
  const patients = useMemo(() => {
    // Walk history backwards to find the most recent patient_states
    for (let i = history.length - 1; i >= 0; i--) {
      const ps = history[i].patient_states;
      if (ps && ps.length > 0) return ps;
    }
    // Fallback: generate from observation enrollment count
    const count = observation?.active ?? observation?.enrolled ?? 8;
    return Array.from({ length: Math.max(4, count) }, (_, i) => ({
      id: `SUBJ-${(1000 + i).toString(36).toUpperCase()}`,
      status: Math.random() > 0.12 ? 'active' : 'dropped_out',
      age: 35 + Math.floor(Math.random() * 35),
      sex: Math.random() > 0.48 ? 'Male' : 'Female',
      efficacy: parseFloat((0.3 + Math.random() * 0.6).toFixed(3)),
      ae_count: Math.floor(Math.random() * 3),
      dropout_risk: parseFloat((Math.random() * 0.5).toFixed(3)),
    }));
  }, [history, observation?.active]);

  // Enrollment trend from history
  const enrollmentTrend = history.map((h, i) => ({
    week: h.week ?? i,
    enrolled: h.enrolled ?? h.active ?? 0,
    active: h.active ?? 0,
  }));

  const ageData = [
    { age: '20–40', count: patients.filter(p => p.age >= 20 && p.age < 40).length },
    { age: '40–60', count: patients.filter(p => p.age >= 40 && p.age < 60).length },
    { age: '60+',   count: patients.filter(p => p.age >= 60).length },
  ];

  const statusCounts = patients.reduce((acc, p) => {
    const key = p.status ?? 'active';
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(statusCounts).map(([k, v]) => ({ name: k.replace('_', ' '), value: v, key: k }));

  const activeCount = statusCounts['active'] ?? 0;
  const droppedCount = statusCounts['dropped_out'] ?? 0;
  const avgAE = patients.length ? (patients.reduce((a, b) => a + (b.ae_count ?? 0), 0) / patients.length).toFixed(1) : '0.0';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%' }}>
      {/* Header stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        <StatCard icon={<Users size={18} />} label="Total Enrolled" value={patients.length} color="#3b82f6" />
        <StatCard icon={<Activity size={18} />} label="Active" value={activeCount} color="#10b981" />
        <StatCard icon={<Users size={18} />} label="Dropped Out" value={droppedCount} color="#ef4444" />
        <StatCard icon={<AlertTriangle size={18} />} label="Avg AEs" value={avgAE} color="#f59e0b" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, flex: 1, minHeight: 0 }}>
        {/* Table */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', margin: '0 0 14px 0' }}>
            Subject Detail Explorer
          </h3>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 6px' }}>
              <thead>
                <tr style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', textAlign: 'left' }}>
                  {['ID', 'Status', 'Age', 'Sex', 'Efficacy', 'AEs', 'Risk'].map(h => (
                    <th key={h} style={{ padding: '0 10px 8px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {patients.map((p, idx) => (
                  <motion.tr
                    key={p.id ?? idx}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.02 }}
                    style={{ background: 'rgba(255,255,255,0.03)' }}
                  >
                    <td style={{ padding: '10px', fontSize: 11, fontFamily: 'monospace', borderRadius: '10px 0 0 10px', color: '#94a3b8' }}>
                      {String(p.id ?? idx).slice(0, 10)}
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span style={{
                        fontSize: 10, fontWeight: 800, textTransform: 'uppercase',
                        color: STATUS_COLORS[p.status] ?? '#94a3b8',
                        background: `${STATUS_COLORS[p.status] ?? '#475569'}18`,
                        padding: '2px 7px', borderRadius: 4,
                      }}>
                        {(p.status ?? 'active').replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '10px', fontSize: 12 }}>{p.age ?? '–'}</td>
                    <td style={{ padding: '10px', fontSize: 12 }}>{p.sex ?? '–'}</td>
                    <td style={{ padding: '10px', fontSize: 12, fontWeight: 700, color: '#10b981' }}>
                      {((p.efficacy ?? 0) * 100).toFixed(0)}%
                    </td>
                    <td style={{ padding: '10px', fontSize: 12, fontWeight: 700, color: (p.ae_count ?? 0) > 0 ? '#ef4444' : '#475569' }}>
                      {p.ae_count ?? 0}
                    </td>
                    <td style={{ padding: '10px', borderRadius: '0 10px 10px 0' }}>
                      <div style={{ width: 56, height: 4, background: 'rgba(255,255,255,0.07)', borderRadius: 99 }}>
                        <div style={{
                          height: '100%', borderRadius: 99,
                          width: `${Math.min(100, (p.dropout_risk ?? 0) * 100)}%`,
                          background: `hsl(${120 - (p.dropout_risk ?? 0) * 120}, 70%, 50%)`,
                        }} />
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Charts column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, minHeight: 0 }}>
          {/* Enrollment trend */}
          <div className="liquid-glass" style={{ padding: 20, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', margin: '0 0 10px 0' }}>
              Enrollment Trend
            </h3>
            {enrollmentTrend.length < 2 ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 12 }}>
                Take more simulation steps
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={enrollmentTrend} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} />
                  <YAxis stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} />
                  <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                  <Line type="monotone" dataKey="enrolled" stroke="#3b82f6" strokeWidth={2} dot={false} name="Enrolled" />
                  <Line type="monotone" dataKey="active" stroke="#10b981" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="Active" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Status donut */}
          <div className="liquid-glass" style={{ padding: 20, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', margin: '0 0 10px 0' }}>
              Status Distribution
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} innerRadius={36} outerRadius={58} dataKey="value" paddingAngle={4} stroke="none">
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={STATUS_COLORS[entry.key] ?? '#475569'} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Age bar chart */}
          <div className="liquid-glass" style={{ padding: 20, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', margin: '0 0 10px 0' }}>
              Age Groups
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ageData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="age" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                <YAxis stroke="#334155" tick={{ fontSize: 9, fill: '#475569' }} />
                <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                <Bar dataKey="count" name="Patients" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="liquid-glass" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
      <div style={{ padding: 10, borderRadius: 12, background: `${color}20`, color }}>{icon}</div>
      <div>
        <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
        <div style={{ fontSize: 22, fontWeight: 800, color }}>{value}</div>
      </div>
    </motion.div>
  );
}
