import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, Activity } from 'lucide-react';
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import { useTrialStore } from '../store';
import { api } from '../api';

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: '10px 16px' }}>
        {payload.map((p) => (
          <div key={p.name} style={{ color: p.color, fontSize: 12, marginBottom: 2 }}>
            {p.name}: <b>{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</b>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function PatientCohort() {
  const { sessionId } = useTrialStore();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const fetchPatients = async () => {
      if (!sessionId || sessionId === 'offline-demo') {
        // Mock data
        if (active) {
          setPatients(Array.from({ length: 12 }, (_, i) => ({
            id: `SUBJ-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
            status: Math.random() > 0.2 ? 'active' : 'dropped',
            age: 40 + Math.floor(Math.random() * 30),
            sex: Math.random() > 0.5 ? 'Male' : 'Female',
            efficacy: 0.3 + Math.random() * 0.6,
            ae_count: Math.floor(Math.random() * 4),
            dropout_risk: Math.random() * 0.8
          })));
          setLoading(false);
        }
        return;
      }

      try {
        const response = await fetch(`http://localhost:8000/simulation/patients/${sessionId}`);
        const data = await response.json();
        if (active && data.patients) {
          setPatients(data.patients);
        }
      } catch (err) {
        console.error("Failed to fetch patients", err);
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchPatients();
    
    // Auto-refresh interval (polling for updates)
    const interval = setInterval(fetchPatients, 3000);
    return () => { active = false; clearInterval(interval); };
  }, [sessionId]);

  if (loading) return <div style={{ padding: 20, color: '#94a3b8' }}>Loading cohort data...</div>;

  const maleCount = patients.filter(p => p.sex === 'Male' || p.sex === 'male').length;
  const femaleCount = patients.length - maleCount;

  const ageData = [
    { age: '20-40', count: patients.filter(p => p.age >= 20 && p.age < 40).length },
    { age: '40-60', count: patients.filter(p => p.age >= 40 && p.age < 60).length },
    { age: '60+', count: patients.filter(p => p.age >= 60).length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        <div className="liquid-glass" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
           <div style={{ padding: 10, borderRadius: 12, background: 'rgba(59,130,246,0.2)', color: '#3b82f6' }}><Users size={18} /></div>
           <div>
             <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>Total Enrolled</div>
             <div style={{ fontSize: 22, fontWeight: 800, color: '#3b82f6' }}>{patients.length}</div>
           </div>
        </div>
        <div className="liquid-glass" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
           <div style={{ padding: 10, borderRadius: 12, background: 'rgba(16,185,129,0.2)', color: '#10b981' }}><Activity size={18} /></div>
           <div>
             <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>Active</div>
             <div style={{ fontSize: 22, fontWeight: 800, color: '#10b981' }}>{patients.filter(p => p.status === 'active').length}</div>
           </div>
        </div>
        <div className="liquid-glass" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
           <div style={{ padding: 10, borderRadius: 12, background: 'rgba(239,68,68,0.2)', color: '#ef4444' }}><Users size={18} /></div>
           <div>
             <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>Avg AE Count</div>
             <div style={{ fontSize: 22, fontWeight: 800, color: '#ef4444' }}>{(patients.reduce((a,b) => a + b.ae_count, 0) / (patients.length || 1)).toFixed(1)}</div>
           </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, flex: 1, minHeight: 0 }}>
        {/* Table View */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 14 }}>Subject Detail Explorer</h3>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 8px' }}>
              <thead>
                <tr style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', textAlign: 'left' }}>
                  <th style={{ padding: '0 12px 8px' }}>ID</th>
                  <th style={{ padding: '0 12px 8px' }}>Status</th>
                  <th style={{ padding: '0 12px 8px' }}>Efficacy</th>
                  <th style={{ padding: '0 12px 8px' }}>AEs</th>
                  <th style={{ padding: '0 12px 8px' }}>Risk</th>
                </tr>
              </thead>
              <tbody>
                {patients.map(p => (
                  <tr key={p.id} style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '12px', fontSize: 12, fontFamily: 'monospace', borderRadius: '12px 0 0 12px' }}>{p.id.slice(0, 10)}...</td>
                    <td style={{ padding: '12px' }}>
                       <span style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', color: p.status === 'active' ? '#10b981' : '#ef4444', background: p.status === 'active' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', padding: '2px 6px', borderRadius: 4 }}>{p.status}</span>
                    </td>
                    <td style={{ padding: '12px', fontSize: 13, fontWeight: 700 }}>{(p.efficacy * 100).toFixed(0)}%</td>
                    <td style={{ padding: '12px', fontSize: 13, fontWeight: 700, color: p.ae_count > 0 ? '#ef4444' : '#94a3b8' }}>{p.ae_count}</td>
                    <td style={{ padding: '12px', borderRadius: '0 12px 12px 0' }}>
                       <div style={{ height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 99, width: 60 }}>
                          <div style={{ height: '100%', background: '#3b82f6', borderRadius: 99, width: `${Math.min(100, p.dropout_risk * 100)}%` }} />
                       </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="liquid-glass" style={{ padding: 20, flex: 1, display: 'flex', flexDirection: 'column' }}>
             <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 14 }}>Age Distribution</h3>
             <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ageData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                   <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                   <XAxis dataKey="age" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                   <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                   <Tooltip content={<CustomTooltip />} />
                   <Bar dataKey="count" name="Patients" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
             </ResponsiveContainer>
          </div>
          <div className="liquid-glass" style={{ padding: 20, flex: 1, display: 'flex', flexDirection: 'column' }}>
             <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 14 }}>Sex Distribution</h3>
             <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                   <Pie data={[{name: 'Male', value: maleCount}, {name: 'Female', value: femaleCount}]} innerRadius={40} outerRadius={60} dataKey="value">
                      <Cell fill="#3b82f6" />
                      <Cell fill="#ec4899" />
                   </Pie>
                   <Tooltip content={<CustomTooltip />} />
                </PieChart>
             </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
