import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Beaker, Users, TrendingUp, AlertTriangle, Activity,
  Play, RotateCcw, Zap, Clock, ChevronRight, Shield, FlaskConical
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { useTrialStore } from '../store';

const ACTIONS = [
  { id: 'recruit', label: 'Recruit +5 Patients', icon: <Users size={16} />, color: '#3b82f6', payload: { action_type: 'recruit', magnitude: 5 } },
  { id: 'dose_up', label: 'Increase Dose (+0.1)', icon: <TrendingUp size={16} />, color: '#8b5cf6', payload: { action_type: 'adjust_dose', magnitude: 0.1 } },
  { id: 'dose_down', label: 'Decrease Dose (-0.1)', icon: <Activity size={16} />, color: '#f59e0b', payload: { action_type: 'adjust_dose', magnitude: -0.1 } },
  { id: 'report', label: 'File Interim Report', icon: <Shield size={16} />, color: '#10b981', payload: { action_type: 'file_interim_report' } },
  { id: 'wait', label: 'Wait 1 Week', icon: <Clock size={16} />, color: '#64748b', payload: { action_type: 'noop' } },
  { id: 'escalate', label: 'Escalate Recruitment', icon: <Zap size={16} />, color: '#ec4899', payload: { action_type: 'recruit', magnitude: 15 } },
];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: '10px 16px' }}>
        {payload.map((p) => (
          <div key={p.name} style={{ color: p.color, fontSize: 12, marginBottom: 2 }}>
            {p.name}: <b>{typeof p.value === 'number' ? p.value.toFixed(3) : p.value}</b>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

const MetricBar = ({ label, value, max = 1, color }) => (
  <div style={{ marginBottom: 12 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12, color: '#94a3b8' }}>
      <span>{label}</span>
      <span style={{ color: '#f8fafc', fontWeight: 700 }}>{typeof value === 'number' ? value.toFixed(3) : value}</span>
    </div>
    <div style={{ height: 6, background: 'rgba(255,255,255,0.07)', borderRadius: 99 }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, (value / max) * 100)}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        style={{ height: '100%', background: color, borderRadius: 99, boxShadow: `0 0 8px ${color}60` }}
      />
    </div>
  </div>
);

export default function InteractiveTrial() {
  const { observation, history, eventLog, stepNumber, totalReward, trialPhase, actionLoading, takeAction } = useTrialStore();
  const logRef = React.useRef(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [eventLog]);

  if (!observation) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>
      <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.5, repeat: Infinity }}>
        Awaiting environment initialization...
      </motion.div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      {/* KPI Header */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        {[
          { label: 'Trial Phase', value: trialPhase, color: '#3b82f6', icon: <FlaskConical size={18} /> },
          { label: 'Step', value: stepNumber, color: '#8b5cf6', icon: <Activity size={18} /> },
          { label: 'Total Reward', value: totalReward.toFixed(2), color: totalReward >= 0 ? '#10b981' : '#ef4444', icon: <TrendingUp size={18} /> },
          { label: 'Active Subjects', value: observation.active ?? '—', color: '#f59e0b', icon: <Users size={18} /> },
        ].map((kpi) => (
          <motion.div key={kpi.label} whileHover={{ y: -2 }} className="liquid-glass" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ padding: 10, borderRadius: 12, background: kpi.color + '20', color: kpi.color }}>{kpi.icon}</div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
              <motion.div key={kpi.value} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} style={{ fontSize: 22, fontWeight: 800, color: kpi.color }}>
                {kpi.value}
              </motion.div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Main 3-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.7fr 1fr', gap: 16, flex: 1, minHeight: 0 }}>
        {/* Left: State Viewer */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 6, overflow: 'hidden' }}>
          <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 8 }}>Environment State</h3>
          <MetricBar label="Drug Concentration" value={observation.drug_concentration ?? 0} max={2} color="#8b5cf6" />
          <MetricBar label="Efficacy Signal" value={observation.efficacy_signal_estimate ?? 0} max={1} color="#10b981" />
          <MetricBar label="Cumulative Toxicity" value={observation.cumulative_toxicity ?? 0} max={1} color="#ef4444" />
          <MetricBar label="FDA Sentiment" value={observation.fda_sentiment ?? 0} max={1} color="#3b82f6" />
          {observation.disease_progression !== undefined && (
            <MetricBar label="Disease Progression" value={observation.disease_progression ?? 0} max={100} color="#f59e0b" />
          )}
          <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: observation.fda_flag === 'clear' ? '#10b981' : observation.fda_flag === 'monitoring' ? '#f59e0b' : '#ef4444',
                boxShadow: `0 0 6px ${observation.fda_flag === 'clear' ? '#10b981' : observation.fda_flag === 'monitoring' ? '#f59e0b' : '#ef4444'}`
              }} />
              <span style={{ color: '#94a3b8' }}>FDA: </span>
              <span style={{ fontWeight: 700, textTransform: 'capitalize' }}>{observation.fda_flag ?? 'unknown'}</span>
            </div>
          </div>
        </div>

        {/* Center: Charts */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 14 }}>Trial Trajectory</h3>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gEff" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gTox" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="step" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
              <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="efficacy_signal_estimate" name="Efficacy" stroke="#3b82f6" fill="url(#gEff)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="cumulative_toxicity" name="Toxicity" stroke="#ef4444" fill="url(#gTox)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="drug_concentration" name="Drug Conc." stroke="#8b5cf6" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Right: Action Panel */}
        <div className="liquid-glass" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 4 }}>Action Panel</h3>
          {ACTIONS.map((action) => (
            <motion.button
              key={action.id}
              id={`action-${action.id}`}
              onClick={() => takeAction(action.payload)}
              disabled={actionLoading}
              whileHover={{ scale: 1.02, x: 3 }}
              whileTap={{ scale: 0.97 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                width: '100%', padding: '11px 14px',
                background: 'rgba(255,255,255,0.03)',
                border: `1px solid ${action.color}40`,
                borderRadius: 12, color: action.color,
                fontSize: 13, fontWeight: 600, cursor: actionLoading ? 'not-allowed' : 'pointer',
                opacity: actionLoading ? 0.5 : 1,
                transition: 'background 0.2s',
              }}
            >
              {action.icon}
              {action.label}
              <ChevronRight size={14} style={{ marginLeft: 'auto', opacity: 0.5 }} />
            </motion.button>
          ))}

          {actionLoading && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ textAlign: 'center', fontSize: 12, color: '#64748b', marginTop: 4 }}
            >
              <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1, repeat: Infinity }}>
                Processing action...
              </motion.span>
            </motion.div>
          )}
        </div>
      </div>

      {/* Bottom: Event Log */}
      <div className="liquid-glass" style={{ padding: '16px 20px', maxHeight: 180, overflow: 'hidden' }}>
        <h3 style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color: '#64748b', marginBottom: 10 }}>Event Timeline</h3>
        <div ref={logRef} style={{ overflowY: 'auto', maxHeight: 120, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <AnimatePresence initial={false}>
            {eventLog.map((e) => (
              <motion.div
                key={e.id}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, padding: '5px 8px', borderRadius: 8, background: 'rgba(255,255,255,0.02)' }}
              >
                <span style={{ color: '#334155', minWidth: 60, fontFamily: 'monospace' }}>{e.time}</span>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                  background: e.type === 'positive' ? '#10b981' : e.type === 'negative' ? '#ef4444' : e.type === 'error' ? '#f59e0b' : '#3b82f6'
                }} />
                <span style={{ color: '#94a3b8', flex: 1 }}>{e.message}</span>
                {e.reward !== null && (
                  <span style={{ fontWeight: 700, color: e.reward >= 0 ? '#10b981' : '#ef4444', minWidth: 50, textAlign: 'right' }}>
                    {e.reward >= 0 ? '+' : ''}{e.reward.toFixed(3)}
                  </span>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
